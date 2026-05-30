from __future__ import annotations

from datetime import date

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from backend.app.models.discovery import ArxivCollection, ArxivCollectionItem, ArxivPaper, ArxivPaperEnrichment, ArxivPaperReview
from backend.app.models.discovery import ArxivTranslateDecision
from backend.app.models.task import TaskEngine, TaskSourceType
from backend.app.models.user import User
from backend.app.repositories.arxiv_repository import ArxivRepository
from backend.app.schemas.discovery import (
    DiscoveryCollectionItemResponse,
    DiscoveryCollectionListResponse,
    DiscoveryCollectionMembershipResponse,
    DiscoveryCollectionResponse,
    DiscoveryDailyDigestResponse,
    DiscoveryPaperDetailResponse,
    DiscoveryPaperEnrichmentResponse,
    DiscoveryPaperListResponse,
    DiscoveryPaperReviewResponse,
    DiscoveryPaperSummaryResponse,
    DiscoveryPaperTaskCreateRequest,
    DiscoveryPaperTaskResponse,
    DiscoveryRunResponse,
)
from backend.app.schemas.task import TaskCreateRequest as TaskCreatePayload
from backend.app.schemas.task import TaskSummaryResponse
from backend.app.services.access_service import AccessService
from backend.app.services.arxiv_collection_service import ArxivCollectionService
from backend.app.services.arxiv_persistence_service import ArxivPersistenceService
from backend.app.services.task_service import TaskService


class ArxivDiscoveryService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = ArxivRepository(db)
        self.access_service = AccessService(db)

    def list_papers(
        self,
        *,
        page: int,
        page_size: int,
        current_user: User,
        category: str | None = None,
        keyword: str | None = None,
        worth_read: bool | None = None,
        translated: bool | None = None,
        collection_id: int | None = None,
        source_run_date: date | None = None,
    ) -> DiscoveryPaperListResponse:
        papers, total = self.repository.list_papers(
            page=page,
            page_size=page_size,
            current_user=current_user,
            category=category,
            keyword=keyword,
            worth_read=worth_read,
            translated=translated,
            collection_id=collection_id,
            source_run_date=source_run_date,
        )
        items = [self._build_paper_summary_response(paper, current_user=current_user, preferred_collection_id=collection_id) for paper in papers]
        return DiscoveryPaperListResponse(items=items, total=total, page=page, page_size=page_size)

    def get_paper_detail(self, paper_id: int, *, current_user: User) -> DiscoveryPaperDetailResponse:
        paper = self.repository.get_paper_by_id(paper_id)
        if paper is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paper not found.")
        summary = self._build_paper_summary_response(paper, current_user=current_user)
        tasks = self._visible_task_summaries(paper, current_user=current_user)
        reviews = [
            self._build_review_response(review)
            for review in paper.reviews
            if review.collection.user_id == current_user.id
        ]
        active_enrichment = self._pick_enrichment(paper.enrichments)
        enrichment_response = self._build_enrichment_response(active_enrichment) if active_enrichment else None
        latest_task = tasks[0] if tasks else None
        return DiscoveryPaperDetailResponse(
            **summary.model_dump(),
            enrichment=enrichment_response,
            reviews=reviews,
            tasks=tasks,
            latest_task=latest_task,
        )

    def list_collections(self, *, current_user: User) -> DiscoveryCollectionListResponse:
        collections = self.repository.list_collections(current_user=current_user)
        items = [self._build_collection_response(collection, current_user=current_user) for collection in collections]
        return DiscoveryCollectionListResponse(items=items, total=len(items))

    def get_daily_digest(self, *, current_user: User) -> DiscoveryDailyDigestResponse:
        run = self.repository.get_latest_completed_run()
        if run is None:
            return DiscoveryDailyDigestResponse(run=None, total_papers=0, total_worth_read=0, total_translated=0)
        total_translated = self.repository.count_translated_papers_for_run(
            source_run_date=run.source_run_date
        )
        return DiscoveryDailyDigestResponse(
            run=DiscoveryRunResponse.model_validate(run),
            total_papers=run.total_papers,
            total_worth_read=run.total_worth_read,
            total_translated=total_translated,
        )

    def create_task_from_paper(
        self,
        paper_id: int,
        payload: DiscoveryPaperTaskCreateRequest,
        *,
        current_user: User,
    ) -> DiscoveryPaperTaskResponse:
        paper = self.repository.get_paper_by_id(paper_id)
        if paper is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paper not found.")

        if payload.collection_id is not None:
            item = self.repository.get_collection_item(collection_id=payload.collection_id, paper_id=paper_id)
            collection = self.repository.get_collection(payload.collection_id, current_user=current_user)
            if collection is None or item is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Collection item not found.")

        task_payload = TaskCreatePayload(
            task_name=payload.task_name,
            engine=TaskEngine.LATEX,
            source_type=TaskSourceType.ARXIV,
            arxiv_id=paper.arxiv_id,
            source_language=payload.source_language,
            target_language=payload.target_language,
            model_name=payload.model_name,
            env_profile=payload.env_profile,
            output_name=payload.output_name,
            options=payload.options,
        )
        task_response = TaskService(self.db).create_task(task_payload, owner=current_user)
        persisted_task = self.repository.find_tasks_by_arxiv_id(paper.arxiv_id)
        if persisted_task:
            ArxivPersistenceService(self.db).ensure_task_link(
                paper=paper,
                task=persisted_task[0],
                created_by_user_id=current_user.id,
                link_type="paper_create_task",
            )
            self.repository.commit()

        if payload.collection_id is not None:
            ArxivCollectionService(self.db).update_item_translate_decision(
                collection_id=payload.collection_id,
                paper_id=paper.id,
                translate_decision=ArxivTranslateDecision.MANUAL_REQUESTED,
                current_user=current_user,
            )

        paper_detail = self.get_paper_detail(paper.id, current_user=current_user)
        return DiscoveryPaperTaskResponse(task=task_response, paper=paper_detail)

    def _visible_task_summaries(self, paper: ArxivPaper, *, current_user: User) -> list[TaskSummaryResponse]:
        task_service = TaskService(self.db)
        visible: list[TaskSummaryResponse] = []
        seen: set[str] = set()
        for link in paper.task_links:
            task = link.task
            if task is None or task.id in seen:
                continue
            if not self.access_service.can_view_task(task, current_user):
                continue
            seen.add(task.id)
            visible.append(task_service._build_task_summary_response(task, current_user=current_user))
        visible.sort(key=lambda item: item.created_at, reverse=True)
        return visible

    def _build_collection_response(
        self,
        collection: ArxivCollection,
        *,
        current_user: User,
    ) -> DiscoveryCollectionResponse:
        items = [self._build_collection_item_response(item, current_user=current_user) for item in collection.items]
        return DiscoveryCollectionResponse(
            id=collection.id,
            user_id=collection.user_id,
            name=collection.name,
            description=collection.description,
            categories_json=collection.categories_json or [],
            prefer_keywords=collection.prefer_keywords,
            avoid_keywords=collection.avoid_keywords,
            translation_mode=collection.translation_mode,
            auto_translate_enabled=collection.auto_translate_enabled,
            item_count=len(items),
            items=items,
            created_at=collection.created_at,
            updated_at=collection.updated_at,
        )

    def _build_collection_item_response(
        self,
        item: ArxivCollectionItem,
        *,
        current_user: User,
    ) -> DiscoveryCollectionItemResponse:
        return DiscoveryCollectionItemResponse(
            id=item.id,
            collection_id=item.collection_id,
            paper_id=item.paper_id,
            added_by_user_id=item.added_by_user_id,
            note=item.note,
            translate_decision=item.translate_decision,
            created_at=item.created_at,
            updated_at=item.updated_at,
            paper=self._build_paper_summary_response(
                item.paper,
                current_user=current_user,
                preferred_collection_id=item.collection_id,
            ),
        )

    def _build_paper_summary_response(
        self,
        paper: ArxivPaper,
        *,
        current_user: User,
        preferred_collection_id: int | None = None,
        skip_task_details: bool = False,
    ) -> DiscoveryPaperSummaryResponse:
        reviews = [review for review in paper.reviews if review.collection.user_id == current_user.id]
        memberships = [
            item for item in paper.collection_items if item.collection.user_id == current_user.id
        ]
        selected_review = self._pick_review(reviews, preferred_collection_id=preferred_collection_id)

        # skip_task_details=True 时（如 daily-digest），task_links 未预加载 task 详情，
        # 直接用 task_links 数量判断，避免触发懒加载
        if skip_task_details:
            task_count = len(paper.task_links)
            has_translation = task_count > 0
        else:
            tasks = self._visible_task_summaries(paper, current_user=current_user)
            task_count = len(tasks)
            has_translation = bool(tasks)

        # Phase 2: title_zh/abstract_zh 只从全局 enrichment 读，review 不再携带这两个字段
        active_enrichment = self._pick_enrichment(paper.enrichments)
        title_zh = active_enrichment.title_zh if active_enrichment else None
        abstract_zh = active_enrichment.abstract_zh if active_enrichment else None

        return DiscoveryPaperSummaryResponse(
            id=paper.id,
            arxiv_id=paper.arxiv_id,
            primary_category=paper.primary_category,
            published_at=paper.published_at,
            scraped_at=paper.scraped_at,
            title_en=paper.title_en,
            abstract_en=paper.abstract_en,
            authors_json=paper.authors_json or [],
            pdf_url=paper.pdf_url,
            abs_url=paper.abs_url,
            subjects_json=paper.subjects_json or [],
            comments=paper.comments,
            source_run_date=paper.source_run_date,
            title_zh=title_zh,
            abstract_zh=abstract_zh,
            worth_read=selected_review.worth_read if selected_review else None,
            comment=selected_review.comment if selected_review else None,
            has_translation=has_translation,
            translation_task_count=task_count,
            collections=[self._build_membership_response(item) for item in memberships],
            created_at=paper.created_at,
            updated_at=paper.updated_at,
        )

    def _pick_review(
        self,
        reviews: list[ArxivPaperReview],
        *,
        preferred_collection_id: int | None = None,
    ) -> ArxivPaperReview | None:
        if preferred_collection_id is not None:
            for review in reviews:
                if review.collection_id == preferred_collection_id:
                    return review
        worthy_reviews = [review for review in reviews if review.worth_read]
        if worthy_reviews:
            worthy_reviews.sort(key=lambda review: review.updated_at, reverse=True)
            return worthy_reviews[0]
        if not reviews:
            return None
        reviews.sort(key=lambda review: review.updated_at, reverse=True)
        return reviews[0]

    def _pick_enrichment(
        self,
        enrichments: list[ArxivPaperEnrichment],
        *,
        enrichment_type: str = "global_summary",
    ) -> ArxivPaperEnrichment | None:
        """返回指定类型的最新 enrichment，优先取 global_summary。"""
        typed = [e for e in enrichments if e.enrichment_type == enrichment_type]
        if not typed:
            return enrichments[0] if enrichments else None
        typed.sort(key=lambda e: e.updated_at, reverse=True)
        return typed[0]

    def _build_membership_response(self, item: ArxivCollectionItem) -> DiscoveryCollectionMembershipResponse:
        return DiscoveryCollectionMembershipResponse(
            item_id=item.id,
            collection_id=item.collection_id,
            collection_name=item.collection.name,
            translate_decision=item.translate_decision,
            note=item.note,
            created_at=item.created_at,
            updated_at=item.updated_at,
        )

    def _build_review_response(self, review: ArxivPaperReview) -> DiscoveryPaperReviewResponse:
        return DiscoveryPaperReviewResponse(
            id=review.id,
            collection_id=review.collection_id,
            collection_name=review.collection.name,
            review_type=review.review_type,
            model_name=review.model_name,
            worth_read=review.worth_read,
            comment=review.comment,
            raw_result_json=review.raw_result_json,
            created_at=review.created_at,
            updated_at=review.updated_at,
        )

    def _build_enrichment_response(self, enrichment: ArxivPaperEnrichment) -> DiscoveryPaperEnrichmentResponse:
        return DiscoveryPaperEnrichmentResponse(
            id=enrichment.id,
            enrichment_type=enrichment.enrichment_type,
            model_name=enrichment.model_name,
            title_zh=enrichment.title_zh,
            abstract_zh=enrichment.abstract_zh,
            summary_zh=enrichment.summary_zh,
            keywords_json=enrichment.keywords_json,
            created_at=enrichment.created_at,
            updated_at=enrichment.updated_at,
        )

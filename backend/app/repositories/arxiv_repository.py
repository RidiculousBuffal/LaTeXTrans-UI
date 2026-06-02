from __future__ import annotations

from datetime import date

from sqlalchemy import exists, func, or_, select
from sqlalchemy.orm import Session, selectinload

from backend.app.models.discovery import (
    ArxivCollection,
    ArxivCollectionItem,
    ArxivDiscoveryRunStatus,
    ArxivDiscoveryRun,
    ArxivPaper,
    ArxivPaperEnrichment,
    ArxivPaperReview,
    ArxivPaperTaskLink,
)
from backend.app.models.task import TranslationTask
from backend.app.models.user import User


class ArxivRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_papers(
        self,
        *,
        page: int,
        page_size: int,
        current_user: User | None,
        category: str | None = None,
        keyword: str | None = None,
        worth_read: bool | None = None,
        translated: bool | None = None,
        collection_id: int | None = None,
        source_run_date: date | None = None,
    ) -> tuple[list[ArxivPaper], int]:
        filters = []
        if category:
            filters.append(ArxivPaper.primary_category == category)
        if source_run_date:
            filters.append(ArxivPaper.source_run_date == source_run_date)
        if keyword:
            keyword_pattern = f"%{keyword}%"
            # title_zh / abstract_zh 已迁移到 enrichment 表
            enrichment_exists = (
                select(ArxivPaperEnrichment.id)
                .where(
                    ArxivPaperEnrichment.paper_id == ArxivPaper.id,
                    or_(
                        ArxivPaperEnrichment.title_zh.ilike(keyword_pattern),
                        ArxivPaperEnrichment.abstract_zh.ilike(keyword_pattern),
                    ),
                )
                .exists()
            )
            keyword_filters = [
                ArxivPaper.arxiv_id.ilike(keyword_pattern),
                ArxivPaper.title_en.ilike(keyword_pattern),
                ArxivPaper.abstract_en.ilike(keyword_pattern),
                ArxivPaper.comments.ilike(keyword_pattern),
                enrichment_exists,
            ]
            if current_user is not None:
                review_comment_exists = (
                    select(ArxivPaperReview.id)
                    .join(ArxivCollection, ArxivCollection.id == ArxivPaperReview.collection_id)
                    .where(
                        ArxivPaperReview.paper_id == ArxivPaper.id,
                        ArxivCollection.user_id == current_user.id,
                        ArxivPaperReview.comment.ilike(keyword_pattern),
                    )
                    .exists()
                )
                keyword_filters.append(review_comment_exists)
            filters.append(or_(*keyword_filters))
        if worth_read is not None:
            if current_user is None:
                from sqlalchemy import false

                filters.append(false())
                # 匿名访问没有 collection-scoped review，可直接返回空结果条件
                pass
            else:
                review_stmt = select(ArxivPaperReview.id).where(
                    ArxivPaperReview.paper_id == ArxivPaper.id,
                    ArxivPaperReview.worth_read.is_(worth_read),
                )
                review_stmt = review_stmt.join(
                    ArxivCollection, ArxivCollection.id == ArxivPaperReview.collection_id
                ).where(ArxivCollection.user_id == current_user.id)
                filters.append(exists(review_stmt))
        if translated is not None:
            translated_exists = exists(
                select(ArxivPaperTaskLink.id).where(ArxivPaperTaskLink.paper_id == ArxivPaper.id)
            )
            filters.append(translated_exists if translated else ~translated_exists)
        if collection_id is not None and current_user is not None:
            filters.append(
                exists(
                    select(ArxivCollectionItem.id)
                    .join(ArxivCollection, ArxivCollection.id == ArxivCollectionItem.collection_id)
                    .where(
                        ArxivCollectionItem.paper_id == ArxivPaper.id,
                        ArxivCollectionItem.collection_id == collection_id,
                        ArxivCollection.user_id == current_user.id,
                    )
                )
            )

        stmt = (
            select(ArxivPaper)
            .where(*filters)
            .execution_options(populate_existing=True)
            .options(
                selectinload(ArxivPaper.enrichments),
                selectinload(ArxivPaper.reviews).selectinload(ArxivPaperReview.collection),
                selectinload(ArxivPaper.collection_items).selectinload(ArxivCollectionItem.collection),
                selectinload(ArxivPaper.task_links).selectinload(ArxivPaperTaskLink.task),
            )
            .order_by(ArxivPaper.scraped_at.desc(), ArxivPaper.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        count_stmt = select(func.count()).select_from(ArxivPaper).where(*filters)
        items = list(self.db.scalars(stmt).all())
        total = self.db.scalar(count_stmt) or 0
        return items, total

    def list_papers_for_digest(
        self,
        *,
        source_run_date: date,
        page_size: int = 200,
    ) -> list[ArxivPaper]:
        """daily-digest 专用查询：只加载必要的关联，不执行 COUNT。

        - enrichments: 用于 title_zh / abstract_zh
        - reviews → collection: 用于 worth_read / comment，需要 collection.user_id 做过滤
        - collection_items → collection: 用于 membership，需要 collection.user_id 做过滤
        - task_links: 只需要 paper_id 存在与否（has_translation），不需要加载 task 详情
        """
        stmt = (
            select(ArxivPaper)
            .where(ArxivPaper.source_run_date == source_run_date)
            .options(
                selectinload(ArxivPaper.enrichments),
                selectinload(ArxivPaper.reviews).selectinload(ArxivPaperReview.collection),
                selectinload(ArxivPaper.collection_items).selectinload(ArxivCollectionItem.collection),
                selectinload(ArxivPaper.task_links),  # 不再深层加载 task 详情
            )
            .order_by(ArxivPaper.scraped_at.desc(), ArxivPaper.id.desc())
            .limit(page_size)
        )
        return list(self.db.scalars(stmt).all())

    def get_paper_by_id(self, paper_id: int) -> ArxivPaper | None:
        stmt = (
            select(ArxivPaper)
            .where(ArxivPaper.id == paper_id)
            .execution_options(populate_existing=True)
            .options(
                selectinload(ArxivPaper.enrichments),
                selectinload(ArxivPaper.reviews).selectinload(ArxivPaperReview.collection),
                selectinload(ArxivPaper.collection_items).selectinload(ArxivCollectionItem.collection),
                selectinload(ArxivPaper.task_links).selectinload(ArxivPaperTaskLink.task),
            )
        )
        return self.db.scalar(stmt)

    def get_paper_by_arxiv_id(self, arxiv_id: str) -> ArxivPaper | None:
        stmt = (
            select(ArxivPaper)
            .where(ArxivPaper.arxiv_id == arxiv_id)
            .execution_options(populate_existing=True)
            .options(
                selectinload(ArxivPaper.enrichments),
                selectinload(ArxivPaper.reviews).selectinload(ArxivPaperReview.collection),
                selectinload(ArxivPaper.collection_items).selectinload(ArxivCollectionItem.collection),
                selectinload(ArxivPaper.task_links).selectinload(ArxivPaperTaskLink.task),
            )
        )
        return self.db.scalar(stmt)

    def add_paper(self, paper: ArxivPaper) -> ArxivPaper:
        self.db.add(paper)
        self.db.flush()
        return paper

    def get_review(self, *, paper_id: int, collection_id: int) -> ArxivPaperReview | None:
        stmt = select(ArxivPaperReview).where(
            ArxivPaperReview.paper_id == paper_id,
            ArxivPaperReview.collection_id == collection_id,
        )
        return self.db.scalar(stmt)

    def get_collection(self, collection_id: int, *, current_user: User | None = None) -> ArxivCollection | None:
        stmt = (
            select(ArxivCollection)
            .where(ArxivCollection.id == collection_id)
            .execution_options(populate_existing=True)
            .options(
                selectinload(ArxivCollection.items)
                .selectinload(ArxivCollectionItem.paper)
                .selectinload(ArxivPaper.enrichments),
                selectinload(ArxivCollection.items)
                .selectinload(ArxivCollectionItem.paper)
                .selectinload(ArxivPaper.reviews)
                .selectinload(ArxivPaperReview.collection),
                selectinload(ArxivCollection.items)
                .selectinload(ArxivCollectionItem.paper)
                .selectinload(ArxivPaper.collection_items)
                .selectinload(ArxivCollectionItem.collection),
                selectinload(ArxivCollection.items)
                .selectinload(ArxivCollectionItem.paper)
                .selectinload(ArxivPaper.task_links)
                .selectinload(ArxivPaperTaskLink.task),
            )
        )
        if current_user is not None:
            stmt = stmt.where(ArxivCollection.user_id == current_user.id)
        return self.db.scalar(stmt)

    def list_collections(self, *, current_user: User) -> list[ArxivCollection]:
        stmt = (
            select(ArxivCollection)
            .where(ArxivCollection.user_id == current_user.id)
            .execution_options(populate_existing=True)
            .options(
                selectinload(ArxivCollection.items)
                .selectinload(ArxivCollectionItem.paper)
                .selectinload(ArxivPaper.enrichments),
                selectinload(ArxivCollection.items)
                .selectinload(ArxivCollectionItem.paper)
                .selectinload(ArxivPaper.reviews)
                .selectinload(ArxivPaperReview.collection),
                selectinload(ArxivCollection.items)
                .selectinload(ArxivCollectionItem.paper)
                .selectinload(ArxivPaper.collection_items)
                .selectinload(ArxivCollectionItem.collection),
                selectinload(ArxivCollection.items)
                .selectinload(ArxivCollectionItem.paper)
                .selectinload(ArxivPaper.task_links)
                .selectinload(ArxivPaperTaskLink.task),
            )
            .order_by(ArxivCollection.updated_at.desc(), ArxivCollection.id.desc())
        )
        return list(self.db.scalars(stmt).all())

    def list_sync_target_collections(self) -> list[ArxivCollection]:
        stmt = select(ArxivCollection).order_by(ArxivCollection.id.asc())
        return list(self.db.scalars(stmt).all())

    def add_collection(self, collection: ArxivCollection) -> ArxivCollection:
        self.db.add(collection)
        self.db.flush()
        return collection

    def get_collection_item(self, *, collection_id: int, paper_id: int) -> ArxivCollectionItem | None:
        stmt = select(ArxivCollectionItem).where(
            ArxivCollectionItem.collection_id == collection_id,
            ArxivCollectionItem.paper_id == paper_id,
        )
        return self.db.scalar(stmt)

    def add_collection_item(self, item: ArxivCollectionItem) -> ArxivCollectionItem:
        self.db.add(item)
        self.db.flush()
        return item

    def delete_collection(self, collection: ArxivCollection) -> None:
        self.db.delete(collection)
        self.db.flush()

    def delete_collection_item(self, item: ArxivCollectionItem) -> None:
        self.db.delete(item)
        self.db.flush()

    def find_tasks_by_arxiv_id(self, arxiv_id: str) -> list[TranslationTask]:
        stmt = select(TranslationTask).where(TranslationTask.arxiv_id == arxiv_id).order_by(TranslationTask.created_at.desc())
        return list(self.db.scalars(stmt).all())

    def get_task_link(self, *, paper_id: int, task_id: str) -> ArxivPaperTaskLink | None:
        stmt = select(ArxivPaperTaskLink).where(
            ArxivPaperTaskLink.paper_id == paper_id,
            ArxivPaperTaskLink.task_id == task_id,
        )
        return self.db.scalar(stmt)

    def add_task_link(self, link: ArxivPaperTaskLink) -> ArxivPaperTaskLink:
        self.db.add(link)
        self.db.flush()
        return link

    def get_enrichment(self, *, paper_id: int, enrichment_type: str = "global_summary") -> ArxivPaperEnrichment | None:
        stmt = select(ArxivPaperEnrichment).where(
            ArxivPaperEnrichment.paper_id == paper_id,
            ArxivPaperEnrichment.enrichment_type == enrichment_type,
        )
        return self.db.scalar(stmt)

    def add_enrichment(self, enrichment: ArxivPaperEnrichment) -> ArxivPaperEnrichment:
        self.db.add(enrichment)
        self.db.flush()
        return enrichment

    def add_run(self, run: ArxivDiscoveryRun) -> ArxivDiscoveryRun:
        self.db.add(run)
        self.db.flush()
        return run

    def get_run(self, run_id: str) -> ArxivDiscoveryRun | None:
        return self.db.get(ArxivDiscoveryRun, run_id)

    def find_latest_run_for_date(self, *, source_run_date: date) -> ArxivDiscoveryRun | None:
        stmt = (
            select(ArxivDiscoveryRun)
            .where(ArxivDiscoveryRun.source_run_date == source_run_date)
            .order_by(ArxivDiscoveryRun.created_at.desc())
            .limit(1)
        )
        return self.db.scalar(stmt)

    def list_runs(self, *, page: int, page_size: int) -> tuple[list[ArxivDiscoveryRun], int]:
        stmt = (
            select(ArxivDiscoveryRun)
            .order_by(ArxivDiscoveryRun.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        count_stmt = select(func.count()).select_from(ArxivDiscoveryRun)
        return list(self.db.scalars(stmt).all()), self.db.scalar(count_stmt) or 0

    def count_translated_papers_for_run(self, *, source_run_date: date) -> int:
        """统计指定 run date 下有翻译任务的论文数量（一条 SQL，不加载 paper 数据）。"""
        stmt = (
            select(func.count(ArxivPaper.id))
            .where(
                ArxivPaper.source_run_date == source_run_date,
                exists(
                    select(ArxivPaperTaskLink.id).where(
                        ArxivPaperTaskLink.paper_id == ArxivPaper.id
                    )
                ),
            )
        )
        return self.db.scalar(stmt) or 0

    def get_latest_completed_run(self) -> ArxivDiscoveryRun | None:
        stmt = (
            select(ArxivDiscoveryRun)
            .where(ArxivDiscoveryRun.status == ArxivDiscoveryRunStatus.SUCCEEDED)
            .order_by(ArxivDiscoveryRun.finished_at.desc(), ArxivDiscoveryRun.created_at.desc())
            .limit(1)
        )
        return self.db.scalar(stmt)

    def commit(self) -> None:
        self.db.commit()

    def rollback(self) -> None:
        self.db.rollback()

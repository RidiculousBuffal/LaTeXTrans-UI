from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from backend.app.models.discovery import (
    ArxivCollection,
    ArxivDiscoveryRun,
    ArxivDiscoveryRunStatus,
    ArxivPaper,
    ArxivPaperEnrichment,
    ArxivPaperReview,
    ArxivPaperReviewType,
    ArxivPaperTaskLink,
)
from backend.app.models.task import TranslationTask
from backend.app.repositories.arxiv_repository import ArxivRepository


class ArxivPersistenceService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = ArxivRepository(db)

    def upsert_paper(
        self,
        *,
        arxiv_id: str,
        primary_category: str | None,
        title_en: str,
        abstract_en: str,
        authors_json: list[str],
        pdf_url: str | None,
        abs_url: str | None,
        subjects_json: list[str],
        comments: str | None,
        scraped_at: datetime,
        source_run_date,
    ) -> ArxivPaper:
        paper = self.repository.get_paper_by_arxiv_id(arxiv_id)
        if paper is None:
            paper = ArxivPaper(
                arxiv_id=arxiv_id,
                primary_category=primary_category,
                title_en=title_en,
                abstract_en=abstract_en,
                authors_json=authors_json,
                pdf_url=pdf_url,
                abs_url=abs_url,
                subjects_json=subjects_json,
                comments=comments,
                scraped_at=scraped_at,
                source_run_date=source_run_date,
            )
            self.repository.add_paper(paper)
            return paper

        paper.primary_category = primary_category or paper.primary_category
        paper.title_en = title_en
        paper.abstract_en = abstract_en
        paper.authors_json = authors_json
        paper.pdf_url = pdf_url
        paper.abs_url = abs_url
        paper.subjects_json = subjects_json
        paper.comments = comments
        paper.scraped_at = scraped_at
        paper.source_run_date = source_run_date
        self.db.flush()
        return paper

    def upsert_review(
        self,
        *,
        paper: ArxivPaper,
        collection: ArxivCollection,
        model_name: str,
        worth_read: bool,
        comment: str | None,
        raw_result_json: dict[str, Any] | None,
    ) -> ArxivPaperReview:
        review = self.repository.get_review(paper_id=paper.id, collection_id=collection.id)
        if review is None:
            review = ArxivPaperReview(
                paper_id=paper.id,
                collection_id=collection.id,
                review_type=ArxivPaperReviewType.DAILY_JUDGE,
                model_name=model_name,
                worth_read=worth_read,
                comment=comment,
                raw_result_json=raw_result_json,
            )
            self.db.add(review)
            self.db.flush()
            return review

        review.model_name = model_name
        review.worth_read = worth_read
        review.comment = comment
        review.raw_result_json = raw_result_json
        self.db.flush()
        return review

    def upsert_enrichment(
        self,
        *,
        paper: ArxivPaper,
        model_name: str,
        title_zh: str | None,
        abstract_zh: str | None,
        summary_zh: str | None = None,
        keywords_json: list[str] | None = None,
        raw_result_json: dict[str, Any] | None = None,
        enrichment_type: str = "global_summary",
    ) -> ArxivPaperEnrichment:
        enrichment = self.repository.get_enrichment(paper_id=paper.id, enrichment_type=enrichment_type)
        if enrichment is None:
            enrichment = ArxivPaperEnrichment(
                paper_id=paper.id,
                enrichment_type=enrichment_type,
                model_name=model_name,
                title_zh=title_zh,
                abstract_zh=abstract_zh,
                summary_zh=summary_zh,
                keywords_json=keywords_json,
                raw_result_json=raw_result_json,
            )
            self.repository.add_enrichment(enrichment)
            return enrichment

        enrichment.model_name = model_name
        enrichment.title_zh = title_zh
        enrichment.abstract_zh = abstract_zh
        enrichment.summary_zh = summary_zh
        enrichment.keywords_json = keywords_json
        enrichment.raw_result_json = raw_result_json
        self.db.flush()
        return enrichment

    def ensure_task_link(
        self,
        *,
        paper: ArxivPaper,
        task: TranslationTask,
        created_by_user_id: str | None = None,
        link_type: str = "arxiv_id_match",
    ) -> ArxivPaperTaskLink:
        link = self.repository.get_task_link(paper_id=paper.id, task_id=task.id)
        if link is not None:
            return link
        link = ArxivPaperTaskLink(
            paper_id=paper.id,
            task_id=task.id,
            created_by_user_id=created_by_user_id,
            link_type=link_type,
        )
        self.repository.add_task_link(link)
        return link

    def link_task_to_paper_by_arxiv_id(
        self,
        *,
        task: TranslationTask,
        created_by_user_id: str | None = None,
        link_type: str = "arxiv_id_match",
    ) -> ArxivPaper | None:
        if not task.arxiv_id:
            return None
        paper = self.repository.get_paper_by_arxiv_id(task.arxiv_id)
        if paper is None:
            return None
        self.ensure_task_link(paper=paper, task=task, created_by_user_id=created_by_user_id, link_type=link_type)
        return paper

    def link_existing_tasks_for_paper(self, paper: ArxivPaper) -> int:
        linked = 0
        for task in self.repository.find_tasks_by_arxiv_id(paper.arxiv_id):
            existing = self.repository.get_task_link(paper_id=paper.id, task_id=task.id)
            if existing is not None:
                continue
            self.repository.add_task_link(
                ArxivPaperTaskLink(
                    paper_id=paper.id,
                    task_id=task.id,
                    link_type="arxiv_id_backfill",
                )
            )
            linked += 1
        return linked

    def mark_run_started(self, run: ArxivDiscoveryRun) -> None:
        run.status = ArxivDiscoveryRunStatus.RUNNING
        run.started_at = datetime.utcnow()
        run.error_message = None
        self.db.flush()

    def mark_run_succeeded(
        self,
        run: ArxivDiscoveryRun,
        *,
        total_papers: int,
        total_reviews: int,
        total_worth_read: int,
        summary_json: dict[str, Any] | None,
    ) -> None:
        run.status = ArxivDiscoveryRunStatus.SUCCEEDED
        run.total_papers = total_papers
        run.total_reviews = total_reviews
        run.total_worth_read = total_worth_read
        run.summary_json = summary_json
        run.finished_at = datetime.utcnow()
        self.db.flush()

    def mark_run_failed(self, run: ArxivDiscoveryRun, *, error_message: str) -> None:
        run.status = ArxivDiscoveryRunStatus.FAILED
        run.error_message = error_message
        run.finished_at = datetime.utcnow()
        self.db.flush()

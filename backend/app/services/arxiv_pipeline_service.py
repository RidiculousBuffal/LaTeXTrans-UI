from __future__ import annotations

import shutil
import tarfile
import tempfile
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup
from fastapi import HTTPException, status
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.models.discovery import ArxivCollection, ArxivDiscoveryRun, ArxivDiscoveryRunStatus
from backend.app.models.user import User
from backend.app.repositories.arxiv_repository import ArxivRepository
from backend.app.services.arxiv_persistence_service import ArxivPersistenceService


class JudgeResult(BaseModel):
    chinese_name: str = Field(description="论文中文标题")
    chinese_abstract: str = Field(description="中文摘要")
    worth_read: bool = Field(description="根据收藏夹偏好判断是否值得阅读")
    comment: str = Field(description="简短评论，不超过 200 字")


@dataclass
class SyncReviewPayload:
    collection: ArxivCollection
    model_name: str
    worth_read: bool
    title_zh: str | None
    abstract_zh: str | None
    comment: str | None
    raw_result_json: dict[str, Any] | None


@dataclass
class SyncPaperPayload:
    arxiv_id: str
    primary_category: str | None
    title_en: str
    abstract_en: str
    authors_json: list[str]
    pdf_url: str | None
    abs_url: str | None
    subjects_json: list[str]
    comments: str | None
    scraped_at: datetime
    source_run_date: date
    reviews: list[SyncReviewPayload] = field(default_factory=list)


class ArxivPipelineService:
    BASE_URL = "https://arxiv.org"

    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = ArxivRepository(db)
        self.persistence = ArxivPersistenceService(db)
        self.settings = get_settings()
        self._judge_agent = None

    def create_run(
        self,
        *,
        current_user: User | None,
        trigger_source: str,
        source_run_date: date,
        force_refresh: bool = False,
    ) -> ArxivDiscoveryRun:
        latest = self.repository.find_latest_run_for_date(source_run_date=source_run_date)
        if latest is not None and not force_refresh and latest.status in {
            ArxivDiscoveryRunStatus.PENDING,
            ArxivDiscoveryRunStatus.RUNNING,
            ArxivDiscoveryRunStatus.SUCCEEDED,
        }:
            return latest

        categories = self._collect_sync_categories(self.repository.list_sync_target_collections())
        run = ArxivDiscoveryRun(
            trigger_source=trigger_source,
            requested_by_user_id=current_user.id if current_user else None,
            source_run_date=source_run_date,
            status=ArxivDiscoveryRunStatus.PENDING,
            categories_json=categories,
        )
        self.repository.add_run(run)
        self.repository.commit()
        return run

    def execute_run(self, run_id: str) -> ArxivDiscoveryRun:
        run = self.repository.get_run(run_id)
        if run is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Discovery run not found.")

        self.persistence.mark_run_started(run)
        self.repository.commit()

        try:
            collections = [collection for collection in self.repository.list_sync_target_collections() if collection.categories_json]
            if not run.categories_json:
                self.persistence.mark_run_succeeded(
                    run,
                    total_papers=0,
                    total_reviews=0,
                    total_worth_read=0,
                    summary_json={"reason": "No collection categories configured."},
                )
                self.repository.commit()
                return run

            payloads, summary_json = self._build_sync_payloads(
                categories=run.categories_json,
                collections=collections,
                source_run_date=run.source_run_date,
            )

            total_reviews = 0
            total_worth_read = 0
            for payload in payloads:
                paper = self.persistence.upsert_paper(
                    arxiv_id=payload.arxiv_id,
                    primary_category=payload.primary_category,
                    title_en=payload.title_en,
                    abstract_en=payload.abstract_en,
                    authors_json=payload.authors_json,
                    pdf_url=payload.pdf_url,
                    abs_url=payload.abs_url,
                    subjects_json=payload.subjects_json,
                    comments=payload.comments,
                    scraped_at=payload.scraped_at,
                    source_run_date=payload.source_run_date,
                )
                for review_payload in payload.reviews:
                    self.persistence.upsert_review(
                        paper=paper,
                        collection=review_payload.collection,
                        model_name=review_payload.model_name,
                        worth_read=review_payload.worth_read,
                        title_zh=review_payload.title_zh,
                        abstract_zh=review_payload.abstract_zh,
                        comment=review_payload.comment,
                        raw_result_json=review_payload.raw_result_json,
                    )
                    total_reviews += 1
                    total_worth_read += int(review_payload.worth_read)
                self.persistence.link_existing_tasks_for_paper(paper)

            self.persistence.mark_run_succeeded(
                run,
                total_papers=len(payloads),
                total_reviews=total_reviews,
                total_worth_read=total_worth_read,
                summary_json=summary_json,
            )
            self.repository.commit()
            return run
        except Exception as exc:
            self.repository.rollback()
            run = self.repository.get_run(run_id)
            if run is not None:
                self.persistence.mark_run_failed(run, error_message=str(exc))
                self.repository.commit()
            raise

    def _build_sync_payloads(
        self,
        *,
        categories: list[str],
        collections: list[ArxivCollection],
        source_run_date: date,
    ) -> tuple[list[SyncPaperPayload], dict[str, Any]]:
        papers_by_id: dict[str, SyncPaperPayload] = {}
        category_counts: dict[str, int] = defaultdict(int)
        collection_counts: dict[int, int] = defaultdict(int)

        for category in categories:
            articles = self._crawl_category(category)
            category_counts[category] = len(articles)
            for article in articles:
                payload = papers_by_id.get(article["arxiv_id"])
                if payload is None:
                    payload = SyncPaperPayload(
                        arxiv_id=article["arxiv_id"],
                        primary_category=article["category"],
                        title_en=article["title"],
                        abstract_en=article["abstract"],
                        authors_json=article["authors"],
                        pdf_url=article["pdf_url"],
                        abs_url=article["abs_url"],
                        subjects_json=article["subjects"],
                        comments=article["comments"],
                        scraped_at=article["scraped_at"],
                        source_run_date=source_run_date,
                    )
                    papers_by_id[payload.arxiv_id] = payload
                else:
                    merged_subjects = list(dict.fromkeys([*payload.subjects_json, *article["subjects"]]))
                    payload.subjects_json = merged_subjects
                    payload.primary_category = payload.primary_category or article["category"]

                matched_collections = self._match_collections(article=article, collections=collections)
                for collection in matched_collections:
                    collection_counts[collection.id] += 1
                    if any(review.collection.id == collection.id for review in payload.reviews):
                        continue
                    review = self._build_review(article=article, collection=collection)
                    payload.reviews.append(review)

        summary_json = {
            "categories": [{"category": key, "paper_count": value} for key, value in sorted(category_counts.items())],
            "collections": [
                {"collection_id": collection.id, "collection_name": collection.name, "matched_paper_count": collection_counts.get(collection.id, 0)}
                for collection in collections
            ],
        }
        return list(papers_by_id.values()), summary_json

    def _crawl_category(self, category: str) -> list[dict[str, Any]]:
        url = f"{self.BASE_URL}/list/{category}/new"
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36"
            )
        }
        with httpx.Client(timeout=20.0, headers=headers, follow_redirects=True) as client:
            response = client.get(url)
            response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        listing = soup.find("dl", id="articles")
        if listing is None:
            return []

        dts = listing.find_all("dt", recursive=False)
        dds = listing.find_all("dd", recursive=False)
        scraped_at = datetime.utcnow()
        articles: list[dict[str, Any]] = []

        for dt, dd in zip(dts, dds):
            parsed = self._parse_article(dt, dd, category=category, scraped_at=scraped_at)
            if parsed is not None:
                articles.append(parsed)
        return articles

    def _parse_article(self, dt, dd, *, category: str, scraped_at: datetime) -> dict[str, Any] | None:
        anchors = dt.find_all("a")
        abs_url = None
        arxiv_id = None
        pdf_url = None
        for anchor in anchors:
            href = anchor.get("href", "")
            title = (anchor.get("title") or "").lower()
            anchor_id = anchor.get("id", "")
            if href.startswith("/abs/") or "abstract" in title:
                abs_url = urljoin(self.BASE_URL, href)
                arxiv_id = anchor_id or href.rsplit("/", 1)[-1]
            elif anchor_id.startswith("pdf-") or "pdf" in title:
                pdf_url = urljoin(self.BASE_URL, href)

        if not abs_url or not arxiv_id:
            return None

        meta = dd.find("div", class_="meta")
        if meta is None:
            return None

        title_div = meta.find("div", class_="list-title")
        authors_div = meta.find("div", class_="list-authors")
        abstract_div = meta.find("p", class_="mathjax")
        subjects_div = meta.find("div", class_="list-subjects")
        comments_div = meta.find("div", class_="list-comments")
        if title_div is None or abstract_div is None:
            return None

        title = title_div.get_text(" ", strip=True).replace("Title:", "", 1).strip()
        authors = [anchor.get_text(strip=True) for anchor in authors_div.find_all("a")] if authors_div else []
        abstract = abstract_div.get_text(" ", strip=True)
        comments = None
        if comments_div is not None:
            comments = comments_div.get_text(" ", strip=True).replace("Comments:", "", 1).strip() or None

        subjects: list[str] = []
        primary_subject = None
        if subjects_div is not None:
            primary_span = subjects_div.find("span", class_="primary-subject")
            if primary_span is not None:
                primary_subject = primary_span.get_text(strip=True)
                subjects.append(primary_subject)
            full_text = subjects_div.get_text(" ", strip=True).replace("Subjects:", "", 1).strip()
            for segment in full_text.replace(";", ",").split(","):
                normalized = segment.strip()
                if not normalized or normalized == primary_subject:
                    continue
                subjects.append(normalized)

        return {
            "arxiv_id": arxiv_id,
            "category": category,
            "abs_url": abs_url,
            "pdf_url": pdf_url,
            "title": title,
            "authors": authors,
            "comments": comments,
            "subjects": list(dict.fromkeys(subjects or [category])),
            "abstract": abstract,
            "scraped_at": scraped_at,
        }

    def _match_collections(self, *, article: dict[str, Any], collections: list[ArxivCollection]) -> list[ArxivCollection]:
        article_categories = {article["category"], *article["subjects"]}
        matched: list[ArxivCollection] = []
        for collection in collections:
            configured = {value.strip() for value in collection.categories_json if value.strip()}
            if configured.intersection(article_categories):
                matched.append(collection)
        return matched

    def _build_review(self, *, article: dict[str, Any], collection: ArxivCollection) -> SyncReviewPayload:
        model_name = self.settings.openai_model or "gpt-4.1-mini"
        judge_result = self._judge_article(article=article, collection=collection, model_name=model_name)
        analysis_summary = self._analyze_source_metadata(article)
        raw_result = {
            "judge": judge_result.model_dump(),
            "analysis": analysis_summary,
            "collection_preferences": {
                "categories": collection.categories_json,
                "prefer_keywords": collection.prefer_keywords,
                "avoid_keywords": collection.avoid_keywords,
            },
        }
        return SyncReviewPayload(
            collection=collection,
            model_name=model_name,
            worth_read=judge_result.worth_read,
            title_zh=judge_result.chinese_name,
            abstract_zh=judge_result.chinese_abstract,
            comment=judge_result.comment,
            raw_result_json=raw_result,
        )

    def _judge_article(self, *, article: dict[str, Any], collection: ArxivCollection, model_name: str) -> JudgeResult:
        if not self.settings.openai_api_key:
            return self._fallback_judge(article=article, collection=collection)

        prompt = self._build_judger_prompt(collection)
        message = HumanMessage(
            content=(
                "文章元信息:\n"
                f"arxiv_id={article['arxiv_id']}\n"
                f"title={article['title']}\n"
                f"abstract={article['abstract']}\n"
                f"subjects={article['subjects']}\n"
                f"authors={article['authors']}\n"
                f"comments={article['comments']}\n"
            )
        )
        try:
            agent = self._get_judge_agent(model_name)
            result = agent.invoke({"messages": [SystemMessage(content=prompt), message]})
            structured = result["structured_response"]
            if isinstance(structured, JudgeResult):
                return structured
            return JudgeResult.model_validate(structured)
        except Exception:
            return self._fallback_judge(article=article, collection=collection)

    def _get_judge_agent(self, model_name: str):
        if self._judge_agent is None:
            model = ChatOpenAI(
                api_key=self.settings.openai_api_key,
                base_url=self.settings.openai_base_url or None,
                model=model_name,
                use_responses_api=True,
            )
            self._judge_agent = create_agent(model, response_format=JudgeResult)
        return self._judge_agent

    def _build_judger_prompt(self, collection: ArxivCollection) -> str:
        prefer = collection.prefer_keywords or "<none>"
        avoid = collection.avoid_keywords or "<none>"
        categories = ", ".join(collection.categories_json or []) or "<none>"
        return (
            "你是一个论文评判助手，需要根据收藏夹的研究偏好判断文章是否值得阅读，并返回结构化结果。\n"
            "输出字段必须包括：chinese_name, chinese_abstract, worth_read, comment。\n"
            f"收藏夹关注分类: {categories}\n"
            f"偏好关键词: {prefer}\n"
            f"不偏好关键词: {avoid}\n"
            "请严格判断，不要因为只有少量相关内容就默认推荐。"
        )

    def _fallback_judge(self, *, article: dict[str, Any], collection: ArxivCollection) -> JudgeResult:
        haystack = f"{article['title']} {article['abstract']} {' '.join(article['subjects'])}".lower()
        prefer_terms = self._split_keywords(collection.prefer_keywords)
        avoid_terms = self._split_keywords(collection.avoid_keywords)
        matched_prefer = [term for term in prefer_terms if term in haystack]
        matched_avoid = [term for term in avoid_terms if term in haystack]
        worth_read = (not prefer_terms or bool(matched_prefer)) and not matched_avoid
        if matched_avoid:
            comment = f"命中了不偏好关键词: {', '.join(matched_avoid[:3])}。"
        elif matched_prefer:
            comment = f"命中了偏好关键词: {', '.join(matched_prefer[:3])}。"
        else:
            comment = "未配置可用的 OpenAI 审阅环境，使用关键词回退策略生成结果。"
        return JudgeResult(
            chinese_name=article["title"],
            chinese_abstract=article["abstract"],
            worth_read=worth_read,
            comment=comment,
        )

    def _analyze_source_metadata(self, article: dict[str, Any]) -> dict[str, Any]:
        pdf_url = article.get("pdf_url")
        if not pdf_url:
            return {"status": "skipped", "reason": "missing_pdf_url"}

        src_url = str(pdf_url).replace("/pdf/", "/src/")
        temp_root = Path(tempfile.mkdtemp(prefix="latextrans-discovery-"))
        archive_path = temp_root / "source.tar.gz"
        extract_root = temp_root / "extract"
        extract_root.mkdir(parents=True, exist_ok=True)
        try:
            with httpx.stream("GET", src_url, timeout=60.0, follow_redirects=True) as response:
                response.raise_for_status()
                with archive_path.open("wb") as output:
                    for chunk in response.iter_bytes():
                        if chunk:
                            output.write(chunk)

            tex_count = 0
            figure_count = 0
            with tarfile.open(archive_path, mode="r:gz") as archive:
                for member in archive.getmembers():
                    member_path = Path(member.name)
                    if member_path.is_absolute() or ".." in member_path.parts:
                        continue
                    archive.extract(member, path=extract_root)

            for path in extract_root.rglob("*"):
                if not path.is_file():
                    continue
                if path.suffix.lower() == ".tex":
                    tex_count += 1
                elif path.suffix.lower() in {".png", ".jpg", ".jpeg", ".pdf", ".svg"}:
                    figure_count += 1

            return {
                "status": "succeeded",
                "source_url": src_url,
                "tex_file_count": tex_count,
                "figure_file_count": figure_count,
                "metadata_ready": tex_count > 0,
            }
        except Exception as exc:
            return {"status": "failed", "source_url": src_url, "error": str(exc)}
        finally:
            shutil.rmtree(temp_root, ignore_errors=True)

    def _collect_sync_categories(self, collections: list[ArxivCollection]) -> list[str]:
        categories: list[str] = []
        seen: set[str] = set()
        for collection in collections:
            for category in collection.categories_json or []:
                normalized = category.strip()
                if not normalized or normalized in seen:
                    continue
                seen.add(normalized)
                categories.append(normalized)
        return categories

    def _split_keywords(self, value: str | None) -> list[str]:
        if not value:
            return []
        parts = []
        for chunk in value.replace("\n", ",").split(","):
            normalized = chunk.strip().lower()
            if normalized:
                parts.append(normalized)
        return parts

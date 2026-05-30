from __future__ import annotations

import logging
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

logger = logging.getLogger(__name__)

MAX_ARTICLES_PER_CATEGORY = 50


class JudgeResult(BaseModel):
    chinese_name: str = Field(description="论文中文标题")
    chinese_abstract: str = Field(description="中文摘要")
    worth_read: bool = Field(description="根据收藏夹偏好判断是否值得阅读")
    comment: str = Field(description="简短评论，不超过 200 字")


class EnrichResult(BaseModel):
    """全局 enrichment agent 的输出：只包含与 collection 无关的翻译字段。"""

    chinese_name: str = Field(description="论文中文标题（忠实翻译）")
    chinese_abstract: str = Field(description="中文摘要（忠实翻译）")


class JudgmentResult(BaseModel):
    """Collection judgment agent 的输出：只包含 collection-scoped 判断字段。"""

    worth_read: bool = Field(description="根据收藏夹偏好判断是否值得阅读")
    comment: str = Field(description="简短评论，不超过 200 字")


@dataclass
class SyncEnrichmentPayload:
    """全局 enrichment 数据，与 collection 无关。"""

    model_name: str
    title_zh: str | None
    abstract_zh: str | None
    raw_result_json: dict[str, Any] | None


@dataclass
class SyncReviewPayload:
    collection: ArxivCollection
    model_name: str
    worth_read: bool
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
    enrichment: SyncEnrichmentPayload | None = None
    reviews: list[SyncReviewPayload] = field(default_factory=list)


class ArxivPipelineService:
    BASE_URL = "https://arxiv.org"

    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = ArxivRepository(db)
        self.persistence = ArxivPersistenceService(db)
        self.settings = get_settings()
        self._judge_agent = None
        self._enrich_agent = None

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
                # Phase 1: 先写全局 enrichment
                if payload.enrichment is not None:
                    self.persistence.upsert_enrichment(
                        paper=paper,
                        model_name=payload.enrichment.model_name,
                        title_zh=payload.enrichment.title_zh,
                        abstract_zh=payload.enrichment.abstract_zh,
                        raw_result_json=payload.enrichment.raw_result_json,
                    )
                for review_payload in payload.reviews:
                    self.persistence.upsert_review(
                        paper=paper,
                        collection=review_payload.collection,
                        model_name=review_payload.model_name,
                        worth_read=review_payload.worth_read,
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
                    # 每篇 paper 只生成一次全局 enrichment
                    enrichment = self._build_enrichment(article=article)
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
                        enrichment=enrichment,
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
                    # 每个 collection 生成独立的 judgment
                    review = self._build_judgment(article=article, collection=collection, enrichment=payload.enrichment)
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
        logger.info("[crawl] 开始抓取类别 category=%s url=%s", category, url)
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
            logger.warning("[crawl] 类别 %s 未找到文章列表 (dl#articles)", category)
            return []

        dts = listing.find_all("dt", recursive=False)
        dds = listing.find_all("dd", recursive=False)
        total_candidates = len(dts)
        scraped_at = datetime.utcnow()
        articles: list[dict[str, Any]] = []

        for idx, (dt, dd) in enumerate(zip(dts, dds)):
            if len(articles) >= MAX_ARTICLES_PER_CATEGORY:
                logger.info(
                    "[crawl] 类别 %s 已达上限 %d 条，跳过剩余 %d 条候选",
                    category,
                    MAX_ARTICLES_PER_CATEGORY,
                    total_candidates - idx,
                )
                break
            parsed = self._parse_article(dt, dd, category=category, scraped_at=scraped_at)
            if parsed is not None:
                articles.append(parsed)
                logger.debug(
                    "[parse] 类别 %s 第 %d 条 arxiv_id=%s title=%s",
                    category,
                    len(articles),
                    parsed["arxiv_id"],
                    parsed["title"][:60],
                )
            else:
                logger.debug("[parse] 类别 %s 第 %d 个条目解析失败，已跳过", category, idx + 1)

        logger.info(
            "[crawl] 类别 %s 抓取完成：候选 %d 条，成功解析 %d 条",
            category,
            total_candidates,
            len(articles),
        )
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
            logger.debug("[parse] 跳过条目：缺少 abs_url 或 arxiv_id")
            return None

        meta = dd.find("div", class_="meta")
        if meta is None:
            logger.debug("[parse] arxiv_id=%s 跳过：缺少 meta div", arxiv_id)
            return None

        title_div = meta.find("div", class_="list-title")
        authors_div = meta.find("div", class_="list-authors")
        abstract_div = meta.find("p", class_="mathjax")
        subjects_div = meta.find("div", class_="list-subjects")
        comments_div = meta.find("div", class_="list-comments")
        if title_div is None or abstract_div is None:
            logger.debug("[parse] arxiv_id=%s 跳过：缺少 title 或 abstract", arxiv_id)
            return None

        title = title_div.get_text(" ", strip=True).replace("Title:", "", 1).strip()
        authors = [anchor.get_text(strip=True) for anchor in authors_div.find_all("a")] if authors_div else []
        abstract = abstract_div.get_text(" ", strip=True)
        comments = None
        if comments_div is not None:
            comments = comments_div.get_text(" ", strip=True).replace("Comments:", "", 1).strip() or None
            if comments:
                logger.debug("[parse] arxiv_id=%s 提取到 comments: %s", arxiv_id, comments[:100])
            else:
                logger.debug("[parse] arxiv_id=%s comments 字段为空", arxiv_id)
        else:
            logger.debug("[parse] arxiv_id=%s 无 comments 字段", arxiv_id)

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

        result = {
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
        logger.debug(
            "[parse] 解析成功 arxiv_id=%s category=%s authors=%d subjects=%d has_comments=%s",
            arxiv_id,
            category,
            len(authors),
            len(result["subjects"]),
            comments is not None,
        )
        return result

    def _match_collections(self, *, article: dict[str, Any], collections: list[ArxivCollection]) -> list[ArxivCollection]:
        article_categories = {article["category"], *article["subjects"]}
        matched: list[ArxivCollection] = []
        for collection in collections:
            configured = {value.strip() for value in collection.categories_json if value.strip()}
            if configured.intersection(article_categories):
                matched.append(collection)
        return matched

    def _build_enrichment(self, *, article: dict[str, Any]) -> SyncEnrichmentPayload:
        """生成全局 enrichment（与 collection 无关的翻译结果）。"""
        model_name = self.settings.openai_model or "gpt-4.1-mini"
        enrich_result = self._enrich_article(article=article, model_name=model_name)
        raw_result = {"enrich": enrich_result.model_dump()}
        return SyncEnrichmentPayload(
            model_name=model_name,
            title_zh=enrich_result.chinese_name,
            abstract_zh=enrich_result.chinese_abstract,
            raw_result_json=raw_result,
        )

    def _build_judgment(
        self,
        *,
        article: dict[str, Any],
        collection: ArxivCollection,
        enrichment: SyncEnrichmentPayload | None,
    ) -> SyncReviewPayload:
        """生成 collection-scoped judgment。双写阶段同时携带 title_zh/abstract_zh。"""
        model_name = self.settings.openai_model or "gpt-4.1-mini"
        judgment_result = self._judge_article(article=article, collection=collection, model_name=model_name)
        analysis_summary = self._analyze_source_metadata(article)
        raw_result = {
            "judgment": judgment_result.model_dump(),
            "analysis": analysis_summary,
            "collection_preferences": {
                "categories": collection.categories_json,
                "prefer_keywords": collection.prefer_keywords,
                "avoid_keywords": collection.avoid_keywords,
            },
        }
        # 双写阶段已结束：review 不再携带 title_zh/abstract_zh
        return SyncReviewPayload(
            collection=collection,
            model_name=model_name,
            worth_read=judgment_result.worth_read,
            comment=judgment_result.comment,
            raw_result_json=raw_result,
        )

    def _enrich_article(self, *, article: dict[str, Any], model_name: str) -> EnrichResult:
        """调用 Global Enrichment Agent，只做忠实翻译，不依赖 collection 偏好。"""
        arxiv_id = article.get("arxiv_id", "unknown")
        if not self.settings.openai_api_key:
            logger.info("[enrich] arxiv_id=%s 无 API Key，使用回退策略（保留英文原文）", arxiv_id)
            return self._fallback_enrich(article=article)

        logger.info("[enrich] arxiv_id=%s 开始翻译标题和摘要 model=%s", arxiv_id, model_name)
        prompt = (
            "你是一个学术论文翻译助手，请将以下论文的标题和摘要忠实地翻译成中文。\n"
            "要求：\n"
            "- 保持学术用语准确\n"
            "- 不要添加主观评价或解释性改写\n"
            "- 输出字段：chinese_name（中文标题），chinese_abstract（中文摘要）"
        )
        message = HumanMessage(
            content=(
                f"title={article['title']}\n"
                f"abstract={article['abstract']}\n"
            )
        )
        try:
            agent = self._get_enrich_agent(model_name)
            result = agent.invoke({"messages": [SystemMessage(content=prompt), message]})
            structured = result["structured_response"]
            if isinstance(structured, EnrichResult):
                enrich_result = structured
            else:
                enrich_result = EnrichResult.model_validate(structured)
            logger.info(
                "[enrich] arxiv_id=%s 翻译完成 chinese_name=%s",
                arxiv_id,
                enrich_result.chinese_name[:40],
            )
            return enrich_result
        except Exception as exc:
            logger.warning("[enrich] arxiv_id=%s 翻译失败，使用回退策略 error=%s", arxiv_id, exc)
            return self._fallback_enrich(article=article)

    def _get_enrich_agent(self, model_name: str):
        if self._enrich_agent is None:
            model = ChatOpenAI(
                api_key=self.settings.openai_api_key,
                base_url=self.settings.openai_base_url or None,
                model=model_name,
                use_responses_api=True,
            )
            self._enrich_agent = create_agent(model, response_format=EnrichResult)
        return self._enrich_agent

    def _fallback_enrich(self, *, article: dict[str, Any]) -> EnrichResult:
        """无 API Key 时的回退：直接使用英文原文。"""
        return EnrichResult(
            chinese_name=article["title"],
            chinese_abstract=article["abstract"],
        )

    def _build_review(self, *, article: dict[str, Any], collection: ArxivCollection) -> SyncReviewPayload:
        """兼容旧调用路径，内部委托给新的 _build_enrichment + _build_judgment。"""
        enrichment = self._build_enrichment(article=article)
        return self._build_judgment(article=article, collection=collection, enrichment=enrichment)

    def _judge_article(self, *, article: dict[str, Any], collection: ArxivCollection, model_name: str) -> JudgmentResult:
        arxiv_id = article.get("arxiv_id", "unknown")
        if not self.settings.openai_api_key:
            logger.info(
                "[judge] arxiv_id=%s collection=%s 无 API Key，使用关键词回退策略",
                arxiv_id,
                collection.name,
            )
            return self._fallback_judge(article=article, collection=collection)

        logger.info(
            "[judge] arxiv_id=%s collection=%s 开始生成 comment model=%s",
            arxiv_id,
            collection.name,
            model_name,
        )
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
            if isinstance(structured, JudgmentResult):
                judgment = structured
            else:
                judgment = JudgmentResult.model_validate(structured)
            logger.info(
                "[judge] arxiv_id=%s collection=%s 完成 worth_read=%s comment=%s",
                arxiv_id,
                collection.name,
                judgment.worth_read,
                (judgment.comment or "")[:80],
            )
            return judgment
        except Exception as exc:
            logger.warning(
                "[judge] arxiv_id=%s collection=%s 生成失败，使用回退策略 error=%s",
                arxiv_id,
                collection.name,
                exc,
            )
            return self._fallback_judge(article=article, collection=collection)

    def _get_judge_agent(self, model_name: str):
        if self._judge_agent is None:
            model = ChatOpenAI(
                api_key=self.settings.openai_api_key,
                base_url=self.settings.openai_base_url or None,
                model=model_name,
                use_responses_api=True,
            )
            self._judge_agent = create_agent(model, response_format=JudgmentResult)
        return self._judge_agent

    def _build_judger_prompt(self, collection: ArxivCollection) -> str:
        prefer = collection.prefer_keywords or "<none>"
        avoid = collection.avoid_keywords or "<none>"
        categories = ", ".join(collection.categories_json or []) or "<none>"
        return (
            "你是一个论文评判助手，需要根据收藏夹的研究偏好判断文章是否值得阅读，并返回结构化结果。\n"
            "输出字段必须包括：worth_read, comment。\n"
            f"收藏夹关注分类: {categories}\n"
            f"偏好关键词: {prefer}\n"
            f"不偏好关键词: {avoid}\n"
            "请严格判断，不要因为只有少量相关内容就默认推荐。"
        )

    def _fallback_judge(self, *, article: dict[str, Any], collection: ArxivCollection) -> JudgmentResult:
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
        return JudgmentResult(
            worth_read=worth_read,
            comment=comment,
        )

    def _analyze_source_metadata(self, article: dict[str, Any]) -> dict[str, Any]:
        arxiv_id = article.get("arxiv_id", "unknown")
        pdf_url = article.get("pdf_url")
        if not pdf_url:
            logger.debug("[analyze] arxiv_id=%s 跳过源码分析：缺少 pdf_url", arxiv_id)
            return {"status": "skipped", "reason": "missing_pdf_url"}

        src_url = str(pdf_url).replace("/pdf/", "/src/")
        logger.info("[analyze] arxiv_id=%s 开始下载源码包 src_url=%s", arxiv_id, src_url)
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

            logger.info(
                "[analyze] arxiv_id=%s 源码分析完成 tex_files=%d figure_files=%d",
                arxiv_id,
                tex_count,
                figure_count,
            )
            return {
                "status": "succeeded",
                "source_url": src_url,
                "tex_file_count": tex_count,
                "figure_file_count": figure_count,
                "metadata_ready": tex_count > 0,
            }
        except Exception as exc:
            logger.warning("[analyze] arxiv_id=%s 源码分析失败 error=%s", arxiv_id, exc)
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

"""历史数据回填脚本：从 arxiv_paper_reviews 聚合出全局 enrichment。

用法：
    python backend/scripts/backfill_enrichments.py [--dry-run]

逻辑：
    - 遍历所有 arxiv_papers
    - 若该 paper 已有 global_summary enrichment，跳过
    - 从该 paper 的所有 reviews 中取最新非空 title_zh / abstract_zh
    - 若多个 review 内容不同，记录到 raw_result_json.migration_candidates
    - 写入 arxiv_paper_enrichments
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.app.db.session import SessionLocal
from backend.app.models.discovery import ArxivPaper, ArxivPaperEnrichment, ArxivPaperReview


def _pick_best_value(values: list[str | None]) -> str | None:
    """从列表中取第一个非空值。"""
    for v in values:
        if v and v.strip():
            return v.strip()
    return None


def backfill(db: Session, *, dry_run: bool = False) -> None:
    stmt = (
        select(ArxivPaper)
        .options(
            selectinload(ArxivPaper.enrichments),
            selectinload(ArxivPaper.reviews),
        )
        .order_by(ArxivPaper.id.asc())
    )
    papers = list(db.scalars(stmt).all())
    print(f"共找到 {len(papers)} 篇论文，开始回填...")

    created = 0
    skipped = 0

    for paper in papers:
        # 已有 global_summary enrichment，跳过
        existing = next(
            (e for e in paper.enrichments if e.enrichment_type == "global_summary"),
            None,
        )
        if existing is not None:
            skipped += 1
            continue

        reviews: list[ArxivPaperReview] = sorted(
            paper.reviews, key=lambda r: r.updated_at, reverse=True
        )

        # 收集所有非空 title_zh / abstract_zh
        title_candidates = [r.title_zh for r in reviews if r.title_zh and r.title_zh.strip()]
        abstract_candidates = [r.abstract_zh for r in reviews if r.abstract_zh and r.abstract_zh.strip()]

        title_zh = _pick_best_value(title_candidates)
        abstract_zh = _pick_best_value(abstract_candidates)

        if title_zh is None and abstract_zh is None:
            # 没有任何可回填的内容，跳过
            skipped += 1
            continue

        # 记录候选值（用于审计）
        raw_result: dict = {"migration_source": "backfill_from_reviews"}
        unique_titles = list(dict.fromkeys(t for t in title_candidates if t))
        unique_abstracts = list(dict.fromkeys(a for a in abstract_candidates if a))
        if len(unique_titles) > 1:
            raw_result["migration_candidates"] = {
                "title_zh": unique_titles,
                "abstract_zh": unique_abstracts,
            }

        # 使用最新 review 的 model_name，若无则用 migration 标记
        model_name = reviews[0].model_name if reviews else "migration"

        print(
            f"  paper_id={paper.id} arxiv_id={paper.arxiv_id} "
            f"title_zh={'<有>' if title_zh else '<空>'} "
            f"abstract_zh={'<有>' if abstract_zh else '<空>'}"
        )

        if not dry_run:
            enrichment = ArxivPaperEnrichment(
                paper_id=paper.id,
                enrichment_type="global_summary",
                model_name=model_name,
                title_zh=title_zh,
                abstract_zh=abstract_zh,
                raw_result_json=raw_result,
            )
            db.add(enrichment)
            created += 1
        else:
            created += 1

    if not dry_run:
        db.commit()
        print(f"\n回填完成：新建 {created} 条 enrichment，跳过 {skipped} 条。")
    else:
        print(f"\n[dry-run] 预计新建 {created} 条 enrichment，跳过 {skipped} 条（未写入数据库）。")


def main() -> None:
    parser = argparse.ArgumentParser(description="回填历史 enrichment 数据")
    parser.add_argument("--dry-run", action="store_true", help="只打印，不写入数据库")
    args = parser.parse_args()

    db: Session = SessionLocal()
    try:
        backfill(db, dry_run=args.dry_run)
    finally:
        db.close()


if __name__ == "__main__":
    main()

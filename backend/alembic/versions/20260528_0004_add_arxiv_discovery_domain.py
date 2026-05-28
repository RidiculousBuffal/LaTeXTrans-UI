"""add arxiv discovery domain

Revision ID: 20260528_0004
Revises: 20260527_0003
Create Date: 2026-05-28 11:00:00
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260528_0004"
down_revision = "20260527_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "arxiv_papers",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("arxiv_id", sa.String(length=64), nullable=False, unique=True),
        sa.Column("primary_category", sa.String(length=64), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("scraped_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("title_en", sa.Text(), nullable=False),
        sa.Column("abstract_en", sa.Text(), nullable=False),
        sa.Column("authors_json", sa.JSON(), nullable=False),
        sa.Column("pdf_url", sa.String(length=512), nullable=True),
        sa.Column("abs_url", sa.String(length=512), nullable=True),
        sa.Column("subjects_json", sa.JSON(), nullable=False),
        sa.Column("comments", sa.Text(), nullable=True),
        sa.Column("source_run_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_arxiv_papers_arxiv_id", "arxiv_papers", ["arxiv_id"], unique=True)
    op.create_index(
        "ix_arxiv_papers_primary_category_run_date",
        "arxiv_papers",
        ["primary_category", "source_run_date"],
        unique=False,
    )

    op.create_table(
        "arxiv_collections",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("categories_json", sa.JSON(), nullable=False),
        sa.Column("prefer_keywords", sa.Text(), nullable=True),
        sa.Column("avoid_keywords", sa.Text(), nullable=True),
        sa.Column(
            "translation_mode",
            sa.Enum("manual", "auto", name="arxivcollectiontranslationmode", native_enum=False),
            nullable=False,
            server_default="manual",
        ),
        sa.Column("auto_translate_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_arxiv_collections_user_id", "arxiv_collections", ["user_id"], unique=False)
    op.create_index("ix_arxiv_collections_user_id_name", "arxiv_collections", ["user_id", "name"], unique=True)

    op.create_table(
        "arxiv_paper_reviews",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("paper_id", sa.Integer(), sa.ForeignKey("arxiv_papers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("collection_id", sa.Integer(), sa.ForeignKey("arxiv_collections.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "review_type",
            sa.Enum("daily_judge", name="arxivpaperreviewtype", native_enum=False),
            nullable=False,
            server_default="daily_judge",
        ),
        sa.Column("model_name", sa.String(length=128), nullable=False),
        sa.Column("worth_read", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("title_zh", sa.Text(), nullable=True),
        sa.Column("abstract_zh", sa.Text(), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("raw_result_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_arxiv_paper_reviews_paper_id", "arxiv_paper_reviews", ["paper_id"], unique=False)
    op.create_index("ix_arxiv_paper_reviews_collection_id", "arxiv_paper_reviews", ["collection_id"], unique=False)
    op.create_index(
        "ix_arxiv_paper_reviews_unique_scope",
        "arxiv_paper_reviews",
        ["paper_id", "collection_id", "review_type"],
        unique=True,
    )

    op.create_table(
        "arxiv_collection_items",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("collection_id", sa.Integer(), sa.ForeignKey("arxiv_collections.id", ondelete="CASCADE"), nullable=False),
        sa.Column("paper_id", sa.Integer(), sa.ForeignKey("arxiv_papers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("added_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "translate_decision",
            sa.Enum(
                "pending",
                "manual_requested",
                "auto_queued",
                "translated",
                name="arxivtranslatedecision",
                native_enum=False,
            ),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_arxiv_collection_items_collection_id", "arxiv_collection_items", ["collection_id"], unique=False)
    op.create_index("ix_arxiv_collection_items_paper_id", "arxiv_collection_items", ["paper_id"], unique=False)
    op.create_index(
        "ix_arxiv_collection_items_unique_pair",
        "arxiv_collection_items",
        ["collection_id", "paper_id"],
        unique=True,
    )

    op.create_table(
        "arxiv_paper_task_links",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("paper_id", sa.Integer(), sa.ForeignKey("arxiv_papers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("task_id", sa.String(length=36), sa.ForeignKey("translation_tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("link_type", sa.String(length=32), nullable=False, server_default="arxiv_id_match"),
        sa.Column("created_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_arxiv_paper_task_links_paper_id", "arxiv_paper_task_links", ["paper_id"], unique=False)
    op.create_index("ix_arxiv_paper_task_links_task_id", "arxiv_paper_task_links", ["task_id"], unique=False)
    op.create_index(
        "ix_arxiv_paper_task_links_unique_pair",
        "arxiv_paper_task_links",
        ["paper_id", "task_id"],
        unique=True,
    )

    op.create_table(
        "arxiv_discovery_runs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("trigger_source", sa.String(length=32), nullable=False, server_default="manual"),
        sa.Column("requested_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("source_run_date", sa.Date(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("PENDING", "RUNNING", "SUCCEEDED", "FAILED", name="arxivdiscoveryrunstatus", native_enum=False),
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column("categories_json", sa.JSON(), nullable=False),
        sa.Column("total_papers", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_reviews", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_worth_read", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("summary_json", sa.JSON(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index(
        "ix_arxiv_discovery_runs_status_created_at",
        "arxiv_discovery_runs",
        ["status", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_arxiv_discovery_runs_source_run_date",
        "arxiv_discovery_runs",
        ["source_run_date"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_arxiv_discovery_runs_source_run_date", table_name="arxiv_discovery_runs")
    op.drop_index("ix_arxiv_discovery_runs_status_created_at", table_name="arxiv_discovery_runs")
    op.drop_table("arxiv_discovery_runs")

    op.drop_index("ix_arxiv_paper_task_links_unique_pair", table_name="arxiv_paper_task_links")
    op.drop_index("ix_arxiv_paper_task_links_task_id", table_name="arxiv_paper_task_links")
    op.drop_index("ix_arxiv_paper_task_links_paper_id", table_name="arxiv_paper_task_links")
    op.drop_table("arxiv_paper_task_links")

    op.drop_index("ix_arxiv_collection_items_unique_pair", table_name="arxiv_collection_items")
    op.drop_index("ix_arxiv_collection_items_paper_id", table_name="arxiv_collection_items")
    op.drop_index("ix_arxiv_collection_items_collection_id", table_name="arxiv_collection_items")
    op.drop_table("arxiv_collection_items")

    op.drop_index("ix_arxiv_paper_reviews_unique_scope", table_name="arxiv_paper_reviews")
    op.drop_index("ix_arxiv_paper_reviews_collection_id", table_name="arxiv_paper_reviews")
    op.drop_index("ix_arxiv_paper_reviews_paper_id", table_name="arxiv_paper_reviews")
    op.drop_table("arxiv_paper_reviews")

    op.drop_index("ix_arxiv_collections_user_id_name", table_name="arxiv_collections")
    op.drop_index("ix_arxiv_collections_user_id", table_name="arxiv_collections")
    op.drop_table("arxiv_collections")

    op.drop_index("ix_arxiv_papers_primary_category_run_date", table_name="arxiv_papers")
    op.drop_index("ix_arxiv_papers_arxiv_id", table_name="arxiv_papers")
    op.drop_table("arxiv_papers")

"""add arxiv paper enrichments table

Revision ID: 20260530_0005
Revises: 20260528_0004
Create Date: 2026-05-30 10:00:00
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260530_0005"
down_revision = "20260528_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "arxiv_paper_enrichments",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "paper_id",
            sa.Integer(),
            sa.ForeignKey("arxiv_papers.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("enrichment_type", sa.String(length=64), nullable=False, server_default="global_summary"),
        sa.Column("model_name", sa.String(length=128), nullable=False),
        sa.Column("title_zh", sa.Text(), nullable=True),
        sa.Column("abstract_zh", sa.Text(), nullable=True),
        sa.Column("summary_zh", sa.Text(), nullable=True),
        sa.Column("keywords_json", sa.JSON(), nullable=True),
        sa.Column("raw_result_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_arxiv_paper_enrichments_paper_id", "arxiv_paper_enrichments", ["paper_id"], unique=False)
    op.create_index(
        "ix_arxiv_paper_enrichments_unique_scope",
        "arxiv_paper_enrichments",
        ["paper_id", "enrichment_type"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_arxiv_paper_enrichments_unique_scope", table_name="arxiv_paper_enrichments")
    op.drop_index("ix_arxiv_paper_enrichments_paper_id", table_name="arxiv_paper_enrichments")
    op.drop_table("arxiv_paper_enrichments")

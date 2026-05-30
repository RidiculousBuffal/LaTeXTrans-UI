"""drop title_zh and abstract_zh from arxiv_paper_reviews

Revision ID: 20260530_0006
Revises: 20260530_0005
Create Date: 2026-05-30 11:00:00

Phase 5: title_zh / abstract_zh 已迁移到 arxiv_paper_enrichments，
从 arxiv_paper_reviews 中移除冗余字段。
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260530_0006"
down_revision = "20260530_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("arxiv_paper_reviews", "title_zh")
    op.drop_column("arxiv_paper_reviews", "abstract_zh")


def downgrade() -> None:
    op.add_column("arxiv_paper_reviews", sa.Column("title_zh", sa.Text(), nullable=True))
    op.add_column("arxiv_paper_reviews", sa.Column("abstract_zh", sa.Text(), nullable=True))

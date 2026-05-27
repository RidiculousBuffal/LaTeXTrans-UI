"""add babeldoc task support

Revision ID: 20260527_0002
Revises: 20260526_0001
Create Date: 2026-05-27 11:30:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260527_0002"
down_revision = "20260526_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "translation_tasks",
        sa.Column(
            "engine",
            sa.Enum("latex", "babeldoc", name="taskengine", native_enum=False),
            nullable=False,
            server_default="latex",
        ),
    )
    op.alter_column("translation_tasks", "engine", server_default=None)

    with op.batch_alter_table("translation_tasks") as batch_op:
        batch_op.alter_column(
            "source_type",
            existing_type=sa.Enum("arxiv", "upload", name="tasksourcetype", native_enum=False),
            type_=sa.Enum("arxiv", "upload", "pdf_upload", name="tasksourcetype", native_enum=False),
            existing_nullable=False,
        )

    with op.batch_alter_table("task_artifacts") as batch_op:
        batch_op.alter_column(
            "artifact_type",
            existing_type=sa.Enum(
                "SOURCE_ARCHIVE",
                "EXTRACTED_SOURCE",
                "TRANSLATED_PROJECT",
                "FINAL_PDF",
                "LOG",
                "METADATA",
                "INTERMEDIATE_JSON",
                name="taskartifacttype",
                native_enum=False,
            ),
            type_=sa.Enum(
                "SOURCE_ARCHIVE",
                "SOURCE_PDF",
                "EXTRACTED_SOURCE",
                "TRANSLATED_PROJECT",
                "FINAL_PDF",
                "TRANSLATED_PDF",
                "BABELDOC_OUTPUT",
                "LOG",
                "METADATA",
                "INTERMEDIATE_JSON",
                name="taskartifacttype",
                native_enum=False,
            ),
            existing_nullable=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("task_artifacts") as batch_op:
        batch_op.alter_column(
            "artifact_type",
            existing_type=sa.Enum(
                "SOURCE_ARCHIVE",
                "SOURCE_PDF",
                "EXTRACTED_SOURCE",
                "TRANSLATED_PROJECT",
                "FINAL_PDF",
                "TRANSLATED_PDF",
                "BABELDOC_OUTPUT",
                "LOG",
                "METADATA",
                "INTERMEDIATE_JSON",
                name="taskartifacttype",
                native_enum=False,
            ),
            type_=sa.Enum(
                "SOURCE_ARCHIVE",
                "EXTRACTED_SOURCE",
                "TRANSLATED_PROJECT",
                "FINAL_PDF",
                "LOG",
                "METADATA",
                "INTERMEDIATE_JSON",
                name="taskartifacttype",
                native_enum=False,
            ),
            existing_nullable=False,
        )

    with op.batch_alter_table("translation_tasks") as batch_op:
        batch_op.alter_column(
            "source_type",
            existing_type=sa.Enum("arxiv", "upload", "pdf_upload", name="tasksourcetype", native_enum=False),
            type_=sa.Enum("arxiv", "upload", name="tasksourcetype", native_enum=False),
            existing_nullable=False,
        )

    op.drop_column("translation_tasks", "engine")

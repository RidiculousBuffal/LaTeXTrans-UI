"""init translation tables

Revision ID: 20260526_0001
Revises:
Create Date: 2026-05-26 16:20:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260526_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "translation_tasks",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("task_name", sa.String(length=255), nullable=False),
        sa.Column("source_type", sa.Enum("arxiv", "upload", name="tasksourcetype", native_enum=False), nullable=False),
        sa.Column("arxiv_id", sa.String(length=64), nullable=True),
        sa.Column("source_archive_name", sa.String(length=255), nullable=True),
        sa.Column("source_language", sa.String(length=16), nullable=False),
        sa.Column("target_language", sa.String(length=16), nullable=False),
        sa.Column("model_name", sa.String(length=128), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "PENDING",
                "DOWNLOADING",
                "PARSING",
                "TRANSLATING",
                "VALIDATING",
                "GENERATING",
                "SUCCEEDED",
                "FAILED",
                "CANCELED",
                name="taskstatus",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("current_stage", sa.String(length=64), nullable=False),
        sa.Column("progress_percent", sa.Integer(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(length=128), nullable=False),
        sa.Column("workspace_dir", sa.String(length=512), nullable=True),
        sa.Column("output_dir", sa.String(length=512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("canceled_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_translation_tasks")),
    )
    op.create_index(
        "ix_translation_tasks_status_created_at",
        "translation_tasks",
        ["status", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_translation_tasks_arxiv_id_created_at",
        "translation_tasks",
        ["arxiv_id", "created_at"],
        unique=False,
    )

    op.create_table(
        "task_artifacts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("task_id", sa.String(length=36), nullable=False),
        sa.Column(
            "artifact_type",
            sa.Enum(
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
            nullable=False,
        ),
        sa.Column("object_key", sa.String(length=512), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=128), nullable=True),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["task_id"], ["translation_tasks.id"], name=op.f("fk_task_artifacts_task_id_translation_tasks"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_task_artifacts")),
    )

    op.create_table(
        "task_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("task_id", sa.String(length=36), nullable=False),
        sa.Column("stage", sa.String(length=64), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "PENDING",
                "DOWNLOADING",
                "PARSING",
                "TRANSLATING",
                "VALIDATING",
                "GENERATING",
                "SUCCEEDED",
                "FAILED",
                "CANCELED",
                name="taskstatus",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("message", sa.String(length=500), nullable=False),
        sa.Column("details_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["task_id"], ["translation_tasks.id"], name=op.f("fk_task_events_task_id_translation_tasks"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_task_events")),
    )
    op.create_index(
        "ix_task_events_task_id_created_at",
        "task_events",
        ["task_id", "created_at"],
        unique=False,
    )

    op.create_table(
        "task_configs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("task_id", sa.String(length=36), nullable=False),
        sa.Column("env_profile", sa.String(length=64), nullable=False),
        sa.Column("config_snapshot_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["task_id"], ["translation_tasks.id"], name=op.f("fk_task_configs_task_id_translation_tasks"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_task_configs")),
    )


def downgrade() -> None:
    op.drop_table("task_configs")
    op.drop_index("ix_task_events_task_id_created_at", table_name="task_events")
    op.drop_table("task_events")
    op.drop_table("task_artifacts")
    op.drop_index("ix_translation_tasks_arxiv_id_created_at", table_name="translation_tasks")
    op.drop_index("ix_translation_tasks_status_created_at", table_name="translation_tasks")
    op.drop_table("translation_tasks")

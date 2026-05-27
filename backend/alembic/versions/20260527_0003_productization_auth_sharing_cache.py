"""productization: users, quota, sharing, cache, task extensions

Revision ID: 20260527_0003
Revises: 20260527_0002
Create Date: 2026-05-27 12:00:00
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260527_0003"
down_revision = "20260527_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # users
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("username", sa.String(64), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(256), nullable=False),
        sa.Column("role", sa.Enum("user", "admin", name="userrole", native_enum=False), nullable=False, server_default="user"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_users_username", "users", ["username"], unique=True)

    # user_quota_accounts
    op.create_table(
        "user_quota_accounts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("balance", sa.Integer, nullable=False, server_default="0"),
        sa.Column("total_granted", sa.Integer, nullable=False, server_default="0"),
        sa.Column("total_consumed", sa.Integer, nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_user_quota_accounts_user_id", "user_quota_accounts", ["user_id"], unique=True)

    # user_quota_ledger
    op.create_table(
        "user_quota_ledger",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("account_id", sa.String(36), sa.ForeignKey("user_quota_accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("delta", sa.Integer, nullable=False),
        sa.Column("balance_after", sa.Integer, nullable=False),
        sa.Column("reason_type", sa.String(64), nullable=False),
        sa.Column("reason_ref_id", sa.String(36), nullable=True),
        sa.Column("operator_user_id", sa.String(36), nullable=True),
        sa.Column("metadata_json", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # task_share_grants
    op.create_table(
        "task_share_grants",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("task_id", sa.String(36), sa.ForeignKey("translation_tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("grantee_user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("granted_by_user_id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_task_share_grants_task_grantee", "task_share_grants", ["task_id", "grantee_user_id"], unique=True)

    # translation_cache_entries
    op.create_table(
        "translation_cache_entries",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("cache_key", sa.String(64), nullable=False, unique=True),
        sa.Column("engine", sa.String(32), nullable=False),
        sa.Column("normalized_arxiv_id", sa.String(64), nullable=True),
        sa.Column("source_file_hash", sa.String(64), nullable=True),
        sa.Column("source_fingerprint_type", sa.String(16), nullable=False),
        sa.Column("source_language", sa.String(16), nullable=False),
        sa.Column("target_language", sa.String(16), nullable=False),
        sa.Column("model_name", sa.String(128), nullable=False),
        sa.Column("options_hash", sa.String(64), nullable=False),
        sa.Column("cache_version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("status", sa.Enum("BUILDING", "READY", "FAILED", "INVALIDATED", name="cacheentrystatus", native_enum=False), nullable=False, server_default="BUILDING"),
        sa.Column("canonical_task_id", sa.String(36), nullable=True),
        sa.Column("artifact_manifest_json", sa.JSON, nullable=True),
        sa.Column("hit_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("last_hit_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_cache_entries_cache_key", "translation_cache_entries", ["cache_key"], unique=True)
    op.create_index("ix_cache_entries_arxiv_id", "translation_cache_entries", ["normalized_arxiv_id"])
    op.create_index("ix_cache_entries_file_hash", "translation_cache_entries", ["source_file_hash"])

    # translation_tasks extensions
    op.add_column("translation_tasks", sa.Column("owner_user_id", sa.String(36), nullable=True))
    op.add_column("translation_tasks", sa.Column("visibility", sa.String(16), nullable=False, server_default="private"))
    op.add_column("translation_tasks", sa.Column("source_file_hash", sa.String(64), nullable=True))
    op.add_column("translation_tasks", sa.Column("cache_entry_id", sa.String(36), nullable=True))
    op.add_column("translation_tasks", sa.Column("result_source", sa.String(16), nullable=False, server_default="EXECUTED"))
    op.add_column("translation_tasks", sa.Column("quota_cost", sa.Integer, nullable=False, server_default="1"))
    op.add_column("translation_tasks", sa.Column("quota_charged", sa.Boolean, nullable=False, server_default="0"))
    op.add_column("translation_tasks", sa.Column("shared_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_translation_tasks_owner_user_id", "translation_tasks", ["owner_user_id"])


def downgrade() -> None:
    op.drop_index("ix_translation_tasks_owner_user_id", "translation_tasks")
    for col in ["shared_at", "quota_charged", "quota_cost", "result_source", "cache_entry_id", "source_file_hash", "visibility", "owner_user_id"]:
        op.drop_column("translation_tasks", col)

    op.drop_index("ix_cache_entries_file_hash", "translation_cache_entries")
    op.drop_index("ix_cache_entries_arxiv_id", "translation_cache_entries")
    op.drop_index("ix_cache_entries_cache_key", "translation_cache_entries")
    op.drop_table("translation_cache_entries")

    op.drop_index("ix_task_share_grants_task_grantee", "task_share_grants")
    op.drop_table("task_share_grants")
    op.drop_table("user_quota_ledger")
    op.drop_index("ix_user_quota_accounts_user_id", "user_quota_accounts")
    op.drop_table("user_quota_accounts")
    op.drop_index("ix_users_username", "users")
    op.drop_table("users")

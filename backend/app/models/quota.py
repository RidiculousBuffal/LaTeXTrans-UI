from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, Integer, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base


class UserQuotaAccount(Base):
    __tablename__ = "user_quota_accounts"
    __table_args__ = (Index("ix_user_quota_accounts_user_id", "user_id", unique=True),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    balance: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_granted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_consumed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=func.now(), onupdate=func.now()
    )

    user: Mapped["backend.app.models.user.User"] = relationship(back_populates="quota_account")
    ledger_entries: Mapped[list[UserQuotaLedger]] = relationship(
        back_populates="account", cascade="all, delete-orphan", order_by="UserQuotaLedger.created_at"
    )


class UserQuotaLedger(Base):
    __tablename__ = "user_quota_ledger"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    account_id: Mapped[str] = mapped_column(
        ForeignKey("user_quota_accounts.id", ondelete="CASCADE"), nullable=False
    )
    delta: Mapped[int] = mapped_column(Integer, nullable=False)
    balance_after: Mapped[int] = mapped_column(Integer, nullable=False)
    reason_type: Mapped[str] = mapped_column(String(64), nullable=False)
    reason_ref_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    operator_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=func.now())

    account: Mapped[UserQuotaAccount] = relationship(back_populates="ledger_entries")

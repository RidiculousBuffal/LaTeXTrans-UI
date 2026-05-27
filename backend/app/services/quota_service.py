from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.models.quota import UserQuotaAccount, UserQuotaLedger
from backend.app.models.user import User


class QuotaService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.settings = get_settings()

    def initialize_quota(self, user: User, operator_user_id: str | None = None) -> UserQuotaAccount:
        """Create quota account with initial grant for a new user."""
        initial = self.settings.default_user_translation_quota
        account = UserQuotaAccount(
            user_id=user.id,
            balance=initial,
            total_granted=initial,
            total_consumed=0,
        )
        self.db.add(account)
        self.db.flush()  # get account.id
        ledger = UserQuotaLedger(
            user_id=user.id,
            account_id=account.id,
            delta=initial,
            balance_after=initial,
            reason_type="initial_grant",
            operator_user_id=operator_user_id,
        )
        self.db.add(ledger)
        return account

    def check_and_deduct(self, user: User, task_id: str, cost: int = 1) -> None:
        """Check quota and deduct atomically. Raises 402 if insufficient."""
        account = self._require_account(user)
        if account.balance < cost:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"Insufficient quota. Balance: {account.balance}, required: {cost}.",
            )
        account.balance -= cost
        account.total_consumed += cost
        ledger = UserQuotaLedger(
            user_id=user.id,
            account_id=account.id,
            delta=-cost,
            balance_after=account.balance,
            reason_type="task_deduct",
            reason_ref_id=task_id,
        )
        self.db.add(ledger)

    def refund(self, user: User, task_id: str, cost: int = 1) -> None:
        """Refund quota for a task that did not consume resources."""
        account = self._require_account(user)
        account.balance += cost
        account.total_consumed = max(0, account.total_consumed - cost)
        ledger = UserQuotaLedger(
            user_id=user.id,
            account_id=account.id,
            delta=cost,
            balance_after=account.balance,
            reason_type="task_refund",
            reason_ref_id=task_id,
        )
        self.db.add(ledger)

    def admin_adjust(
        self, user: User, delta: int, reason: str, operator_user_id: str
    ) -> UserQuotaAccount:
        """Admin quota adjustment."""
        account = self._require_account(user)
        account.balance += delta
        if delta > 0:
            account.total_granted += delta
        else:
            account.total_consumed += abs(delta)
        ledger = UserQuotaLedger(
            user_id=user.id,
            account_id=account.id,
            delta=delta,
            balance_after=account.balance,
            reason_type="admin_adjust",
            operator_user_id=operator_user_id,
            metadata_json={"reason": reason},
        )
        self.db.add(ledger)
        return account

    def get_balance(self, user: User) -> int:
        account = self.db.query(UserQuotaAccount).filter_by(user_id=user.id).first()
        return account.balance if account else 0

    def _require_account(self, user: User) -> UserQuotaAccount:
        account = self.db.query(UserQuotaAccount).filter_by(user_id=user.id).with_for_update().first()
        if not account:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Quota account not found.")
        return account

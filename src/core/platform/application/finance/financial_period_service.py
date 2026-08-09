"""Application boundary for organization financial periods."""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import date, datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)
from src.core.platform.application.tenant.tenancy import TenantContextService
from src.core.platform.common.exceptions import (
    BusinessRuleError,
    ConcurrencyError,
    NotFoundError,
    ValidationError,
)
from src.core.platform.contract.finance import FinancialPeriodRepository
from src.core.platform.finance.periods import FinancialPeriod, FinancialPeriodStatus
from src.core.shared.audit import record_audit_entry


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class FinancialPeriodService:
    """Tenant-safe period catalog and normal-posting policy.

    Reopen and late-adjustment commands are intentionally absent. They require
    an explicit authority and separation-of-duties decision before exposure.
    """

    def __init__(
        self,
        *,
        session: Session,
        period_repo: FinancialPeriodRepository,
        tenant_context_service: TenantContextService,
        user_session=None,
        enterprise_audit_service=None,
        now_provider: Callable[[], datetime] = _utc_now,
    ) -> None:
        self._session = session
        self._period_repo = period_repo
        self._tenant_context_service = tenant_context_service
        self._user_session = user_session
        self._enterprise_audit_service = enterprise_audit_service
        self._now_provider = now_provider

    def list_periods(
        self,
        *,
        fiscal_year: int | None = None,
        status: FinancialPeriodStatus | str | None = None,
    ) -> list[FinancialPeriod]:
        require_permission(
            self._user_session,
            "finance.read",
            operation_label="list financial periods",
        )
        try:
            resolved_status = FinancialPeriodStatus(status) if status is not None else None
        except ValueError as exc:
            raise ValidationError(
                "Financial period status is invalid.",
                code="FINANCIAL_PERIOD_STATUS_INVALID",
            ) from exc
        return self._period_repo.list(
            fiscal_year=fiscal_year,
            status=resolved_status,
        )

    def get_period(self, period_id: str) -> FinancialPeriod:
        require_permission(
            self._user_session,
            "finance.read",
            operation_label="view financial period",
        )
        return self._require_period(period_id)

    def create_period(
        self,
        *,
        code: str,
        name: str,
        fiscal_year: int,
        period_number: int,
        start_date: date,
        end_date: date,
    ) -> FinancialPeriod:
        require_permission(
            self._user_session,
            "finance.manage",
            operation_label="create financial period",
        )
        context = self._tenant_context_service.require_active_scope_ids(
            operation_label="create financial period"
        )
        period = FinancialPeriod.create(
            tenant_id=context.tenant_id,
            organization_id=context.organization_id,
            code=code,
            name=name,
            fiscal_year=fiscal_year,
            period_number=period_number,
            start_date=start_date,
            end_date=end_date,
            actor_id=self._actor_id(),
            now=self._now(),
        )
        try:
            with self._session.begin_nested():
                self._period_repo.lock_catalog()
                self._require_non_overlapping(period.start_date, period.end_date)
                self._period_repo.add(period)
                self._session.flush()
        except IntegrityError as exc:
            raise BusinessRuleError(
                "A financial period with this code or fiscal year/number already exists.",
                code="FINANCIAL_PERIOD_DUPLICATE",
            ) from exc
        self._record_audit("create", period, old=None)
        self._session.commit()
        return period

    def update_period(
        self,
        period_id: str,
        *,
        expected_version: int,
        code: str | None = None,
        name: str | None = None,
        fiscal_year: int | None = None,
        period_number: int | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> FinancialPeriod:
        require_permission(
            self._user_session,
            "finance.manage",
            operation_label="update financial period",
        )
        self._period_repo.lock_catalog()
        current = self._require_period(period_id)
        self._require_expected_version(current, expected_version)
        old_value = self._audit_value(current)
        current.update_definition(
            actor_id=self._actor_id(),
            now=self._now(),
            code=code,
            name=name,
            fiscal_year=fiscal_year,
            period_number=period_number,
            start_date=start_date,
            end_date=end_date,
        )
        self._require_non_overlapping(
            current.start_date,
            current.end_date,
            exclude_period_id=current.id,
        )
        try:
            with self._session.begin_nested():
                self._period_repo.update(current, expected_version=expected_version)
                self._session.flush()
        except IntegrityError as exc:
            raise BusinessRuleError(
                "A financial period with this code or fiscal year/number already exists.",
                code="FINANCIAL_PERIOD_DUPLICATE",
            ) from exc
        self._record_audit_value("update", current, old_value=old_value)
        self._session.commit()
        return current

    def close_period(self, period_id: str, *, expected_version: int) -> FinancialPeriod:
        return self._transition(
            period_id,
            expected_version=expected_version,
            operation="close",
        )

    def lock_period(self, period_id: str, *, expected_version: int) -> FinancialPeriod:
        return self._transition(
            period_id,
            expected_version=expected_version,
            operation="lock",
        )

    def require_open_period_for_date(self, posting_date: date) -> FinancialPeriod:
        """Resolve and validate the period used by a normal financial posting."""
        require_permission(
            self._user_session,
            "finance.read",
            operation_label="resolve financial posting period",
        )
        return self._resolve_open_period_for_date(posting_date)

    def require_open_period_for_integration(self, posting_date: date) -> FinancialPeriod:
        """Resolve an open period for an already-authenticated trusted consumer."""
        return self._resolve_open_period_for_date(posting_date)

    def _resolve_open_period_for_date(self, posting_date: date) -> FinancialPeriod:
        if not isinstance(posting_date, date) or isinstance(posting_date, datetime):
            raise ValidationError(
                "Posting date must be a valid date.",
                code="FINANCIAL_PERIOD_DATE_INVALID",
            )
        period = self._period_repo.find_for_date(posting_date)
        if period is None:
            raise BusinessRuleError(
                "No financial period is configured for the posting date.",
                code="FINANCIAL_PERIOD_NOT_CONFIGURED",
            )
        period.require_normal_posting()
        return period

    def _transition(
        self,
        period_id: str,
        *,
        expected_version: int,
        operation: str,
    ) -> FinancialPeriod:
        require_permission(
            self._user_session,
            "finance.manage",
            operation_label=f"{operation} financial period",
        )
        self._period_repo.lock_catalog()
        current = self._require_period(period_id)
        self._require_expected_version(current, expected_version)
        old_value = self._audit_value(current)
        transition = current.close if operation == "close" else current.lock
        transition(actor_id=self._actor_id(), now=self._now())
        self._period_repo.update(current, expected_version=expected_version)
        self._record_audit_value(operation, current, old_value=old_value)
        self._session.commit()
        return current

    def _require_period(self, period_id: str) -> FinancialPeriod:
        period = self._period_repo.get(period_id)
        if period is None:
            raise NotFoundError(
                "Financial period not found.",
                code="FINANCIAL_PERIOD_NOT_FOUND",
            )
        return period

    def _require_non_overlapping(
        self,
        start_date: date,
        end_date: date,
        *,
        exclude_period_id: str | None = None,
    ) -> None:
        if self._period_repo.overlaps(
            start_date=start_date,
            end_date=end_date,
            exclude_period_id=exclude_period_id,
        ):
            raise BusinessRuleError(
                "Financial periods cannot overlap within an organization.",
                code="FINANCIAL_PERIOD_OVERLAP",
            )

    @staticmethod
    def _require_expected_version(period: FinancialPeriod, expected_version: int) -> None:
        if period.version != expected_version:
            raise ConcurrencyError(
                "Financial period changed since you opened it.",
                code="STALE_WRITE",
            )

    def _actor_id(self) -> str:
        principal = getattr(self._user_session, "principal", None)
        actor_id = getattr(principal, "user_id", None)
        if not actor_id:
            raise BusinessRuleError(
                "An authenticated actor is required for financial-period changes.",
                code="FINANCIAL_PERIOD_ACTOR_REQUIRED",
            )
        return str(actor_id)

    def _now(self) -> datetime:
        value = self._now_provider()
        if value.tzinfo is None or value.utcoffset() is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    def _record_audit(
        self,
        operation: str,
        period: FinancialPeriod,
        *,
        old: FinancialPeriod | None,
    ) -> None:
        self._record_audit_value(
            operation,
            period,
            old_value=self._audit_value(old),
        )

    def _record_audit_value(
        self,
        operation: str,
        period: FinancialPeriod,
        *,
        old_value: str | None,
    ) -> None:
        record_audit_entry(
            self,
            operation=f"financial_period.{operation}",
            entity_type="financial_period",
            entity_id=period.id,
            module="platform_finance",
            old_value=old_value,
            new_value=self._audit_value(period),
            organization_id=period.organization_id,
            source="application",
            severity="high",
            compliance_tag="financial",
            metadata={"action": operation},
            commit=False,
            fail_closed=True,
        )

    @staticmethod
    def _audit_value(period: FinancialPeriod | None) -> str | None:
        if period is None:
            return None
        return json.dumps(
            {
                "code": period.code,
                "name": period.name,
                "fiscal_year": period.fiscal_year,
                "period_number": period.period_number,
                "start_date": period.start_date.isoformat(),
                "end_date": period.end_date.isoformat(),
                "status": period.status.value,
                "closed_by": period.closed_by,
                "closed_at": period.closed_at.isoformat() if period.closed_at else None,
                "locked_by": period.locked_by,
                "locked_at": period.locked_at.isoformat() if period.locked_at else None,
                "version": period.version,
            },
            sort_keys=True,
        )


__all__ = ["FinancialPeriodService"]

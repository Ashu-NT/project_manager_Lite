from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.core.modules.project_management.access.scope_permissions import (
    require_project_permission,
)
from src.core.modules.project_management.application.common.module_guard import (
    ProjectManagementModuleGuardMixin,
)
from src.core.modules.project_management.application.financials.cost.entries.audit import (
    record_project_cost_entry_audit,
)
from src.core.modules.project_management.application.financials.cost.entries.capabilities import (
    is_manual_actual_entry,
)
from src.core.modules.project_management.application.financials.cost.entries.cost_entry_events import (
    CostEntryReversed,
    CostEntryStatusChanged,
    CostEntryStatusChangeType,
)
from src.core.modules.project_management.application.financials.cost.entries.manual_source import (
    build_manual_source,
)
from src.core.modules.project_management.contracts.financial_sources.reference import (
    FinancialSourceReference,
)
from src.core.modules.project_management.contracts.repositories.finance.configuration.financial_configuration import (
    ProjectFinancialProfileRepository,
)
from src.core.modules.project_management.contracts.repositories.finance.cost_entries.cost_entry import (
    ProjectCostEntryRepository,
)
from src.core.modules.project_management.domain.financials.configuration import (
    FinancialProfileStatus,
)
from src.core.modules.project_management.domain.financials.cost_entry import (
    ProjectCostEntry,
)
from src.core.modules.project_management.domain.identifiers import generate_id
from src.core.platform.application.finance.queries.financial_period_query import (
    FinancialPeriodQueryHandler,
)
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)
from src.core.platform.application.tenant.tenancy.tenant_context import (
    TenantContextService,
)
from src.core.platform.common.exceptions import (
    BusinessRuleError,
    ConcurrencyError,
    NotFoundError,
    ValidationError,
)
from src.core.platform.domain.finance import EXCHANGE_RATE_STORAGE, Money
from src.core.shared.time.clock import CalendarClock

if TYPE_CHECKING:
    pass


class ProjectCostEntryPostingCommandHandler(ProjectManagementModuleGuardMixin):
    """Caller-owned actual-cost posting commands."""

    def __init__(
        self,
        *,
        session: Session,
        entry_repo: ProjectCostEntryRepository,
        financial_profile_repo: ProjectFinancialProfileRepository,
        financial_period_queries: FinancialPeriodQueryHandler,
        clock: CalendarClock,
        user_session=None,
        enterprise_audit_service=None,
        activity_service=None,
        module_catalog_service=None,
        tenant_context_service: TenantContextService | None = None,
        record_event: Callable[[object], None] | None = None,
    ) -> None:
        self._session = session
        self._entry_repo = entry_repo
        self._financial_profile_repo = financial_profile_repo
        self._financial_period_queries = financial_period_queries
        self._clock = clock
        self._user_session = user_session
        self._enterprise_audit_service = enterprise_audit_service
        self._activity_service = activity_service
        self._module_catalog_service = module_catalog_service
        self._tenant_context_service = tenant_context_service
        self._record_event = record_event

    def post(
        self,
        entry_id: str,
        *,
        expected_version: int,
        posting_date: date,
        exchange_rate: Decimal | None = None,
        exchange_rate_date: date | None = None,
        exchange_rate_source: str | None = None,
        exchange_rate_captured_at: datetime | None = None,
    ) -> ProjectCostEntry:
        entry = self._require_entry(entry_id)
        self._require_manual_interactive_entry(entry, operation="post")
        self._require_command_permission(
            entry.project_id, "project_cost.post", "post project cost entry"
        )
        self._require_expected_version(entry, expected_version)
        profile = self._require_active_profile(entry.project_id)
        del profile
        period = self._financial_period_queries.require_open_period_for_date(
            posting_date
        )
        context = self._require_full_context("post project cost entry")
        base_currency = context.organization.base_currency
        rate, rate_date, rate_source, captured_at = self._resolve_fx_snapshot(
            entry=entry,
            base_currency=base_currency,
            posting_date=posting_date,
            exchange_rate=exchange_rate,
            exchange_rate_date=exchange_rate_date,
            exchange_rate_source=exchange_rate_source,
            exchange_rate_captured_at=exchange_rate_captured_at,
        )
        base_money = Money.of(entry.amount * rate, base_currency).rounded()
        entry.post(
            actor_id=self._actor_id(),
            occurred_at=self._clock.now(),
            posting_date=posting_date,
            financial_period_id=period.id,
            base_money=base_money,
            exchange_rate=rate,
            exchange_rate_date=rate_date,
            exchange_rate_source=rate_source,
            exchange_rate_captured_at=captured_at,
        )
        self._entry_repo.update(entry, expected_row_version=expected_version)
        self._record_audit("post", entry)
        event = CostEntryStatusChanged(
            tenant_id=entry.tenant_id,
            organization_id=entry.organization_id,
            project_id=entry.project_id,
            cost_entry_id=entry.id,
            change_type=CostEntryStatusChangeType.POSTED,
            occurred_at=entry.updated_at,
        )
        if self._record_event is not None:
            self._record_event(event)
        self._session.flush()
        return entry

    def reverse(
        self,
        entry_id: str,
        *,
        expected_version: int,
        command_id: str,
        posting_date: date,
        reason: str,
    ) -> ProjectCostEntry:
        entry = self._require_entry(entry_id, for_update=True)
        self._require_manual_interactive_entry(entry, operation="reverse")
        self._require_command_permission(
            entry.project_id, "project_cost.reverse", "reverse project cost entry"
        )
        source = build_manual_source(
            tenant_id=entry.tenant_id,
            organization_id=entry.organization_id,
            project_id=entry.project_id,
            command_id=command_id,
            content={
                "operation": "reverse",
                "entry_id": entry.id,
                "expected_version": expected_version,
                "posting_date": posting_date.isoformat(),
                "reason": str(reason or "").strip(),
            },
        )
        existing = self._entry_repo.get_by_idempotency_key(source.idempotency_key)
        if existing is not None:
            return self._resolve_replay(existing, source)
        self._require_expected_version(entry, expected_version)
        period = self._financial_period_queries.require_open_period_for_date(
            posting_date
        )
        actor_id = self._actor_id()
        now = self._clock.now()
        reversal_id = generate_id()
        reversal = ProjectCostEntry.create_posted_reversal(
            original=entry,
            reversal_id=reversal_id,
            description=str(reason or "").strip() or f"Reversal of {entry.description}",
            source=source,
            posting_date=posting_date,
            financial_period_id=period.id,
            actor_id=actor_id,
            occurred_at=now,
        )
        try:
            with self._session.begin_nested():
                self._entry_repo.add(reversal)
                self._entry_repo.flush()
                entry.mark_reversed(
                    reversal_entry_id=reversal.id,
                    actor_id=actor_id,
                    occurred_at=now,
                )
                self._entry_repo.update(entry, expected_row_version=expected_version)
                self._entry_repo.flush()
        except IntegrityError as exc:
            raise BusinessRuleError(
                "This project cost entry has already been reversed or the reversal source conflicts.",
                code="PROJECT_COST_ENTRY_REVERSAL_CONFLICT",
            ) from exc
        self._record_audit("reverse_original", entry)
        self._record_audit("create_reversal", reversal)
        event = CostEntryReversed(
            tenant_id=entry.tenant_id,
            organization_id=entry.organization_id,
            project_id=entry.project_id,
            cost_entry_id=reversal.id,
            reverses_entry_id=entry.id,
            occurred_at=now,
        )
        if self._record_event is not None:
            self._record_event(event)
        self._session.flush()
        return reversal

    def _require_entry(
        self, entry_id: str, *, for_update: bool = False
    ) -> ProjectCostEntry:
        entry = self._entry_repo.get(entry_id, for_update=for_update)
        if entry is None:
            raise NotFoundError(
                "Project cost entry not found.", code="PROJECT_COST_ENTRY_NOT_FOUND"
            )
        return entry

    @staticmethod
    def _require_manual_interactive_entry(
        entry: ProjectCostEntry, *, operation: str
    ) -> None:
        if not is_manual_actual_entry(entry):
            raise BusinessRuleError(
                f"Source-owned actuals cannot use the {operation} command in Project Finance.",
                code="PROJECT_COST_ENTRY_SOURCE_OWNED",
            )

    def _require_command_permission(
        self, project_id: str, permission: str, operation: str
    ) -> None:
        require_permission(self._user_session, permission, operation_label=operation)
        require_project_permission(
            self._user_session,
            project_id,
            permission,
            operation_label=operation,
        )

    @staticmethod
    def _require_expected_version(
        entry: ProjectCostEntry, expected_version: int
    ) -> None:
        if entry.row_version != expected_version:
            raise ConcurrencyError(
                "Project cost entry changed since you opened it.",
                code="STALE_WRITE",
            )

    def _require_active_profile(self, project_id: str):
        profile = self._financial_profile_repo.get_by_project(project_id)
        if profile is None:
            raise NotFoundError(
                "Project financial profile is required before recording actual costs.",
                code="PROJECT_FINANCIAL_PROFILE_NOT_FOUND",
            )
        if profile.status != FinancialProfileStatus.ACTIVE:
            raise BusinessRuleError(
                "Project financial profile must be active for actual-cost commands.",
                code="PROJECT_FINANCIAL_PROFILE_NOT_ACTIVE",
            )
        return profile

    def _require_full_context(self, operation_label: str):
        if self._tenant_context_service is None:
            raise BusinessRuleError(
                f"Active organization context is required to {operation_label}.",
                code="TENANT_CONTEXT_REQUIRED",
            )
        context = self._tenant_context_service.require_organization_context(
            operation_label=operation_label
        )
        if context.organization is None:
            raise BusinessRuleError(
                "Active organization is required for project cost posting.",
                code="ORGANIZATION_CONTEXT_REQUIRED",
            )
        return context

    def _resolve_fx_snapshot(
        self,
        *,
        entry: ProjectCostEntry,
        base_currency: str,
        posting_date: date,
        exchange_rate: Decimal | None,
        exchange_rate_date: date | None,
        exchange_rate_source: str | None,
        exchange_rate_captured_at: datetime | None,
    ) -> tuple[Decimal, date, str, datetime]:
        if entry.currency_code == base_currency:
            if exchange_rate not in (None, Decimal(1), 1, "1"):
                raise ValidationError(
                    "Identity-currency postings must use an exchange rate of 1.",
                    code="PROJECT_COST_ENTRY_IDENTITY_RATE_INVALID",
                )
            return Decimal(1), posting_date, "identity", self._clock.now()
        if (
            exchange_rate is None
            or exchange_rate_date is None
            or not str(exchange_rate_source or "").strip()
            or exchange_rate_captured_at is None
        ):
            raise ValidationError(
                "Cross-currency postings require a complete exchange-rate snapshot.",
                code="PROJECT_COST_ENTRY_FX_SNAPSHOT_REQUIRED",
            )
        rate = EXCHANGE_RATE_STORAGE.validate(exchange_rate)
        if rate <= 0:
            raise ValidationError(
                "Exchange rate must be positive.",
                code="PROJECT_COST_ENTRY_EXCHANGE_RATE_INVALID",
            )
        if (
            exchange_rate_captured_at.tzinfo is None
            or exchange_rate_captured_at.utcoffset() is None
        ):
            raise ValidationError(
                "Exchange-rate capture timestamp must include a timezone.",
                code="PROJECT_COST_ENTRY_FX_CAPTURE_TIME_INVALID",
            )
        return (
            rate,
            exchange_rate_date,
            str(exchange_rate_source).strip(),
            exchange_rate_captured_at,
        )

    def _actor_id(self) -> str:
        principal = getattr(self._user_session, "principal", None)
        actor_id = getattr(principal, "user_id", None)
        if not actor_id:
            raise BusinessRuleError(
                "An authenticated actor is required for project cost commands.",
                code="PROJECT_COST_ENTRY_ACTOR_REQUIRED",
            )
        return str(actor_id)

    def _record_audit(self, operation: str, entry: ProjectCostEntry) -> None:
        record_project_cost_entry_audit(self, operation=operation, entry=entry)

    @staticmethod
    def _resolve_replay(
        existing: ProjectCostEntry, source: FinancialSourceReference
    ) -> ProjectCostEntry:
        if (
            existing.project_id == source.project_id
            and existing.source_content_hash == source.content_hash
        ):
            return existing
        raise BusinessRuleError(
            "The financial source identity was already used with different content or scope.",
            code="PROJECT_COST_ENTRY_SOURCE_REPLAY_CONFLICT",
        )


__all__ = ["ProjectCostEntryPostingCommandHandler"]

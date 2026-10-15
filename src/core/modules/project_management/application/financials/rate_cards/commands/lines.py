from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, date, datetime
from enum import Enum
from typing import Any, Final

from sqlalchemy.orm import Session

from src.core.modules.project_management.access.scope_permissions import (
    require_project_permission,
)
from src.core.modules.project_management.application.common.module_guard import (
    ProjectManagementModuleGuardMixin,
)
from src.core.modules.project_management.application.financials.rate_cards._command_values import (
    command_amount as _command_amount,
)
from src.core.modules.project_management.application.financials.rate_cards._command_values import (
    optional_command_amount as _optional_command_amount,
)
from src.core.modules.project_management.application.financials.rate_cards.dto.commands.rate_lines import (
    FinancialAddRateLineCommand,
    FinancialUpdateRateLineCommand,
    FinancialVersionedRateLineCommand,
)
from src.core.modules.project_management.application.financials.rate_cards.rate_card_events import (
    RateCardLineAdded,
    RateCardLineDeactivated,
    RateCardLineUpdated,
)
from src.core.modules.project_management.contracts.repositories.finance.rate_cards.rate_cards import (
    ProjectRateCardRepository,
)
from src.core.modules.project_management.contracts.repositories.projects.project import (
    ProjectRepository,
)
from src.core.modules.project_management.domain.financials.rate_cards import (
    ProjectRateCard,
    RateCardLine,
    RateLineOrigin,
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
)
from src.core.shared.activity import record_activity
from src.core.shared.audit import record_audit_entry


class _Unset(Enum):
    """Typed sentinel distinguishing "argument omitted" from an explicit None."""

    TOKEN = 0


_UNSET: Final = _Unset.TOKEN


class RateCardLineCommandHandler(ProjectManagementModuleGuardMixin):
    """Governed lines mutations in the caller's transaction."""

    def __init__(
        self,
        *,
        session: Session,
        rate_card_repo: ProjectRateCardRepository,
        project_repo: ProjectRepository,
        user_session=None,
        enterprise_audit_service=None,
        module_catalog_service=None,
        tenant_context_service: TenantContextService | None = None,
        record_event: Callable[[object], None] | None = None,
    ) -> None:
        self._session = session
        self._rate_card_repo = rate_card_repo
        self._project_repo = project_repo
        self._user_session = user_session
        self._enterprise_audit_service = enterprise_audit_service
        self._module_catalog_service = module_catalog_service
        self._tenant_context_service = tenant_context_service
        self._record_event = record_event

    def _emit(self, event: object) -> None:
        if self._record_event is not None:
            self._record_event(event)

    # -- Rate cards ---------------------------------------------------

    def create_line(self, command: FinancialAddRateLineCommand) -> RateCardLine:
        rate_card_id = command.rate_card_id
        rate_type = command.rate_type
        unit = command.unit
        rate_amount = _command_amount(command.rate_amount, "Rate amount")
        rate_currency = command.rate_currency
        origin = RateLineOrigin.CONFIGURED
        resource_id = command.resource_id
        customer_party_id = command.customer_party_id
        contract_reference = command.contract_reference
        role = command.role
        skill_code = command.skill_code
        department_id = command.department_id
        effective_from = command.effective_from
        effective_to = command.effective_to
        overtime_multiplier = _optional_command_amount(command.overtime_multiplier)
        weekend_multiplier = _optional_command_amount(command.weekend_multiplier)
        holiday_multiplier = _optional_command_amount(command.holiday_multiplier)
        expected_card_version = command.expected_card_version
        card = self._require_rate_card(rate_card_id)
        self._require_card_manage(card, "create rate card line")
        self._require_active_card(card)
        if expected_card_version is not None:
            self._require_expected_version(card.version, expected_card_version, "Rate card")
        context = self._require_context("create rate card line")
        line = RateCardLine.create(
            tenant_id=context.tenant_id,
            organization_id=context.organization_id,
            rate_card_id=card.id,
            rate_type=rate_type,
            unit=unit,
            rate_amount=rate_amount,
            rate_currency=rate_currency,
            origin=origin,
            resource_id=resource_id,
            customer_party_id=customer_party_id,
            contract_reference=contract_reference,
            role=role,
            skill_code=skill_code,
            department_id=department_id,
            effective_from=effective_from,
            effective_to=effective_to,
            overtime_multiplier=overtime_multiplier,
            weekend_multiplier=weekend_multiplier,
            holiday_multiplier=holiday_multiplier,
        )
        self._reject_overlap(card.id, line)
        self._rate_card_repo.add_line(line)
        self._record_line_audit("create", line)
        self._session.flush()
        self._emit(
            RateCardLineAdded(
                tenant_id=line.tenant_id,
                organization_id=line.organization_id,
                rate_card_id=line.rate_card_id,
                rate_line_id=line.id,
                project_id=card.project_id,
                occurred_at=datetime.now(UTC),
            )
        )
        return line

    def update_line(self, command: FinancialUpdateRateLineCommand) -> RateCardLine:
        line_id = command.rate_line_id
        expected_version = command.expected_version
        effective_from = command.effective_from
        effective_to = command.effective_to
        rate_amount = _command_amount(command.rate_amount, "Rate amount")
        overtime_multiplier = _optional_command_amount(command.overtime_multiplier)
        weekend_multiplier = _optional_command_amount(command.weekend_multiplier)
        holiday_multiplier = _optional_command_amount(command.holiday_multiplier)
        expected_card_version = command.expected_card_version
        current = self._require_line(line_id, for_update=True)
        card = self._require_rate_card(current.rate_card_id)
        self._require_card_manage(card, "update rate card line")
        self._require_active_card(card)
        if expected_card_version is not None:
            self._require_expected_version(card.version, expected_card_version, "Rate card")
        self._require_expected_version(current.version, expected_version, "Rate card line")
        candidate = replace(
            current,
            effective_from=(
                current.effective_from if effective_from is _UNSET else effective_from
            ),
            effective_to=current.effective_to if effective_to is _UNSET else effective_to,
            rate_amount=current.rate_amount if rate_amount is _UNSET else rate_amount,
            overtime_multiplier=(
                current.overtime_multiplier
                if overtime_multiplier is _UNSET
                else overtime_multiplier
            ),
            weekend_multiplier=(
                current.weekend_multiplier
                if weekend_multiplier is _UNSET
                else weekend_multiplier
            ),
            holiday_multiplier=(
                current.holiday_multiplier
                if holiday_multiplier is _UNSET
                else holiday_multiplier
            ),
        )
        if candidate == current:
            # True no-op: no write, audit, event, or version bump.
            return current
        now = datetime.now(UTC)
        candidate = replace(candidate, updated_at=now)
        self._protect_consumed_economics(current, candidate)
        self._reject_overlap(candidate.rate_card_id, candidate, excluding_line_id=candidate.id)
        self._rate_card_repo.update_line(candidate)
        self._record_line_audit("update", candidate, old=current)
        self._session.flush()
        self._emit(
            RateCardLineUpdated(
                tenant_id=candidate.tenant_id,
                organization_id=candidate.organization_id,
                rate_card_id=candidate.rate_card_id,
                rate_line_id=candidate.id,
                project_id=card.project_id,
                occurred_at=now,
            )
        )
        return candidate

    def deactivate_line(self, command: FinancialVersionedRateLineCommand) -> RateCardLine:
        line_id = command.rate_line_id
        expected_version = command.expected_version
        expected_card_version = command.expected_card_version
        current = self._require_line(line_id, for_update=True)
        card = self._require_rate_card(current.rate_card_id)
        self._require_card_manage(card, "deactivate rate card line")
        self._require_active_card(card)
        if expected_card_version is not None:
            self._require_expected_version(card.version, expected_card_version, "Rate card")
        self._require_expected_version(current.version, expected_version, "Rate card line")
        if not current.is_active:
            return current
        now = datetime.now(UTC)
        candidate = replace(current, is_active=False, updated_at=now)
        self._rate_card_repo.update_line(candidate)
        self._record_line_audit("deactivate", candidate, old=current)
        self._session.flush()
        self._emit(
            RateCardLineDeactivated(
                tenant_id=candidate.tenant_id,
                organization_id=candidate.organization_id,
                rate_card_id=candidate.rate_card_id,
                rate_line_id=candidate.id,
                project_id=card.project_id,
                occurred_at=now,
            )
        )
        return candidate

    # -- Overlap prevention ----

    def _reject_overlap(
        self,
        rate_card_id: str,
        candidate: RateCardLine,
        *,
        excluding_line_id: str | None = None,
    ) -> None:
        # Scoped to every card sharing the candidate's project_id: an org-wide line and a
        # project-specific line for the same role are legitimate coexisting precedence
        # tiers, not a duplicate, but two project-scoped cards for the same project are.
        card = self._require_rate_card(rate_card_id)
        self._rate_card_repo.lock_line_overlap_scope(
            "|".join(
                str(value or "-")
                for value in (
                    card.tenant_id,
                    card.organization_id,
                    card.project_id,
                    candidate.rate_type.value,
                    candidate.resource_id,
                    candidate.customer_party_id,
                    candidate.contract_reference,
                    candidate.role,
                    candidate.skill_code,
                    candidate.department_id,
                )
            )
        )
        existing = self._rate_card_repo.list_lines_in_scope(project_id=card.project_id)
        for other in existing:
            if other.id == excluding_line_id:
                continue
            if other.rate_type != candidate.rate_type:
                continue
            if not self._same_selection_key(other, candidate):
                continue
            if self._windows_overlap(other, candidate):
                raise BusinessRuleError(
                    "A rate line with the same selection key and an overlapping "
                    "effective window already exists.",
                    code="RATE_CARD_LINE_OVERLAP",
                )

    @staticmethod
    def _same_selection_key(left: RateCardLine, right: RateCardLine) -> bool:
        return (
            left.resource_id == right.resource_id
            and left.customer_party_id == right.customer_party_id
            and left.contract_reference == right.contract_reference
            and left.role == right.role
            and left.skill_code == right.skill_code
            and left.department_id == right.department_id
        )

    @staticmethod
    def _windows_overlap(left: RateCardLine, right: RateCardLine) -> bool:
        left_end = left.effective_to or date.max
        right_end = right.effective_to or date.max
        left_start = left.effective_from or date.min
        right_start = right.effective_from or date.min
        return left_start <= right_end and right_start <= left_end

    # -- Shared helpers ---------------------------------------------------

    def _require_project(self, project_id: str, permission: str, operation: str):
        require_permission(self._user_session, permission, operation_label=operation)
        project = self._project_repo.get(project_id)
        if project is None:
            raise NotFoundError("Project not found.")
        require_project_permission(
            self._user_session,
            project_id,
            permission,
            operation_label=operation,
        )
        return project

    def _require_rate_card(self, rate_card_id: str) -> ProjectRateCard:
        rate_card = self._rate_card_repo.get(rate_card_id)
        if rate_card is None:
            raise NotFoundError("Rate card not found.")
        return rate_card

    def _require_line(self, line_id: str, *, for_update: bool = False) -> RateCardLine:
        line = self._rate_card_repo.get_line(line_id, for_update=for_update)
        if line is None:
            raise NotFoundError("Rate card line not found.")
        return line

    def _require_card_manage(self, card: ProjectRateCard, operation: str) -> None:
        require_permission(self._user_session, "finance.manage", operation_label=operation)
        if card.project_id:
            self._require_project(card.project_id, "finance.manage", operation)

    @staticmethod
    def _require_active_card(card: ProjectRateCard) -> None:
        if not card.is_active:
            raise BusinessRuleError(
                "Inactive Rate Cards cannot be changed.",
                code="RATE_CARD_INACTIVE",
            )

    def _protect_consumed_economics(
        self, current: RateCardLine, candidate: RateCardLine
    ) -> None:
        if not self._rate_card_repo.is_line_consumed(current.id):
            return
        immutable_fields = (
            "rate_amount",
            "rate_currency",
            "rate_type",
            "unit",
            "resource_id",
            "customer_party_id",
            "contract_reference",
            "role",
            "skill_code",
            "department_id",
            "effective_from",
            "overtime_multiplier",
            "weekend_multiplier",
            "holiday_multiplier",
        )
        if any(getattr(current, name) != getattr(candidate, name) for name in immutable_fields):
            raise BusinessRuleError(
                "This Rate Line has historical financial use. Its economic terms are "
                "immutable; end-date it for the future and add a new Rate Line.",
                code="RATE_CARD_LINE_HISTORICAL_IMMUTABLE",
            )
        if (
            candidate.effective_to != current.effective_to
            and (candidate.effective_to is None or candidate.effective_to < date.today())  # noqa: DTZ011 -- naive local business date by design
        ):
                raise BusinessRuleError(
                    "A consumed Rate Line may only be end-dated today or in the future.",
                    code="RATE_CARD_LINE_HISTORICAL_END_DATE_INVALID",
                )

    def _require_context(self, operation: str):
        if self._tenant_context_service is None:
            raise BusinessRuleError(
                f"Active organization context is required to {operation}.",
                code="TENANT_CONTEXT_REQUIRED",
            )
        return self._tenant_context_service.require_organization_context(
            operation_label=operation
        )

    @staticmethod
    def _require_expected_version(actual: int, expected: int, label: str) -> None:
        if actual != expected:
            raise ConcurrencyError(
                f"{label} changed since you opened it. Refresh and try again.",
                code="STALE_WRITE",
            )

    def _record_line_audit(
        self,
        operation: str,
        line: RateCardLine,
        *,
        old: RateCardLine | None = None,
    ) -> None:
        self._record_audit(
            operation=f"rate_card_line.{operation}",
            entity_type="rate_card_line",
            entity_id=line.id,
            project_id=None,
            before_data=self._line_audit_value(old),
            after_data=self._line_audit_value(line),
        )

    def _record_audit(
        self,
        *,
        operation: str,
        entity_type: str,
        entity_id: str,
        project_id: str | None,
        before_data: dict[str, Any] | None,
        after_data: dict[str, Any] | None,
    ) -> None:
        record_audit_entry(
            self,
            operation=operation,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_parent_id=project_id,
            module="project_management",
            category="FINANCIAL",
            before_data=before_data,
            after_data=after_data,
            workspace_id=project_id,
            source="application",
            severity="high",
            metadata={"action": operation},
            commit=False,
            fail_closed=True,
        )
        record_activity(
            self,
            action=operation,
            entity_type=entity_type,
            entity_id=entity_id,
            parent_entity_id=project_id,
            module="project_management",
            workspace_id=project_id,
            details={"action": operation},
            commit=False,
        )

    @staticmethod
    def _line_audit_value(line: RateCardLine | None) -> dict[str, Any] | None:
        if line is None:
            return None
        return {
            "rate_type": line.rate_type.value,
            "origin": line.origin.value,
            "resource_id": line.resource_id,
            "customer_party_id": line.customer_party_id,
            "contract_reference": line.contract_reference,
            "role": line.role,
            "skill_code": line.skill_code,
            "department_id": line.department_id,
            "effective_from": (
                line.effective_from.isoformat() if line.effective_from else None
            ),
            "effective_to": line.effective_to.isoformat() if line.effective_to else None,
            "is_active": line.is_active,
            "unit": line.unit,
            "rate_amount": str(line.rate_amount),
            "rate_currency": line.rate_currency,
            "version": line.version,
        }


__all__ = ["RateCardLineCommandHandler"]

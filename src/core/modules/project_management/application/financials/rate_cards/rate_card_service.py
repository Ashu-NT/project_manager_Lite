from __future__ import annotations

import json
from dataclasses import replace
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.core.modules.project_management.application.common.module_guard import (
    ProjectManagementModuleGuardMixin,
)
from src.core.modules.project_management.contracts.repositories.finance.rate_cards.rate_cards import (
    ProjectRateCardRepository,
)
from src.core.modules.project_management.contracts.repositories.projects.project import ProjectRepository
from src.core.modules.project_management.domain.financials.rate_cards import (
    ProjectRateCard,
    RateCardLine,
    RateLineOrigin,
    RateType,
)
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)
from src.core.modules.project_management.access.scope_permissions import require_project_permission
from src.core.platform.application.tenant.tenancy.tenant_context import TenantContextService
from src.core.platform.common.exceptions import (
    BusinessRuleError,
    ConcurrencyError,
    NotFoundError,
    ValidationError,
)
from src.core.shared.audit import record_audit_entry


_UNSET = object()


class ProjectRateCardService(ProjectManagementModuleGuardMixin):
    """Governed creation, update, and overlap validation of rate cards and lines.
    """

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
    ) -> None:
        self._session = session
        self._rate_card_repo = rate_card_repo
        self._project_repo = project_repo
        self._user_session = user_session
        self._enterprise_audit_service = enterprise_audit_service
        self._module_catalog_service = module_catalog_service
        self._tenant_context_service = tenant_context_service

    # -- Rate cards ---------------------------------------------------

    def create_rate_card(
        self,
        *,
        name: str,
        project_id: str | None = None,
    ) -> ProjectRateCard:
        if project_id:
            self._require_project(project_id, "finance.manage", "create project rate card")
        else:
            require_permission(
                self._user_session,
                "finance.manage",
                operation_label="create organization rate card",
            )
        context = self._require_context("create rate card")
        rate_card = ProjectRateCard.create(
            tenant_id=context.tenant_id,
            organization_id=context.organization_id,
            name=name,
            project_id=project_id,
        )
        self._rate_card_repo.add(rate_card)
        self._record_card_audit("create", rate_card)
        self._commit()
        return rate_card

    def list_rate_cards(
        self,
        *,
        project_id: str | None = None,
        include_inactive: bool = False,
    ) -> list[ProjectRateCard]:
        require_permission(
            self._user_session,
            "finance.read",
            operation_label="list rate cards",
        )
        return self._rate_card_repo.list(project_id=project_id, include_inactive=include_inactive)

    def deactivate_rate_card(self, rate_card_id: str, *, expected_version: int) -> ProjectRateCard:
        require_permission(
            self._user_session,
            "finance.manage",
            operation_label="deactivate rate card",
        )
        current = self._require_rate_card(rate_card_id)
        self._require_expected_version(current.version, expected_version, "Rate card")
        if not current.is_active:
            return current
        candidate = replace(current, is_active=False, updated_at=datetime.now(timezone.utc))
        self._rate_card_repo.update(candidate)
        self._record_card_audit("deactivate", candidate, old=current)
        self._commit()
        return candidate

    # -- Rate card lines ------------------------------------------------

    def create_line(
        self,
        rate_card_id: str,
        *,
        rate_type: RateType | str,
        unit: str,
        rate_amount: Decimal,
        rate_currency: str,
        origin: RateLineOrigin | str = RateLineOrigin.CONFIGURED,
        resource_id: str | None = None,
        customer_party_id: str | None = None,
        contract_reference: str | None = None,
        role: str | None = None,
        skill_code: str | None = None,
        department_id: str | None = None,
        effective_from: date | None = None,
        effective_to: date | None = None,
        overtime_multiplier: Decimal | None = None,
        weekend_multiplier: Decimal | None = None,
        holiday_multiplier: Decimal | None = None,
    ) -> RateCardLine:
        require_permission(
            self._user_session,
            "finance.manage",
            operation_label="create rate card line",
        )
        card = self._require_rate_card(rate_card_id)
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
        self._commit()
        return line

    def update_line(
        self,
        line_id: str,
        *,
        expected_version: int,
        effective_from: date | None | object = _UNSET,
        effective_to: date | None | object = _UNSET,
        rate_amount: Decimal | object = _UNSET,
        overtime_multiplier: Decimal | None | object = _UNSET,
        weekend_multiplier: Decimal | None | object = _UNSET,
        holiday_multiplier: Decimal | None | object = _UNSET,
    ) -> RateCardLine:
        require_permission(
            self._user_session,
            "finance.manage",
            operation_label="update rate card line",
        )
        current = self._require_line(line_id)
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
            updated_at=datetime.now(timezone.utc),
        )
        self._reject_overlap(candidate.rate_card_id, candidate, excluding_line_id=candidate.id)
        self._rate_card_repo.update_line(candidate)
        self._record_line_audit("update", candidate, old=current)
        self._commit()
        return candidate

    def deactivate_line(self, line_id: str, *, expected_version: int) -> RateCardLine:
        require_permission(
            self._user_session,
            "finance.manage",
            operation_label="deactivate rate card line",
        )
        current = self._require_line(line_id)
        self._require_expected_version(current.version, expected_version, "Rate card line")
        if not current.is_active:
            return current
        candidate = replace(current, is_active=False, updated_at=datetime.now(timezone.utc))
        self._rate_card_repo.update_line(candidate)
        self._record_line_audit("deactivate", candidate, old=current)
        self._commit()
        return candidate

    def list_lines(
        self,
        rate_card_id: str,
        *,
        include_inactive: bool = False,
    ) -> list[RateCardLine]:
        require_permission(
            self._user_session,
            "finance.read",
            operation_label="list rate card lines",
        )
        return self._rate_card_repo.list_lines(rate_card_id, include_inactive=include_inactive)

    # -- Overlap prevention (application layer — see plan rationale) ----

    def _reject_overlap(
        self,
        rate_card_id: str,
        candidate: RateCardLine,
        *,
        excluding_line_id: str | None = None,
    ) -> None:
        # Scoped to every card sharing the candidate's own project_id (not
        # just this one card, and not the broader cross-tier resolution
        # view either — an org-wide line and a project-specific line for
        # the same role are legitimate coexisting precedence tiers, not a
        # duplicate). Two project-scoped cards for the SAME project are
        # the same tier and must not silently both define the same line.
        card = self._require_rate_card(rate_card_id)
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

    def _require_line(self, line_id: str) -> RateCardLine:
        line = self._rate_card_repo.get_line(line_id)
        if line is None:
            raise NotFoundError("Rate card line not found.")
        return line

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

    def _record_card_audit(
        self,
        operation: str,
        rate_card: ProjectRateCard,
        *,
        old: ProjectRateCard | None = None,
    ) -> None:
        self._record_audit(
            operation=f"project_rate_card.{operation}",
            entity_type="project_rate_card",
            entity_id=rate_card.id,
            project_id=rate_card.project_id,
            old_value=self._card_audit_value(old),
            new_value=self._card_audit_value(rate_card),
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
            old_value=self._line_audit_value(old),
            new_value=self._line_audit_value(line),
        )

    def _record_audit(
        self,
        *,
        operation: str,
        entity_type: str,
        entity_id: str,
        project_id: str | None,
        old_value: str | None,
        new_value: str | None,
    ) -> None:
        record_audit_entry(
            self,
            operation=operation,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_parent_id=project_id,
            module="project_management",
            old_value=old_value,
            new_value=new_value,
            workspace_id=project_id,
            source="application",
            severity="high",
            compliance_tag="financial",
            metadata={"action": operation},
            commit=False,
            fail_closed=True,
        )

    @staticmethod
    def _card_audit_value(rate_card: ProjectRateCard | None) -> str | None:
        if rate_card is None:
            return None
        return json.dumps(
            {
                "name": rate_card.name,
                "project_id": rate_card.project_id,
                "is_active": rate_card.is_active,
                "version": rate_card.version,
            },
            sort_keys=True,
        )

    @staticmethod
    def _line_audit_value(line: RateCardLine | None) -> str | None:
        if line is None:
            return None
        return json.dumps(
            {
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
            },
            sort_keys=True,
        )

    def _commit(self, *, duplicate_message: str | None = None) -> None:
        try:
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            if duplicate_message:
                raise ValidationError(
                    duplicate_message,
                    code="RATE_CARD_DUPLICATE",
                ) from exc
            raise
        except Exception:
            self._session.rollback()
            raise


__all__ = ["ProjectRateCardService"]

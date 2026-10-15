from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from src.core.modules.project_management.access.scope_permissions import (
    require_project_permission,
)
from src.core.modules.project_management.application.common.module_guard import (
    ProjectManagementModuleGuardMixin,
)
from src.core.modules.project_management.application.financials.rate_cards.dto.commands.rate_cards import (
    FinancialCreateRateCardCommand,
    FinancialUpdateRateCardCommand,
    FinancialVersionedRateCardCommand,
)
from src.core.modules.project_management.application.financials.rate_cards.rate_card_events import (
    RateCardCreated,
    RateCardDeactivated,
    RateCardUpdated,
)
from src.core.modules.project_management.contracts.repositories.finance.rate_cards.rate_cards import (
    ProjectRateCardRepository,
)
from src.core.modules.project_management.contracts.repositories.projects.project import (
    ProjectRepository,
)
from src.core.modules.project_management.domain.financials.rate_cards import (
    ProjectRateCard,
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


class ProjectRateCardCommandHandler(ProjectManagementModuleGuardMixin):
    """Governed cards mutations in the caller's transaction."""

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

    def create_rate_card(self, command: FinancialCreateRateCardCommand) -> ProjectRateCard:
        name = command.name
        project_id = command.project_id
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
        self._session.flush()
        self._emit(
            RateCardCreated(
                tenant_id=rate_card.tenant_id,
                organization_id=rate_card.organization_id,
                rate_card_id=rate_card.id,
                project_id=rate_card.project_id,
                occurred_at=datetime.now(UTC),
            )
        )
        return rate_card

    def deactivate_rate_card(self, command: FinancialVersionedRateCardCommand) -> ProjectRateCard:
        rate_card_id = command.rate_card_id
        expected_version = command.expected_version
        current = self._require_rate_card(rate_card_id)
        self._require_card_manage(current, "deactivate rate card")
        self._require_expected_version(current.version, expected_version, "Rate card")
        if not current.is_active:
            return current
        now = datetime.now(UTC)
        candidate = replace(current, is_active=False, updated_at=now)
        self._rate_card_repo.update(candidate)
        self._record_card_audit("deactivate", candidate, old=current)
        self._session.flush()
        self._emit(
            RateCardDeactivated(
                tenant_id=candidate.tenant_id,
                organization_id=candidate.organization_id,
                rate_card_id=candidate.id,
                project_id=candidate.project_id,
                occurred_at=now,
            )
        )
        return candidate

    def update_rate_card(self, command: FinancialUpdateRateCardCommand) -> ProjectRateCard:
        rate_card_id = command.rate_card_id
        expected_version = command.expected_version
        name = command.name
        current = self._require_rate_card(rate_card_id)
        self._require_card_manage(current, "update rate card")
        self._require_expected_version(current.version, expected_version, "Rate card")
        candidate = replace(current)
        candidate.rename(name)
        if candidate.name == current.name:
            return current
        self._rate_card_repo.update(candidate)
        self._record_card_audit("update", candidate, old=current)
        self._session.flush()
        self._emit(
            RateCardUpdated(
                tenant_id=candidate.tenant_id,
                organization_id=candidate.organization_id,
                rate_card_id=candidate.id,
                project_id=candidate.project_id,
                occurred_at=candidate.updated_at,
            )
        )
        return candidate

    # -- Rate card lines ------------------------------------------------

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

    def _require_card_manage(self, card: ProjectRateCard, operation: str) -> None:
        require_permission(self._user_session, "finance.manage", operation_label=operation)
        if card.project_id:
            self._require_project(card.project_id, "finance.manage", operation)

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
            before_data=self._card_audit_value(old),
            after_data=self._card_audit_value(rate_card),
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
    def _card_audit_value(rate_card: ProjectRateCard | None) -> dict[str, Any] | None:
        if rate_card is None:
            return None
        return {
            "name": rate_card.name,
            "project_id": rate_card.project_id,
            "is_active": rate_card.is_active,
            "version": rate_card.version,
        }


__all__ = ["ProjectRateCardCommandHandler"]

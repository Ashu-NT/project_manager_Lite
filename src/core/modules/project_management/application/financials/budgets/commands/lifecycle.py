from __future__ import annotations

from collections.abc import Callable
from enum import Enum
from typing import Any, Final

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.core.modules.project_management.access.scope_permissions import (
    require_project_permission,
)
from src.core.modules.project_management.application.common.module_guard import (
    ProjectManagementModuleGuardMixin,
)
from src.core.modules.project_management.application.financials.budgets.budget_events import (
    BudgetProfileUpdated,
    BudgetRemoved,
    BudgetStatusChanged,
    BudgetStatusChangeType,
    BudgetVersionCreated,
)
from src.core.modules.project_management.application.financials.budgets.dto.commands.budget_lifecycle import (
    FinancialCreateBudgetSuccessorCommand,
    FinancialCreateBudgetVersionCommand,
    FinancialUpdateBudgetCommand,
    FinancialVersionedBudgetCommand,
)
from src.core.modules.project_management.application.financials.budgets.dto.responses.mutations import (
    FinancialBudgetMutationDto,
)
from src.core.modules.project_management.application.financials.budgets.mappers.responses import (
    map_budget,
)
from src.core.modules.project_management.contracts.repositories.finance.budgets.budget import (
    ProjectBudgetRepository,
)
from src.core.modules.project_management.contracts.repositories.finance.configuration.financial_configuration import (
    ProjectFinancialProfileRepository,
)
from src.core.modules.project_management.contracts.repositories.projects.project import (
    ProjectRepository,
)
from src.core.modules.project_management.domain.financials.budget import (
    BudgetLine,
    BudgetStatus,
    ProjectBudget,
)
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)
from src.core.platform.application.tenant.tenancy.tenant_context import (
    TenantContext,
    TenantContextService,
)
from src.core.platform.common.exceptions import (
    BusinessRuleError,
    ConcurrencyError,
    NotFoundError,
    ValidationError,
)
from src.core.shared.activity import record_activity
from src.core.shared.audit import record_audit_entry
from src.core.shared.time.clock import CalendarClock


class _Unset(Enum):
    """Typed sentinel distinguishing "argument omitted" from an explicit None."""

    TOKEN = 0


_UNSET: Final = _Unset.TOKEN

_OPEN_VERSION_CONSTRAINT = "uq_pf_budgets_one_open_per_project"
_APPROVED_CONSTRAINT = "uq_pf_budgets_one_approved_per_project"
_REVISION_CONSTRAINT = "uq_pf_budget_project_revision"


class BudgetLifecycleCommands(ProjectManagementModuleGuardMixin):
    """Version lifecycle and header commands."""

    def _command_actor_id(self) -> str:
        actor_id = self.current_actor_user_id
        if not actor_id:
            raise ValidationError(
                "An authenticated actor is required for Budget commands.",
                code="BUDGET_ACTOR_REQUIRED",
            )
        return str(actor_id)

    def __init__(
        self,
        *,
        session: Session,
        budget_repo: ProjectBudgetRepository,
        project_repo: ProjectRepository,
        financial_profile_repo: ProjectFinancialProfileRepository,
        clock: CalendarClock,
        user_session=None,
        enterprise_audit_service=None,
        module_catalog_service=None,
        tenant_context_service: TenantContextService | None = None,
        record_event: Callable[[object], None] | None = None,
    ) -> None:
        self._session = session
        self._budget_repo = budget_repo
        self._project_repo = project_repo
        self._financial_profile_repo = financial_profile_repo
        self._clock = clock
        self._user_session = user_session
        self._enterprise_audit_service = enterprise_audit_service
        self._module_catalog_service = module_catalog_service
        self._tenant_context_service = tenant_context_service
        self._record_event = record_event


    def create_budget(self, command: FinancialCreateBudgetVersionCommand) -> FinancialBudgetMutationDto:
        currency_code = command.currency_code or None
        require_permission(self._user_session, "budget.manage", operation_label="create project budget")
        require_project_permission(
            self._user_session, command.project_id, "budget.manage", operation_label="create project budget"
        )
        project = self._project_repo.get(command.project_id)
        if project is None:
            raise NotFoundError("Project not found.", code="PROJECT_NOT_FOUND")
        profile = self._financial_profile_repo.get_by_project(command.project_id)
        if profile is None:
            raise NotFoundError(
                "Project financial profile not found; configure the project's "
                "finance settings before creating a budget.",
                code="PROJECT_FINANCIAL_PROFILE_NOT_FOUND",
            )
        context = self._require_context("create project budget")
        organization_id = context.organization_id
        if organization_id is None:  # require_organization_context guarantees this
            raise BusinessRuleError(
                "Active organization context is required to create project budget.",
                code="TENANT_CONTEXT_REQUIRED",
            )
        if self._budget_repo.has_open_for_project(command.project_id):
            raise BusinessRuleError(
                "A draft or submitted budget already exists for this project.",
                code="PROJECT_BUDGET_OPEN_VERSION_EXISTS",
            )
        latest = self._budget_repo.get_latest_for_project(command.project_id)
        revision = (latest.revision + 1) if latest is not None else 1
        now = self._clock.now()
        budget = ProjectBudget.create(
            tenant_id=context.tenant_id,
            organization_id=organization_id,
            project_id=command.project_id,
            name=command.name,
            currency_code=currency_code or profile.currency_code,
            revision=revision,
            created_at=now,
        )
        try:
            with self._session.begin_nested():
                self._budget_repo.add(budget)
                self._budget_repo.flush()
        except IntegrityError as exc:
            self._translate_create_conflict(exc)
        self._record_budget_audit(operation="create", budget=budget)
        event = BudgetVersionCreated(
            tenant_id=budget.tenant_id,
            organization_id=budget.organization_id,
            project_id=budget.project_id,
            budget_id=budget.id,
            status=budget.status,
            predecessor_budget_id=None,
            occurred_at=now,
        )
        if self._record_event is not None:
            self._record_event(event)
        self._session.flush()
        return map_budget(budget)


    def create_successor(self, command: FinancialCreateBudgetSuccessorCommand) -> FinancialBudgetMutationDto:
        """Create a mutable draft copied from an approved budget revision.

        The predecessor remains immutable. Revision assignment, currency, and
        line cloning are server-owned so the desktop cannot manufacture
        financial lineage or silently omit approved dimensions.
        """
        require_permission(
            self._user_session,
            "budget.manage",
            operation_label="create project budget successor",
        )
        predecessor = self._require_budget(command.predecessor_budget_id)
        require_project_permission(
            self._user_session,
            predecessor.project_id,
            "budget.manage",
            operation_label="create project budget successor",
        )
        if predecessor.status != BudgetStatus.APPROVED:
            raise BusinessRuleError(
                "Only an approved budget can be used as a successor source.",
                code="PROJECT_BUDGET_SUCCESSOR_SOURCE_INVALID",
            )
        if self._budget_repo.has_open_for_project(predecessor.project_id):
            raise BusinessRuleError(
                "A draft or submitted budget already exists for this project.",
                code="PROJECT_BUDGET_OPEN_VERSION_EXISTS",
            )

        latest = self._budget_repo.get_latest_for_project(predecessor.project_id)
        now = self._clock.now()
        successor = ProjectBudget.create(
            tenant_id=predecessor.tenant_id,
            organization_id=predecessor.organization_id,
            project_id=predecessor.project_id,
            predecessor_budget_id=predecessor.id,
            name=command.name,
            currency_code=predecessor.currency_code,
            revision=(latest.revision + 1) if latest is not None else 1,
            created_at=now,
        )
        try:
            with self._session.begin_nested():
                self._budget_repo.add(successor)
                self._budget_repo.flush()
                for source in self._budget_repo.list_lines(predecessor.id):
                    cloned = BudgetLine.create(
                        tenant_id=successor.tenant_id,
                        organization_id=successor.organization_id,
                        budget_id=successor.id,
                        project_id=successor.project_id,
                        cost_code_id=source.cost_code_id,
                        task_id=source.task_id,
                        description=source.description,
                        amount=source.amount,
                        currency_code=successor.currency_code,
                        created_at=now,
                    )
                    self._budget_repo.add_line(cloned)
                self._budget_repo.flush()
        except IntegrityError as exc:
            self._translate_create_conflict(exc)
        self._record_budget_audit(operation="create_successor", budget=successor)
        event = BudgetVersionCreated(
            tenant_id=successor.tenant_id,
            organization_id=successor.organization_id,
            project_id=successor.project_id,
            budget_id=successor.id,
            status=successor.status,
            predecessor_budget_id=successor.predecessor_budget_id,
            occurred_at=now,
        )
        if self._record_event is not None:
            self._record_event(event)
        self._session.flush()
        return map_budget(successor)


    def submit_budget(self, command: FinancialVersionedBudgetCommand) -> FinancialBudgetMutationDto:
        submitted_by = self._command_actor_id()
        require_permission(self._user_session, "budget.manage", operation_label="submit project budget")
        budget = self._require_budget(command.budget_id)
        require_project_permission(
            self._user_session, budget.project_id, "budget.manage", operation_label="submit project budget"
        )
        if budget.row_version != command.expected_version:
            raise ConcurrencyError("Budget changed since you opened it.", code="STALE_WRITE")
        lines = self._budget_repo.list_lines(command.budget_id)
        if not lines:
            raise BusinessRuleError("Cannot submit an empty budget.", code="PROJECT_BUDGET_EMPTY")
        now = self._clock.now()
        budget.submit(submitted_by=submitted_by, submitted_at=now, notes=command.notes)
        self._budget_repo.update(budget, expected_row_version=command.expected_version)
        self._record_budget_audit(operation="submit", budget=budget)
        event = BudgetStatusChanged(
            tenant_id=budget.tenant_id,
            organization_id=budget.organization_id,
            project_id=budget.project_id,
            budget_id=budget.id,
            change_type=BudgetStatusChangeType.SUBMITTED,
            occurred_at=budget.updated_at,
        )
        if self._record_event is not None:
            self._record_event(event)
        self._session.flush()
        return map_budget(budget)


    def close_budget(self, command: FinancialVersionedBudgetCommand) -> FinancialBudgetMutationDto:
        closed_by = self._command_actor_id()
        require_permission(self._user_session, "budget.approve", operation_label="close project budget")
        budget = self._require_budget(command.budget_id)
        require_project_permission(
            self._user_session, budget.project_id, "budget.approve", operation_label="close project budget"
        )
        if budget.row_version != command.expected_version:
            raise ConcurrencyError("Budget changed since you opened it.", code="STALE_WRITE")
        now = self._clock.now()
        budget.close(closed_by=closed_by, closed_at=now, notes=command.notes)
        self._budget_repo.update(budget, expected_row_version=command.expected_version)
        self._record_budget_audit(operation="close", budget=budget)
        event = BudgetStatusChanged(
            tenant_id=budget.tenant_id,
            organization_id=budget.organization_id,
            project_id=budget.project_id,
            budget_id=budget.id,
            change_type=BudgetStatusChangeType.CLOSED,
            occurred_at=budget.updated_at,
        )
        if self._record_event is not None:
            self._record_event(event)
        self._session.flush()
        return map_budget(budget)


    def update_budget_header(self, command: FinancialUpdateBudgetCommand) -> FinancialBudgetMutationDto:
        # currency_code is deliberately not a parameter here â€” a budget's
        # currency is immutable after creation once lines may exist in it.
        require_permission(self._user_session, "budget.manage", operation_label="update project budget")
        budget = self._require_budget(command.budget_id)
        require_project_permission(
            self._user_session, budget.project_id, "budget.manage", operation_label="update project budget"
        )
        budget.ensure_mutable()
        if budget.row_version != command.expected_version:
            raise ConcurrencyError("Budget changed since you opened it.", code="STALE_WRITE")
        if command.name is not None:
            budget.rename(command.name)
        if command.notes is not None:
            budget.update_notes(command.notes)
        budget.touch(updated_at=self._clock.now())
        self._budget_repo.update(budget, expected_row_version=command.expected_version)
        self._record_budget_audit(operation="update_header", budget=budget)
        event = BudgetProfileUpdated(
            tenant_id=budget.tenant_id,
            organization_id=budget.organization_id,
            project_id=budget.project_id,
            budget_id=budget.id,
            occurred_at=budget.updated_at,
        )
        if self._record_event is not None:
            self._record_event(event)
        self._session.flush()
        return map_budget(budget)


    def delete_budget(self, command: FinancialVersionedBudgetCommand) -> ProjectBudget:
        require_permission(self._user_session, "budget.manage", operation_label="delete project budget")
        budget = self._require_budget(command.budget_id)
        require_project_permission(
            self._user_session, budget.project_id, "budget.manage", operation_label="delete project budget"
        )
        if budget.status != BudgetStatus.DRAFT:
            raise BusinessRuleError(
                f"Budget cannot be deleted in status '{budget.status.value}'.",
                code="PROJECT_BUDGET_DELETE_STATUS_INVALID",
            )
        # Atomic delete-if-version-matches: a concurrent submit between this
        # DRAFT check and the delete call bumps row_version, so the delete
        # itself (not a redundant manual check here) surfaces STALE_WRITE.
        self._budget_repo.delete(command.budget_id, expected_row_version=command.expected_version)
        self._record_budget_audit(operation="delete", budget=budget)
        event = BudgetRemoved(
            tenant_id=budget.tenant_id,
            organization_id=budget.organization_id,
            project_id=budget.project_id,
            budget_id=budget.id,
            occurred_at=self._clock.now(),
        )
        if self._record_event is not None:
            self._record_event(event)
        self._session.flush()
        return budget


    @staticmethod
    def _integrity_message(exc: IntegrityError) -> str:
        # Deliberately NOT `str(exc)`/`.statement` â€” both embed the full
        # failing SQL statement, whose column list always contains the
        # literal word "revision" for this table regardless of which
        # constraint actually failed, which would make every conflict here
        # misidentify as a revision conflict. `.orig` (the raw DBAPI
        # exception) carries only the constraint/column text that actually
        # violated â€” precise on both SQLite (columns) and PostgreSQL
        # (named constraint).
        orig_message = str(getattr(exc, "orig", "") or "")
        return (orig_message or str(exc)).lower()


    def _translate_create_conflict(self, exc: IntegrityError) -> None:
        message = self._integrity_message(exc)
        if _REVISION_CONSTRAINT in message or "revision" in message:
            raise ConcurrencyError(
                "Another budget revision was created for this project concurrently. "
                "Refresh and try again.",
                code="PROJECT_BUDGET_REVISION_CONFLICT",
            ) from exc
        if _OPEN_VERSION_CONSTRAINT in message or "project_finance_budgets" in message:
            raise BusinessRuleError(
                "A draft or submitted budget already exists for this project.",
                code="PROJECT_BUDGET_OPEN_VERSION_EXISTS",
            ) from exc
        raise exc


    def _require_budget(self, budget_id: str) -> ProjectBudget:
        budget = self._budget_repo.get(budget_id)
        if budget is None:
            raise NotFoundError("Project budget not found.", code="PROJECT_BUDGET_NOT_FOUND")
        return budget


    def _require_context(self, operation_label: str) -> TenantContext:
        if self._tenant_context_service is None:
            raise BusinessRuleError(
                f"Active organization context is required to {operation_label}.",
                code="TENANT_CONTEXT_REQUIRED",
            )
        return self._tenant_context_service.require_organization_context(
            operation_label=operation_label
        )


    def _record_budget_audit(self, *, operation: str, budget: ProjectBudget) -> None:
        full_operation = f"project_budget.{operation}"
        record_audit_entry(
            self,
            operation=full_operation,
            entity_type="project_budget",
            entity_id=budget.id,
            entity_parent_id=budget.project_id,
            module="project_management",
            category="FINANCIAL",
            after_data=self._budget_audit_value(budget),
            workspace_id=budget.project_id,
            source="application",
            severity="high",
            metadata={"action": operation},
            commit=False,
            fail_closed=True,
        )
        record_activity(
            self,
            action=full_operation,
            entity_type="project_budget",
            entity_id=budget.id,
            parent_entity_id=budget.project_id,
            module="project_management",
            workspace_id=budget.project_id,
            details={"action": operation},
            commit=False,
        )


    @staticmethod
    def _budget_audit_value(budget: ProjectBudget) -> dict[str, Any]:
        return {
            "name": budget.name,
            "status": budget.status.value,
            "revision": budget.revision,
            "currency_code": budget.currency_code,
            "row_version": budget.row_version,
        }



__all__ = ["BudgetLifecycleCommands"]

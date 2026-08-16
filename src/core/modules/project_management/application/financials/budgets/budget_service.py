from __future__ import annotations

import json
from decimal import Decimal

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.core.modules.project_management.access.scope_permissions import require_project_permission
from src.core.modules.project_management.application.common.clock import Clock
from src.core.modules.project_management.application.common.module_guard import (
    ProjectManagementModuleGuardMixin,
)
from src.core.modules.project_management.application.financials.budgets.approval_result import (
    BudgetApprovalOutcome,
    BudgetApprovalResult,
)
from src.core.modules.project_management.contracts.repositories.finance.budgets.budget import (
    ProjectBudgetRepository,
)
from src.core.modules.project_management.contracts.repositories.finance.configuration.financial_configuration import (
    ProjectCostCodeRepository,
    ProjectFinancialProfileRepository,
)
from src.core.modules.project_management.contracts.repositories.projects.project import ProjectRepository
from src.core.modules.project_management.contracts.repositories.tasks.task import TaskRepository
from src.core.modules.project_management.domain.financials.budget import (
    BudgetLine,
    BudgetStatus,
    ProjectBudget,
)
from src.core.modules.project_management.domain.financials.configuration import CostCodePolicy
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
)
from src.core.platform.domain.approval.policy import is_governance_required
from src.core.shared.audit import record_audit_entry
from src.core.shared.events.domain_events import domain_events

_UNSET = object()

_OPEN_VERSION_CONSTRAINT = "uq_pf_budgets_one_open_per_project"
_APPROVED_CONSTRAINT = "uq_pf_budgets_one_approved_per_project"
_REVISION_CONSTRAINT = "uq_pf_budget_project_revision"


class BudgetService(ProjectManagementModuleGuardMixin):
    """Governed lifecycle for the versioned ``ProjectBudget``/``BudgetLine``
    aggregate — see docs/pm_modernization/project_budget_lifecycle_plan.md.

    ``approve_budget`` names direct application and governed request creation
    as separate successful outcomes. Both direct application and the
    composition-registered decision handlers funnel through the same internal
    mutation methods; those handlers rely on their already-authorized callers
    and never expose an approval-bypass flag.
    """

    def __init__(
        self,
        *,
        session: Session,
        budget_repo: ProjectBudgetRepository,
        project_repo: ProjectRepository,
        financial_profile_repo: ProjectFinancialProfileRepository,
        cost_code_repo: ProjectCostCodeRepository,
        task_repo: TaskRepository,
        clock: Clock,
        user_session=None,
        enterprise_audit_service=None,
        module_catalog_service=None,
        tenant_context_service: TenantContextService | None = None,
        approval_service=None,
    ) -> None:
        self._session = session
        self._budget_repo = budget_repo
        self._project_repo = project_repo
        self._financial_profile_repo = financial_profile_repo
        self._cost_code_repo = cost_code_repo
        self._task_repo = task_repo
        self._clock = clock
        self._user_session = user_session
        self._enterprise_audit_service = enterprise_audit_service
        self._module_catalog_service = module_catalog_service
        self._tenant_context_service = tenant_context_service
        self._approval_service = approval_service

    # -- Reads ------------------------------------------------------------

    def get_budget(self, budget_id: str) -> ProjectBudget:
        require_permission(self._user_session, "finance.read", operation_label="view project budget")
        budget = self._require_budget(budget_id)
        require_project_permission(
            self._user_session, budget.project_id, "finance.read", operation_label="view project budget"
        )
        return budget

    def list_budgets_for_project(
        self, project_id: str, *, include_superseded: bool = True
    ) -> list[ProjectBudget]:
        require_permission(self._user_session, "finance.read", operation_label="list project budgets")
        require_project_permission(
            self._user_session, project_id, "finance.read", operation_label="list project budgets"
        )
        return self._budget_repo.list_for_project(project_id, include_superseded=include_superseded)

    def get_approved_budget(self, project_id: str) -> ProjectBudget | None:
        require_permission(
            self._user_session, "finance.read", operation_label="view approved project budget"
        )
        require_project_permission(
            self._user_session,
            project_id,
            "finance.read",
            operation_label="view approved project budget",
        )
        return self._budget_repo.get_approved_for_project(project_id)

    def list_lines(self, budget_id: str) -> list[BudgetLine]:
        require_permission(
            self._user_session, "finance.read", operation_label="list project budget lines"
        )
        budget = self._require_budget(budget_id)
        require_project_permission(
            self._user_session,
            budget.project_id,
            "finance.read",
            operation_label="list project budget lines",
        )
        return self._budget_repo.list_lines(budget_id)

    def get_totals_by_cost_code(self, budget_id: str) -> dict[str, Decimal]:
        totals: dict[str, Decimal] = {}
        for line in self.list_lines(budget_id):
            totals[line.cost_code_id] = totals.get(line.cost_code_id, Decimal("0")) + line.amount
        return totals

    def get_totals_by_task(self, budget_id: str) -> dict[str, Decimal]:
        totals: dict[str, Decimal] = {}
        for line in self.list_lines(budget_id):
            key = line.task_id or ""
            totals[key] = totals.get(key, Decimal("0")) + line.amount
        return totals

    # -- Lifecycle ----------------------------------------------------------

    def create_budget(
        self, project_id: str, name: str, currency_code: str | None = None
    ) -> ProjectBudget:
        require_permission(self._user_session, "budget.manage", operation_label="create project budget")
        require_project_permission(
            self._user_session, project_id, "budget.manage", operation_label="create project budget"
        )
        project = self._project_repo.get(project_id)
        if project is None:
            raise NotFoundError("Project not found.", code="PROJECT_NOT_FOUND")
        profile = self._financial_profile_repo.get_by_project(project_id)
        if profile is None:
            raise NotFoundError(
                "Project financial profile not found; configure the project's "
                "finance settings before creating a budget.",
                code="PROJECT_FINANCIAL_PROFILE_NOT_FOUND",
            )
        context = self._require_context("create project budget")
        if self._budget_repo.has_open_for_project(project_id):
            raise BusinessRuleError(
                "A draft or submitted budget already exists for this project.",
                code="PROJECT_BUDGET_OPEN_VERSION_EXISTS",
            )
        latest = self._budget_repo.get_latest_for_project(project_id)
        revision = (latest.revision + 1) if latest is not None else 1
        now = self._clock.now()
        budget = ProjectBudget.create(
            tenant_id=context.tenant_id,
            organization_id=context.organization_id,
            project_id=project_id,
            name=name,
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
        self._commit()
        domain_events.budgets_changed.emit(project_id)
        return budget

    def submit_budget(
        self, budget_id: str, submitted_by: str, notes: str = "", *, expected_version: int
    ) -> ProjectBudget:
        require_permission(self._user_session, "budget.manage", operation_label="submit project budget")
        budget = self._require_budget(budget_id)
        require_project_permission(
            self._user_session, budget.project_id, "budget.manage", operation_label="submit project budget"
        )
        if budget.row_version != expected_version:
            raise ConcurrencyError("Budget changed since you opened it.", code="STALE_WRITE")
        lines = self._budget_repo.list_lines(budget_id)
        if not lines:
            raise BusinessRuleError("Cannot submit an empty budget.", code="PROJECT_BUDGET_EMPTY")
        now = self._clock.now()
        budget.submit(submitted_by=submitted_by, submitted_at=now, notes=notes)
        self._budget_repo.update(budget, expected_row_version=expected_version)
        self._record_budget_audit(operation="submit", budget=budget)
        self._commit()
        domain_events.budgets_changed.emit(budget.project_id)
        return budget

    def approve_budget(
        self, budget_id: str, *, approved_by: str, notes: str = "", expected_version: int
    ) -> BudgetApprovalResult:
        budget = self._require_budget(budget_id)
        governed = self._is_approval_governed()
        # A governed requester needs approval.request, while only a direct
        # approver needs budget.approve. Collapsing these checks would prevent
        # valid governance-only reviewers from submitting a decision request.
        if governed:
            require_permission(
                self._user_session, "approval.request", operation_label="request budget approval"
            )
            require_project_permission(
                self._user_session,
                budget.project_id,
                "approval.request",
                operation_label="request budget approval",
            )
        else:
            require_permission(
                self._user_session, "budget.approve", operation_label="approve project budget"
            )
            require_project_permission(
                self._user_session,
                budget.project_id,
                "budget.approve",
                operation_label="approve project budget",
            )
        if budget.row_version != expected_version:
            raise ConcurrencyError("Budget changed since you opened it.", code="STALE_WRITE")
        if governed:
            req = self._approval_service.request_change(
                request_type="budget.approve",
                entity_type="project_budget",
                entity_id=budget_id,
                project_id=budget.project_id,
                payload={
                    "budget_id": budget_id,
                    "expected_version": expected_version,
                    "notes": notes,
                },
            )
            return BudgetApprovalResult(
                outcome=BudgetApprovalOutcome.PENDING_APPROVAL,
                budget_id=budget.id,
                project_id=budget.project_id,
                budget_status=budget.status,
                row_version=budget.row_version,
                approval_request_id=req.id,
            )
        approved = self._apply_approval_decision(
            budget_id=budget_id,
            approved_by=approved_by,
            expected_version=expected_version,
            notes=notes,
            commit=True,
        )
        return BudgetApprovalResult(
            outcome=BudgetApprovalOutcome.APPLIED,
            budget_id=approved.id,
            project_id=approved.project_id,
            budget_status=approved.status,
            row_version=approved.row_version,
        )

    def reject_budget(
        self,
        budget_id: str,
        *,
        rejected_by: str,
        expected_version: int,
        notes: str = "",
        commit: bool = True,
    ) -> ProjectBudget:
        require_permission(self._user_session, "budget.approve", operation_label="reject project budget")
        budget = self._require_budget(budget_id)
        require_project_permission(
            self._user_session,
            budget.project_id,
            "budget.approve",
            operation_label="reject project budget",
        )
        return self._apply_rejection_decision(
            budget_id=budget_id,
            rejected_by=rejected_by,
            expected_version=expected_version,
            notes=notes,
            commit=commit,
        )

    def close_budget(
        self, budget_id: str, closed_by: str, notes: str = "", *, expected_version: int
    ) -> ProjectBudget:
        require_permission(self._user_session, "budget.approve", operation_label="close project budget")
        budget = self._require_budget(budget_id)
        require_project_permission(
            self._user_session, budget.project_id, "budget.approve", operation_label="close project budget"
        )
        if budget.row_version != expected_version:
            raise ConcurrencyError("Budget changed since you opened it.", code="STALE_WRITE")
        now = self._clock.now()
        budget.close(closed_by=closed_by, closed_at=now, notes=notes)
        self._budget_repo.update(budget, expected_row_version=expected_version)
        self._record_budget_audit(operation="close", budget=budget)
        self._commit()
        domain_events.budgets_changed.emit(budget.project_id)
        return budget

    def update_budget_header(
        self, budget_id: str, *, name: str | None = None, notes: str | None = None, expected_version: int
    ) -> ProjectBudget:
        # currency_code is deliberately not a parameter here — a budget's
        # currency is immutable after creation once lines may exist in it.
        require_permission(self._user_session, "budget.manage", operation_label="update project budget")
        budget = self._require_budget(budget_id)
        require_project_permission(
            self._user_session, budget.project_id, "budget.manage", operation_label="update project budget"
        )
        budget.ensure_mutable()
        if budget.row_version != expected_version:
            raise ConcurrencyError("Budget changed since you opened it.", code="STALE_WRITE")
        if name is not None:
            budget.rename(name)
        if notes is not None:
            budget.update_notes(notes)
        budget.touch(updated_at=self._clock.now())
        self._budget_repo.update(budget, expected_row_version=expected_version)
        self._record_budget_audit(operation="update_header", budget=budget)
        self._commit()
        domain_events.budgets_changed.emit(budget.project_id)
        return budget

    def delete_budget(self, budget_id: str, *, expected_version: int) -> None:
        require_permission(self._user_session, "budget.manage", operation_label="delete project budget")
        budget = self._require_budget(budget_id)
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
        self._budget_repo.delete(budget_id, expected_row_version=expected_version)
        self._record_budget_audit(operation="delete", budget=budget)
        self._commit()
        domain_events.budgets_changed.emit(budget.project_id)

    # -- Line mutations (each also advances the parent budget's row_version) -

    def add_line(
        self,
        budget_id: str,
        *,
        cost_code_id: str,
        task_id: str | None = None,
        description: str,
        amount: Decimal,
        currency_code: str | None = None,
        expected_budget_version: int,
    ) -> BudgetLine:
        require_permission(self._user_session, "budget.manage", operation_label="add project budget line")
        budget = self._require_budget(budget_id)
        require_project_permission(
            self._user_session,
            budget.project_id,
            "budget.manage",
            operation_label="add project budget line",
        )
        budget.ensure_mutable()
        if budget.row_version != expected_budget_version:
            raise ConcurrencyError("Budget changed since you opened it.", code="STALE_WRITE")
        resolved_currency = currency_code or budget.currency_code
        if resolved_currency != budget.currency_code:
            raise BusinessRuleError(
                "Budget line currency must match the budget's currency.",
                code="PROJECT_BUDGET_LINE_CURRENCY_MISMATCH",
            )
        self._require_eligible_cost_code(budget.project_id, cost_code_id)
        if task_id is not None:
            self._require_task_in_project(task_id, budget.project_id)
        now = self._clock.now()
        line = BudgetLine.create(
            tenant_id=budget.tenant_id,
            organization_id=budget.organization_id,
            budget_id=budget.id,
            project_id=budget.project_id,
            cost_code_id=cost_code_id,
            task_id=task_id,
            description=description,
            amount=amount,
            currency_code=resolved_currency,
            created_at=now,
        )
        self._budget_repo.add_line(line)
        budget.touch(updated_at=now)
        self._budget_repo.update(budget, expected_row_version=expected_budget_version)
        self._record_line_audit(operation="add_line", line=line, budget=budget)
        self._commit()
        domain_events.budgets_changed.emit(budget.project_id)
        return line

    def update_line(
        self,
        line_id: str,
        *,
        expected_line_version: int,
        expected_budget_version: int,
        cost_code_id: str | None = None,
        task_id: str | None | object = _UNSET,
        description: str | None = None,
        amount: Decimal | None = None,
        currency_code: str | None = None,
    ) -> BudgetLine:
        require_permission(
            self._user_session, "budget.manage", operation_label="update project budget line"
        )
        line = self._require_line(line_id)
        budget = self._require_budget(line.budget_id)
        require_project_permission(
            self._user_session,
            budget.project_id,
            "budget.manage",
            operation_label="update project budget line",
        )
        budget.ensure_mutable()
        if budget.row_version != expected_budget_version:
            raise ConcurrencyError("Budget changed since you opened it.", code="STALE_WRITE")
        if line.row_version != expected_line_version:
            raise ConcurrencyError("Budget line changed since you opened it.", code="STALE_WRITE")

        resolved_cost_code_id = line.cost_code_id if cost_code_id is None else cost_code_id
        resolved_task_id = line.task_id if task_id is _UNSET else task_id
        resolved_currency = line.currency_code if currency_code is None else currency_code

        if resolved_currency != budget.currency_code:
            raise BusinessRuleError(
                "Budget line currency must match the budget's currency.",
                code="PROJECT_BUDGET_LINE_CURRENCY_MISMATCH",
            )
        if resolved_cost_code_id != line.cost_code_id:
            self._require_eligible_cost_code(budget.project_id, resolved_cost_code_id)
        if resolved_task_id is not None and resolved_task_id != line.task_id:
            self._require_task_in_project(resolved_task_id, budget.project_id)

        now = self._clock.now()
        line.cost_code_id = resolved_cost_code_id
        line.task_id = resolved_task_id
        if description is not None:
            line.description = description
        if amount is not None:
            line.amount = amount
        line.currency_code = resolved_currency
        line.updated_at = now

        self._budget_repo.update_line(line, expected_row_version=expected_line_version)
        budget.touch(updated_at=now)
        self._budget_repo.update(budget, expected_row_version=expected_budget_version)
        self._record_line_audit(operation="update_line", line=line, budget=budget)
        self._commit()
        domain_events.budgets_changed.emit(budget.project_id)
        return line

    def delete_line(
        self, line_id: str, *, expected_line_version: int, expected_budget_version: int
    ) -> None:
        require_permission(
            self._user_session, "budget.manage", operation_label="delete project budget line"
        )
        line = self._require_line(line_id)
        budget = self._require_budget(line.budget_id)
        require_project_permission(
            self._user_session,
            budget.project_id,
            "budget.manage",
            operation_label="delete project budget line",
        )
        budget.ensure_mutable()
        if budget.row_version != expected_budget_version:
            raise ConcurrencyError("Budget changed since you opened it.", code="STALE_WRITE")
        # Atomic delete-if-version-matches — see delete_budget's note.
        self._budget_repo.delete_line(line_id, expected_row_version=expected_line_version)
        now = self._clock.now()
        budget.touch(updated_at=now)
        self._budget_repo.update(budget, expected_row_version=expected_budget_version)
        self._record_line_audit(operation="delete_line", line=line, budget=budget)
        self._commit()
        domain_events.budgets_changed.emit(budget.project_id)

    # -- Internal, unchecked decision application ----------------------------
    # Reachable only through approve_budget/reject_budget (already permission-
    # checked) or through the composition-registered approval apply/reject
    # handlers (already authorized by ApprovalService's own "approval.decide"
    # check). Neither ever checks "budget.approve" itself — that is
    # deliberate, not an oversight: a governance-only approver holding
    # "approval.decide" but not "budget.approve" must still be able to have
    # their decision applied.

    def _apply_approval_decision(
        self, *, budget_id: str, approved_by: str, expected_version: int, notes: str, commit: bool
    ) -> ProjectBudget:
        budget = self._require_budget(budget_id)
        now = self._clock.now()
        previous = self._budget_repo.get_approved_for_project(budget.project_id)
        try:
            with self._session.begin_nested():
                if previous is not None:
                    previous_expected_version = previous.row_version
                    previous.supersede(superseded_by=approved_by, superseded_at=now)
                    self._budget_repo.update(previous, expected_row_version=previous_expected_version)
                    self._budget_repo.flush()
                budget_expected_version = expected_version
                budget.approve(approved_by=approved_by, approved_at=now, notes=notes)
                self._budget_repo.update(budget, expected_row_version=budget_expected_version)
                self._budget_repo.flush()
        except IntegrityError as exc:
            if self._is_approval_conflict(exc):
                raise BusinessRuleError(
                    "Another budget version was approved for this project concurrently.",
                    code="PROJECT_BUDGET_APPROVAL_CONFLICT",
                ) from exc
            raise
        self._record_budget_audit(operation="approve", budget=budget)
        if commit:
            self._commit()
            domain_events.budgets_changed.emit(budget.project_id)
        else:
            self._session.flush()
        return budget

    def _apply_rejection_decision(
        self, *, budget_id: str, rejected_by: str, expected_version: int, notes: str, commit: bool
    ) -> ProjectBudget:
        budget = self._require_budget(budget_id)
        if budget.row_version != expected_version:
            raise ConcurrencyError("Budget changed since you opened it.", code="STALE_WRITE")
        now = self._clock.now()
        budget.reject(rejected_by=rejected_by, rejected_at=now, notes=notes)
        self._budget_repo.update(budget, expected_row_version=expected_version)
        self._record_budget_audit(operation="reject", budget=budget)
        if commit:
            self._commit()
            domain_events.budgets_changed.emit(budget.project_id)
        else:
            self._session.flush()
        return budget

    def _is_approval_governed(self) -> bool:
        return self._approval_service is not None and is_governance_required("budget.approve")

    # -- Conflict translation (concurrent writes surface named errors, not
    #    raw IntegrityError) -------------------------------------------------

    @staticmethod
    def _integrity_message(exc: IntegrityError) -> str:
        # Deliberately NOT `str(exc)`/`.statement` — both embed the full
        # failing SQL statement, whose column list always contains the
        # literal word "revision" for this table regardless of which
        # constraint actually failed, which would make every conflict here
        # misidentify as a revision conflict. `.orig` (the raw DBAPI
        # exception) carries only the constraint/column text that actually
        # violated — precise on both SQLite (columns) and PostgreSQL
        # (named constraint).
        orig_message = str(getattr(exc, "orig", "") or "")
        return (orig_message or str(exc)).lower()

    @classmethod
    def _is_approval_conflict(cls, exc: IntegrityError) -> bool:
        message = cls._integrity_message(exc)
        # Reachable only from _apply_approval_decision, which never inserts
        # a new open (draft/submitted) row — any unique violation on this
        # table reached from here is necessarily the one-approved-per-
        # project index, so a bare table-name match is unambiguous (SQLite
        # never surfaces the partial index's name in its error text).
        return _APPROVED_CONSTRAINT in message or "project_finance_budgets" in message

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
        raise

    # -- Shared helpers -------------------------------------------------------

    def _require_budget(self, budget_id: str) -> ProjectBudget:
        budget = self._budget_repo.get(budget_id)
        if budget is None:
            raise NotFoundError("Project budget not found.", code="PROJECT_BUDGET_NOT_FOUND")
        return budget

    def _require_line(self, line_id: str) -> BudgetLine:
        line = self._budget_repo.get_line(line_id)
        if line is None:
            raise NotFoundError("Project budget line not found.", code="PROJECT_BUDGET_LINE_NOT_FOUND")
        return line

    def _require_context(self, operation_label: str) -> TenantContext:
        if self._tenant_context_service is None:
            raise BusinessRuleError(
                f"Active organization context is required to {operation_label}.",
                code="TENANT_CONTEXT_REQUIRED",
            )
        return self._tenant_context_service.require_organization_context(
            operation_label=operation_label
        )

    def _require_eligible_cost_code(self, project_id: str, cost_code_id: str) -> None:
        cost_code = self._cost_code_repo.get(cost_code_id)
        if cost_code is None:
            raise NotFoundError(
                "Cost code not found.", code="PROJECT_BUDGET_LINE_COST_CODE_NOT_FOUND"
            )
        if not cost_code.is_effective_on(self._clock.today()):
            raise BusinessRuleError(
                "Cost code is not active or effective for this date.",
                code="PROJECT_BUDGET_LINE_COST_CODE_INACTIVE",
            )
        profile = self._financial_profile_repo.get_by_project(project_id)
        if profile is not None and profile.cost_code_policy == CostCodePolicy.RESTRICTED:
            allowed_ids = {
                restriction.cost_code_id
                for restriction in self._cost_code_repo.list_restrictions(project_id)
            }
            if cost_code_id not in allowed_ids:
                raise BusinessRuleError(
                    "This cost code is not permitted for this project.",
                    code="PROJECT_BUDGET_LINE_COST_CODE_NOT_PERMITTED",
                )

    def _require_task_in_project(self, task_id: str, project_id: str) -> None:
        task = self._task_repo.get(task_id)
        if task is None:
            raise NotFoundError("Task not found.", code="TASK_NOT_FOUND")
        if task.project_id != project_id:
            raise BusinessRuleError(
                "Task does not belong to this project.",
                code="PROJECT_BUDGET_LINE_TASK_PROJECT_MISMATCH",
            )

    def _record_budget_audit(self, *, operation: str, budget: ProjectBudget) -> None:
        record_audit_entry(
            self,
            operation=f"project_budget.{operation}",
            entity_type="project_budget",
            entity_id=budget.id,
            entity_parent_id=budget.project_id,
            module="project_management",
            old_value=None,
            new_value=self._budget_audit_value(budget),
            workspace_id=budget.project_id,
            source="application",
            severity="high",
            compliance_tag="financial",
            metadata={"action": operation},
            commit=False,
            fail_closed=True,
        )

    def _record_line_audit(self, *, operation: str, line: BudgetLine, budget: ProjectBudget) -> None:
        record_audit_entry(
            self,
            operation=f"project_budget_line.{operation}",
            entity_type="project_budget_line",
            entity_id=line.id,
            entity_parent_id=budget.id,
            module="project_management",
            old_value=None,
            new_value=self._line_audit_value(line),
            workspace_id=budget.project_id,
            source="application",
            severity="high",
            compliance_tag="financial",
            metadata={"action": operation},
            commit=False,
            fail_closed=True,
        )

    @staticmethod
    def _budget_audit_value(budget: ProjectBudget) -> str:
        return json.dumps(
            {
                "name": budget.name,
                "status": budget.status.value,
                "revision": budget.revision,
                "currency_code": budget.currency_code,
                "row_version": budget.row_version,
            },
            sort_keys=True,
        )

    @staticmethod
    def _line_audit_value(line: BudgetLine) -> str:
        return json.dumps(
            {
                "cost_code_id": line.cost_code_id,
                "task_id": line.task_id,
                "amount": str(line.amount),
                "currency_code": line.currency_code,
                "row_version": line.row_version,
            },
            sort_keys=True,
        )

    def _commit(self) -> None:
        try:
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise


__all__ = ["BudgetService"]

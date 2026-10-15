from __future__ import annotations

from collections.abc import Callable
from datetime import date
from decimal import Decimal

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
    CostEntryRecorded,
    CostEntryRemoved,
    CostEntryStatusChanged,
    CostEntryStatusChangeType,
    CostEntryUpdated,
)
from src.core.modules.project_management.application.financials.cost.entries.manual_source import (
    build_manual_content,
    build_manual_source,
)
from src.core.modules.project_management.contracts.financial_sources.reference import (
    FinancialSourceReference,
    financial_source_content_hash,
)
from src.core.modules.project_management.contracts.repositories.finance.configuration.financial_configuration import (
    ProjectCostCodeRepository,
    ProjectFinancialProfileRepository,
)
from src.core.modules.project_management.contracts.repositories.finance.cost_entries.cost_entry import (
    ProjectCostEntryRepository,
)
from src.core.modules.project_management.contracts.repositories.projects.project import (
    ProjectRepository,
)
from src.core.modules.project_management.contracts.repositories.resources.resource import (
    ResourceRepository,
)
from src.core.modules.project_management.contracts.repositories.tasks.task import (
    TaskRepository,
)
from src.core.modules.project_management.domain.financials.configuration import (
    CostCodePolicy,
    FinancialProfileStatus,
)
from src.core.modules.project_management.domain.financials.cost_entry import (
    ProjectCostEntry,
    ProjectCostEntryKind,
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
from src.core.platform.domain.finance import Money
from src.core.shared.time.clock import CalendarClock


class ProjectCostEntryLifecycleCommandHandler(ProjectManagementModuleGuardMixin):
    """Caller-owned actual-cost manual commands."""

    def __init__(
        self,
        *,
        session: Session,
        entry_repo: ProjectCostEntryRepository,
        project_repo: ProjectRepository,
        financial_profile_repo: ProjectFinancialProfileRepository,
        cost_code_repo: ProjectCostCodeRepository,
        task_repo: TaskRepository,
        resource_repo: ResourceRepository,
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
        self._project_repo = project_repo
        self._financial_profile_repo = financial_profile_repo
        self._cost_code_repo = cost_code_repo
        self._task_repo = task_repo
        self._resource_repo = resource_repo
        self._clock = clock
        self._user_session = user_session
        self._enterprise_audit_service = enterprise_audit_service
        self._activity_service = activity_service
        self._module_catalog_service = module_catalog_service
        self._tenant_context_service = tenant_context_service
        self._record_event = record_event

    def create_manual_entry(
        self,
        *,
        project_id: str,
        command_id: str,
        description: str,
        amount: Decimal,
        currency_code: str,
        transaction_date: date,
        cost_code_id: str,
        entry_kind: ProjectCostEntryKind | str = ProjectCostEntryKind.ACTUAL,
        task_id: str | None = None,
        resource_id: str | None = None,
    ) -> ProjectCostEntry:
        self._require_command_permission(
            project_id, "project_cost.create", "create project cost entry"
        )
        context = self._require_scope("create project cost entry")
        self._require_project(project_id)
        profile = self._require_active_profile(project_id)
        del profile
        kind = self._resolve_draft_kind(entry_kind)
        money = Money.of(amount, currency_code)
        self._require_dimensions(
            project_id=project_id,
            cost_code_id=cost_code_id,
            transaction_date=transaction_date,
            task_id=task_id,
            resource_id=resource_id,
            organization_id=context.organization_id,
        )
        source = build_manual_source(
            tenant_id=context.tenant_id,
            organization_id=context.organization_id,
            project_id=project_id,
            command_id=command_id,
            content=build_manual_content(
                description=description,
                kind=kind,
                money=money,
                transaction_date=transaction_date,
                cost_code_id=cost_code_id,
                task_id=task_id,
                resource_id=resource_id,
            ),
        )
        existing = self._entry_repo.get_by_idempotency_key(source.idempotency_key)
        if existing is not None:
            return self._resolve_replay(existing, source)
        actor_id = self._actor_id()
        now = self._clock.now()
        entry = ProjectCostEntry.create_draft(
            tenant_id=context.tenant_id,
            organization_id=context.organization_id,
            project_id=project_id,
            description=description,
            kind=kind,
            money=money,
            transaction_date=transaction_date,
            cost_code_id=cost_code_id,
            task_id=task_id,
            resource_id=resource_id,
            source=source,
            actor_id=actor_id,
            occurred_at=now,
        )
        try:
            # The savepoint translates only the source-identity race. The outer
            # Finance UoW remains the sole transaction owner.
            with self._session.begin_nested():
                self._entry_repo.add(entry)
                self._entry_repo.flush()
        except IntegrityError as exc:
            concurrent = self._entry_repo.get_by_idempotency_key(source.idempotency_key)
            if concurrent is not None:
                return self._resolve_replay(concurrent, source)
            raise BusinessRuleError(
                "Project cost entry conflicts with an existing financial source.",
                code="PROJECT_COST_ENTRY_SOURCE_CONFLICT",
            ) from exc
        self._record_audit("create", entry)
        event = CostEntryRecorded(
            tenant_id=entry.tenant_id,
            organization_id=entry.organization_id,
            project_id=entry.project_id,
            cost_entry_id=entry.id,
            status=entry.status,
            occurred_at=now,
        )
        if self._record_event is not None:
            self._record_event(event)
        self._session.flush()
        return entry

    def update_draft(
        self,
        entry_id: str,
        *,
        expected_version: int,
        description: str,
        amount: Decimal,
        currency_code: str,
        transaction_date: date,
        cost_code_id: str,
        task_id: str | None = None,
        resource_id: str | None = None,
    ) -> ProjectCostEntry:
        entry = self._require_entry(entry_id)
        self._require_manual_interactive_entry(entry, operation="edit")
        self._require_command_permission(
            entry.project_id,
            "project_cost.update_draft",
            "update project cost entry draft",
        )
        self._require_expected_version(entry, expected_version)
        context = self._require_scope("update project cost entry draft")
        money = Money.of(amount, currency_code)
        self._require_dimensions(
            project_id=entry.project_id,
            cost_code_id=cost_code_id,
            transaction_date=transaction_date,
            task_id=task_id,
            resource_id=resource_id,
            organization_id=context.organization_id,
        )
        content_hash = financial_source_content_hash(
            build_manual_content(
                description=description,
                kind=entry.entry_kind,
                money=money,
                transaction_date=transaction_date,
                cost_code_id=cost_code_id,
                task_id=task_id,
                resource_id=resource_id,
            )
        )
        actor_id = self._actor_id()
        entry.update_draft(
            description=description,
            amount=money.amount,
            currency_code=money.currency.code,
            transaction_date=transaction_date,
            cost_code_id=cost_code_id,
            task_id=task_id,
            resource_id=resource_id,
            source_content_hash=content_hash,
            updated_by=actor_id,
            updated_at=self._clock.now(),
        )
        self._entry_repo.update(entry, expected_row_version=expected_version)
        self._record_audit("update_draft", entry)
        event = CostEntryUpdated(
            tenant_id=entry.tenant_id,
            organization_id=entry.organization_id,
            project_id=entry.project_id,
            cost_entry_id=entry.id,
            occurred_at=entry.updated_at,
        )
        if self._record_event is not None:
            self._record_event(event)
        self._session.flush()
        return entry

    def delete_draft(self, entry_id: str, *, expected_version: int) -> None:
        entry = self._require_entry(entry_id)
        self._require_manual_interactive_entry(entry, operation="delete")
        self._require_command_permission(
            entry.project_id,
            "project_cost.update_draft",
            "delete project cost entry draft",
        )
        self._require_expected_version(entry, expected_version)
        if not entry.is_draft:
            raise BusinessRuleError(
                "Only a draft project cost entry can be deleted.",
                code="PROJECT_COST_ENTRY_DELETE_FORBIDDEN",
            )
        self._entry_repo.delete_draft(entry.id, expected_row_version=expected_version)
        self._record_audit("delete_draft", entry)
        event = CostEntryRemoved(
            tenant_id=entry.tenant_id,
            organization_id=entry.organization_id,
            project_id=entry.project_id,
            cost_entry_id=entry.id,
            occurred_at=self._clock.now(),
        )
        if self._record_event is not None:
            self._record_event(event)
        self._session.flush()

    def submit(self, entry_id: str, *, expected_version: int) -> ProjectCostEntry:
        entry = self._require_entry(entry_id)
        self._require_manual_interactive_entry(entry, operation="submit")
        self._require_command_permission(
            entry.project_id, "project_cost.submit", "submit project cost entry"
        )
        self._require_expected_version(entry, expected_version)
        entry.submit(actor_id=self._actor_id(), occurred_at=self._clock.now())
        self._entry_repo.update(entry, expected_row_version=expected_version)
        self._record_audit("submit", entry)
        event = CostEntryStatusChanged(
            tenant_id=entry.tenant_id,
            organization_id=entry.organization_id,
            project_id=entry.project_id,
            cost_entry_id=entry.id,
            change_type=CostEntryStatusChangeType.SUBMITTED,
            occurred_at=entry.updated_at,
        )
        if self._record_event is not None:
            self._record_event(event)
        self._session.flush()
        return entry

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

    def _require_scope(self, operation_label: str):
        if self._tenant_context_service is None:
            raise BusinessRuleError(
                f"Active organization context is required to {operation_label}.",
                code="TENANT_CONTEXT_REQUIRED",
            )
        return self._tenant_context_service.require_active_scope_ids(
            operation_label=operation_label
        )

    def _require_project(self, project_id: str) -> None:
        if self._project_repo.get(project_id) is None:
            raise NotFoundError("Project not found.", code="PROJECT_NOT_FOUND")

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

    @staticmethod
    def _resolve_draft_kind(value: ProjectCostEntryKind | str) -> ProjectCostEntryKind:
        try:
            kind = ProjectCostEntryKind(value)
        except ValueError as exc:
            raise ValidationError(
                "Project cost entry kind is invalid.",
                code="PROJECT_COST_ENTRY_KIND_INVALID",
            ) from exc
        if kind == ProjectCostEntryKind.REVERSAL:
            raise ValidationError(
                "Reversals can only be created through the reversal command.",
                code="PROJECT_COST_ENTRY_DRAFT_REVERSAL_FORBIDDEN",
            )
        return kind

    def _require_dimensions(
        self,
        *,
        project_id: str,
        cost_code_id: str,
        transaction_date: date,
        task_id: str | None,
        resource_id: str | None,
        organization_id: str,
    ) -> None:
        cost_code = self._cost_code_repo.get(cost_code_id)
        if cost_code is None:
            raise NotFoundError(
                "Cost code not found.", code="PROJECT_COST_ENTRY_COST_CODE_NOT_FOUND"
            )
        if not cost_code.is_effective_on(transaction_date):
            raise BusinessRuleError(
                "Cost code is not active or effective on the transaction date.",
                code="PROJECT_COST_ENTRY_COST_CODE_INACTIVE",
            )
        profile = self._require_active_profile(project_id)
        if profile.cost_code_policy == CostCodePolicy.RESTRICTED:
            allowed = {
                restriction.cost_code_id
                for restriction in self._cost_code_repo.list_restrictions(project_id)
            }
            if cost_code_id not in allowed:
                raise BusinessRuleError(
                    "This cost code is not permitted for the project.",
                    code="PROJECT_COST_ENTRY_COST_CODE_NOT_PERMITTED",
                )
        if task_id:
            task = self._task_repo.get(task_id)
            if task is None:
                raise NotFoundError("Task not found.", code="TASK_NOT_FOUND")
            if task.project_id != project_id:
                raise BusinessRuleError(
                    "Task does not belong to the project.",
                    code="PROJECT_COST_ENTRY_TASK_PROJECT_MISMATCH",
                )
        if resource_id:
            resource = self._resource_repo.get(resource_id)
            if resource is None:
                raise NotFoundError("Resource not found.", code="RESOURCE_NOT_FOUND")
            if resource.organization_id != organization_id:
                raise BusinessRuleError(
                    "Resource does not belong to the active organization.",
                    code="PROJECT_COST_ENTRY_RESOURCE_SCOPE_MISMATCH",
                )

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

    @staticmethod
    def _require_expected_version(
        entry: ProjectCostEntry, expected_version: int
    ) -> None:
        if entry.row_version != expected_version:
            raise ConcurrencyError(
                "Project cost entry changed since you opened it.",
                code="STALE_WRITE",
            )


__all__ = ["ProjectCostEntryLifecycleCommandHandler"]

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.core.modules.project_management.contracts.repositories.projects.project import (
    ProjectRepository,
)
from src.core.modules.project_management.contracts.repositories.tasks.task import (
    AssignmentRepository,
    DependencyRepository,
    TaskRepository,
)
from src.core.modules.project_management.contracts.uow.projects.project_unit_of_work import (
    ProjectUnitOfWorkFactory,
)
from src.core.modules.project_management.domain.enums import ProjectStatus
from src.core.modules.project_management.domain.financials.configuration import (
    ProjectFinancialProfile,
)
from src.core.modules.project_management.domain.projects.project import Project
from src.core.platform.application.tenant.tenancy.tenant_context import (
    ActiveScopeIds,
    TenantContextService,
)
from src.core.platform.common.exceptions import (
    BusinessRuleError,
    ValidationError,
)
from src.core.platform.contract.repositories.time_management.time.contracts import (
    TimeEntryRepository,
)
from src.core.platform.domain.security.auth.session import UserSessionContext
from src.core.shared.audit import record_audit_entry
from src.core.shared.events.domain_event_context import DomainEventContext
from src.core.shared.persistence.unit_of_work import UnitOfWorkFactory

# Fields diffed for the project.update activity entry -- kept in the same
# order they're shown to the user, not dataclass declaration order.
_PROJECT_UPDATE_DIFF_FIELDS: tuple[str, ...] = (
    "name",
    "code",
    "status",
    "description",
    "start_date",
    "end_date",
    "client_name",
    "client_contact",
    "site_id",
    "department_id",
    "client_party_id",
    "manager_user_id",
)


def _format_activity_diff_value(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, ProjectStatus):
        return value.value
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _diff_project_fields(
    before: Project, after: Project, fields: tuple[str, ...] = _PROJECT_UPDATE_DIFF_FIELDS
) -> dict[str, dict[str, str | None]]:
    """Field-level before/after diff for the project activity log.

    Only fields that actually changed are included, so a status-only update
    doesn't log a wall of unchanged fields alongside it.
    """
    changes: dict[str, dict[str, str | None]] = {}
    for field_name in fields:
        old_value = getattr(before, field_name, None)
        new_value = getattr(after, field_name, None)
        if old_value == new_value:
            continue
        changes[field_name] = {
            "from": _format_activity_diff_value(old_value),
            "to": _format_activity_diff_value(new_value),
        }
    return changes


class ProjectSupportMixin:
    _new_context: Callable[..., DomainEventContext]
    _require_shared_uow_factory: Callable[[], UnitOfWorkFactory]
    _session: Session
    _project_repo: ProjectRepository
    _task_repo: TaskRepository
    _dependency_repo: DependencyRepository
    _assignment_repo: AssignmentRepository
    _time_entry_repo: TimeEntryRepository | None
    _user_session: UserSessionContext | None
    _uow_factory: ProjectUnitOfWorkFactory | None
    _tenant_context_service: TenantContextService | None

    def _require_project_scope_ids(self, *, operation_label: str) -> ActiveScopeIds:
        tenant_context = self._tenant_context_service
        if tenant_context is None:
            raise BusinessRuleError(
                f"Active organization context is required for {operation_label}.",
                code="TENANT_CONTEXT_REQUIRED",
            )
        return tenant_context.require_active_scope_ids(operation_label=operation_label)

    def _validate_project_name(
        self,
        name: str,
        *,
        organization_id: str,
        exclude_id: str | None = None,
        project_repo: ProjectRepository | None = None,
    ) -> None:
        normalized_name = name.strip().lower()
        if not normalized_name:
            return
        repo = project_repo if project_repo is not None else self._project_repo
        for project in repo.list():
            if exclude_id is not None and project.id == exclude_id:
                continue
            if project.name.strip().lower() == normalized_name:
                raise ValidationError(
                    "A project with this name already exists.",
                    code="PROJECT_NAME_DUPLICATE",
                )

    def _resolve_project_code(
        self,
        code: str,
        name: str,
        *,
        exclude_id: str | None = None,
        organization_id: str | None = None,
        project_repo: ProjectRepository | None = None,
    ) -> str:
        """Normalize a manual code or auto-generate a unique code."""
        from src.core.platform.common.code_generation import (
            CodeGenerator,
            assert_code_unique,
            normalize_manual_code,
        )

        repo = project_repo if project_repo is not None else self._project_repo
        project_rows = repo.list()
        existing = {
            str(getattr(project, "code", "") or "").upper()
            for project in project_rows
            if exclude_id is None or project.id != exclude_id
        }
        manual = normalize_manual_code(code)
        if manual:
            assert_code_unique(
                manual,
                exists=lambda candidate: candidate.upper() in existing,
                label="Project code",
            )
            return manual
        return CodeGenerator().generate(
            "project",
            exists=lambda candidate: candidate.upper() in existing,
            name=(name or "").strip() or None,
            use_year=not bool((name or "").strip()),
        )

    @staticmethod
    def _is_project_code_integrity_error(exc: IntegrityError) -> bool:
        message = " ".join(
            part
            for part in [
                str(getattr(exc, "orig", "") or ""),
                str(getattr(exc, "statement", "") or ""),
                str(exc),
            ]
            if part
        ).lower()
        return "ux_projects_code" in message or "projects.project_code" in message

    @staticmethod
    def _raise_project_code_duplicate(code: str, exc: IntegrityError) -> None:
        raise ValidationError(
            f"Project code '{code}' already exists.",
            code="CODE_DUPLICATE",
        ) from exc

    def _require_project_uow_factory(self) -> ProjectUnitOfWorkFactory:
        if self._uow_factory is None:
            raise RuntimeError("Project unit of work is not configured.")
        return self._uow_factory

    def _record_financial_profile_audit(
        self,
        owner: object,
        operation: str,
        profile: ProjectFinancialProfile,
        *,
        old: ProjectFinancialProfile | None = None,
    ) -> None:
        def _snapshot(item: ProjectFinancialProfile | None) -> dict[str, Any] | None:
            if item is None:
                return None
            return {
                "billing_method": item.billing_method.value,
                "budget_control_mode": item.budget_control_mode.value,
                "cost_code_policy": item.cost_code_policy.value,
                "currency_code": item.currency_code,
                "status": item.status.value,
                "version": item.version,
            }

        before = _snapshot(old)
        after = _snapshot(profile)
        changed_fields = None
        if before is not None and after is not None:
            changed_fields = {
                key: {"before": before[key], "after": after[key]}
                for key in after
                if before.get(key) != after[key]
            }

        record_audit_entry(
            owner,
            operation=f"financial_profile.{operation}",
            entity_type="project_financial_profile",
            entity_id=profile.id,
            entity_parent_id=profile.project_id,
            module="project_management",
            category="FINANCIAL",
            before_data=before,
            after_data=after,
            changed_fields=changed_fields,
            workspace_id=profile.project_id,
            source="application",
            severity="high",
            metadata={"action": f"financial_profile.{operation}"},
            commit=False,
            fail_closed=True,
        )

    def _active_project_organization_id(self, *, operation_label: str) -> str:
        tenant_context = getattr(self, "_tenant_context_service", None)
        if tenant_context is None:
            raise BusinessRuleError(
                f"Active organization context is required for {operation_label}.",
                code="TENANT_CONTEXT_REQUIRED",
            )
        organization_id = tenant_context.require_active_organization_id(
            operation_label=operation_label
        )
        if organization_id is None:
            raise BusinessRuleError(
                f"Active organization context is required for {operation_label}.",
                code="TENANT_CONTEXT_REQUIRED",
            )
        return organization_id

    def _resolve_project_organization_id(
        self,
        organization_id: str | None,
        *,
        operation_label: str,
    ) -> str:
        active_organization_id = self._active_project_organization_id(operation_label=operation_label)
        requested_organization_id = str(organization_id or "").strip() or None
        if requested_organization_id and requested_organization_id != active_organization_id:
            raise ValidationError(
                "Project organization must match the active tenant context.",
                code="PROJECT_ORGANIZATION_MISMATCH",
            )
        return active_organization_id

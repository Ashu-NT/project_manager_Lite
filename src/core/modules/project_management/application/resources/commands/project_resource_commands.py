from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

from src.core.modules.project_management.contracts.repositories.projects.project import (
    ProjectRepository,
    ProjectResourceRepository,
)
from src.core.modules.project_management.contracts.repositories.resources.resource import ResourceRepository
from src.core.modules.project_management.contracts.repositories.tasks.task import (
    AssignmentRepository,
    TaskRepository,
)
from src.core.modules.project_management.domain.projects.project import ProjectResource
from src.core.modules.project_management.access.scope_permissions import require_project_permission
from src.core.shared.activity import record_activity
from src.core.platform.application.security.authorization.enforcement.permission_checks import require_permission
from src.core.platform.common.exceptions import BusinessRuleError, NotFoundError
from src.core.shared.events.domain_events import domain_events
from src.core.modules.project_management.application.common.currency_policy import (
    resolve_pm_currency,
)

# Fields diffed for the project_resource.update/set_active activity entries,
# in the order shown to the user.
_PROJECT_RESOURCE_DIFF_FIELDS: tuple[str, ...] = (
    "hourly_rate",
    "currency_code",
    "planned_hours",
    "is_active",
)


def _diff_project_resource_fields(
    before: ProjectResource,
    after: ProjectResource,
    fields: tuple[str, ...] = _PROJECT_RESOURCE_DIFF_FIELDS,
) -> dict[str, dict[str, str | None]]:
    changes: dict[str, dict[str, str | None]] = {}
    for field_name in fields:
        old_value = getattr(before, field_name, None)
        new_value = getattr(after, field_name, None)
        if old_value == new_value:
            continue
        changes[field_name] = {
            "from": None if old_value is None else str(old_value),
            "to": None if new_value is None else str(new_value),
        }
    return changes


class ProjectResourceCommandMixin:
    _project_resource_repo: ProjectResourceRepository
    _resource_repo: ResourceRepository
    _project_repo: ProjectRepository
    # Optional — only needed to enforce the envelope-shrink guard below.
    # When absent (composition didn't wire them), the guard is skipped
    # rather than raising, since not every caller composing this mixin
    # necessarily deals with task assignments.
    _task_repo: TaskRepository | None = None
    _assignment_repo: AssignmentRepository | None = None

    def _financial_currency_code(self, project_id: str) -> str | None:
        profile_repo = getattr(self, "_financial_profile_repo", None)
        if profile_repo is None:
            return None
        profile = profile_repo.get_by_project(project_id)
        if profile is None:
            raise NotFoundError(
                "Project financial profile not found.",
                code="FINANCIAL_PROFILE_NOT_FOUND",
            )
        return profile.currency_code

    def _allocated_planned_hours_total(self, project_id: str, resource_id: str) -> Decimal:
        if self._task_repo is None or self._assignment_repo is None:
            return Decimal("0")
        task_ids = [t.id for t in self._task_repo.list_by_project(project_id)]
        if not task_ids:
            return Decimal("0")
        return sum(
            (
                a.allocated_planned_hours
                for a in self._assignment_repo.list_by_tasks(task_ids)
                if a.resource_id == resource_id
            ),
            Decimal("0"),
        )

    def add_to_project(
        self,
        project_id: str,
        resource_id: str,
        hourly_rate: Decimal | int | str | None = None,
        currency_code: str | None = None,
        planned_hours: Decimal | int | str = Decimal("0"),
        is_active: bool = True,
    ) -> ProjectResource:
        require_permission(
            self._user_session,
            "project.manage",
            operation_label="add project resource",
        )
        require_project_permission(
            self._user_session,
            project_id,
            "project.manage",
            operation_label="add project resource",
        )

        resource = self._resource_repo.get(resource_id)
        if not resource:
            raise NotFoundError("Resource not found.", code="RESOURCE_NOT_FOUND")
        if not resource.is_active:
            raise BusinessRuleError(
                "Inactive resource cannot be added to a project.",
                code="RESOURCE_INACTIVE",
            )
        project = self._project_repo.get(project_id)
        if not project:
            raise NotFoundError("Project not found.", code="PROJECT_NOT_FOUND")

        existing = self._project_resource_repo.get_for_project(project_id, resource_id)
        if existing:
            raise BusinessRuleError(
                "Resource is already added to this project.",
                code="PROJECT_RESOURCE_EXISTS",
            )

        resolved_currency = resolve_pm_currency(
            tenant_context_service=getattr(self, "_tenant_context_service", None),
            operation_label="add project resource",
            explicit=currency_code,
            project_default=self._financial_currency_code(project_id),
        )

        project_resource = ProjectResource.create(
            project_id=project_id,
            resource_id=resource_id,
            hourly_rate=hourly_rate,
            currency_code=resolved_currency,
            planned_hours=planned_hours,
            is_active=is_active,
        )

        try:
            self._project_resource_repo.add(project_resource)
            self._session.commit()
            record_activity(
                self,
                action="project_resource.add",
                entity_type="project_resource",
                entity_id=project_resource.id,
                module="project_management",
                workspace_id=project_id,
                parent_entity_id=project_id,
                message=f"Assigned {resource.name} to the project",
                details={
                    "resource_name": resource.name,
                    "planned_hours": str(project_resource.planned_hours),
                    "hourly_rate": None if project_resource.hourly_rate is None else str(project_resource.hourly_rate),
                    "currency_code": project_resource.currency_code,
                    "is_active": project_resource.is_active,
                },
            )
        except Exception:
            self._session.rollback()
            raise

        domain_events.project_changed.emit(project_id)
        return project_resource

    def update(
        self,
        pr_id: str,
        hourly_rate: Decimal | int | str | None,
        currency_code: str | None,
        planned_hours: Decimal | int | str,
        is_active: bool,
    ) -> None:
        require_permission(
            self._user_session,
            "project.manage",
            operation_label="update project resource",
        )
        project_resource = self._project_resource_repo.get(pr_id)
        if not project_resource:
            raise NotFoundError("Project resource not found.", code="PROJECT_RESOURCE_NOT_FOUND")
        require_project_permission(
            self._user_session,
            project_resource.project_id,
            "project.manage",
            operation_label="update project resource",
        )

        project = self._project_repo.get(project_resource.project_id)
        if not project:
            raise NotFoundError("Project not found.", code="PROJECT_NOT_FOUND")

        new_envelope = Decimal(str(planned_hours if planned_hours not in (None, "") else 0))
        allocated_total = self._allocated_planned_hours_total(
            project_resource.project_id, project_resource.resource_id
        )
        if new_envelope < allocated_total:
            raise BusinessRuleError(
                f"Cannot reduce planned hours to {new_envelope}: "
                f"{allocated_total} hours are already allocated to tasks for this resource.",
                code="PROJECT_RESOURCE_ENVELOPE_BELOW_ALLOCATIONS",
            )

        resolved_currency = resolve_pm_currency(
            tenant_context_service=getattr(self, "_tenant_context_service", None),
            operation_label="update project resource",
            explicit=currency_code,
            project_default=self._financial_currency_code(project_resource.project_id),
        )
        before = SimpleNamespace(
            hourly_rate=project_resource.hourly_rate,
            currency_code=project_resource.currency_code,
            planned_hours=project_resource.planned_hours,
            is_active=project_resource.is_active,
        )
        project_resource.hourly_rate = hourly_rate
        project_resource.currency_code = resolved_currency
        project_resource.planned_hours = planned_hours
        project_resource.is_active = is_active
        resource = self._resource_repo.get(project_resource.resource_id)
        resource_name = resource.name if resource is not None else project_resource.resource_id

        try:
            self._project_resource_repo.update(project_resource)
            self._session.commit()
            record_activity(
                self,
                action="project_resource.update",
                entity_type="project_resource",
                entity_id=project_resource.id,
                module="project_management",
                workspace_id=project_resource.project_id,
                parent_entity_id=project_resource.project_id,
                message=f"Updated {resource_name}'s assignment",
                details={
                    "resource_name": resource_name,
                    "changes": _diff_project_resource_fields(before, project_resource),
                },
            )
        except Exception:
            self._session.rollback()
            raise

        domain_events.project_changed.emit(project_resource.project_id)

    def set_active(self, pr_id: str, is_active: bool) -> None:
        require_permission(
            self._user_session,
            "project.manage",
            operation_label="toggle project resource active",
        )
        project_resource = self._project_resource_repo.get(pr_id)
        if not project_resource:
            raise NotFoundError("Project resource not found.", code="PROJECT_RESOURCE_NOT_FOUND")
        require_project_permission(
            self._user_session,
            project_resource.project_id,
            "project.manage",
            operation_label="toggle project resource active",
        )

        before = SimpleNamespace(is_active=project_resource.is_active)
        project_resource.is_active = is_active
        try:
            self._project_resource_repo.update(project_resource)
            self._session.commit()
            resource = self._resource_repo.get(project_resource.resource_id)
            resource_name = resource.name if resource is not None else project_resource.resource_id
            record_activity(
                self,
                action="project_resource.set_active",
                entity_type="project_resource",
                entity_id=project_resource.id,
                module="project_management",
                workspace_id=project_resource.project_id,
                parent_entity_id=project_resource.project_id,
                message=(
                    f"{'Activated' if project_resource.is_active else 'Deactivated'} "
                    f"{resource_name}'s assignment"
                ),
                details={
                    "resource_name": resource_name,
                    "changes": _diff_project_resource_fields(
                        before, project_resource, fields=("is_active",)
                    ),
                },
            )
        except Exception:
            self._session.rollback()
            raise
        domain_events.project_changed.emit(project_resource.project_id)

    def delete(self, pr_id: str) -> None:
        require_permission(
            self._user_session,
            "project.manage",
            operation_label="delete project resource",
        )
        project_resource = self._project_resource_repo.get(pr_id)
        if not project_resource:
            raise NotFoundError("Project resource not found.", code="PROJECT_RESOURCE_NOT_FOUND")
        require_project_permission(
            self._user_session,
            project_resource.project_id,
            "project.manage",
            operation_label="delete project resource",
        )
        resource = self._resource_repo.get(project_resource.resource_id)
        resource_name = resource.name if resource is not None else project_resource.resource_id
        try:
            self._project_resource_repo.delete(pr_id)
            self._session.commit()
            record_activity(
                self,
                action="project_resource.delete",
                entity_type="project_resource",
                entity_id=project_resource.id,
                module="project_management",
                workspace_id=project_resource.project_id,
                parent_entity_id=project_resource.project_id,
                message=f"Removed {resource_name} from the project",
                details={"resource_name": resource_name},
            )
        except Exception:
            self._session.rollback()
            raise
        domain_events.project_changed.emit(project_resource.project_id)


__all__ = ["ProjectResourceCommandMixin"]

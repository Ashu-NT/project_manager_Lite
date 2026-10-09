from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime, timezone

from sqlalchemy.exc import IntegrityError

from src.core.modules.project_management.access.scope_permissions import (
    require_project_permission,
)
from src.core.modules.project_management.application.projects.commands.support import (
    ProjectSupportMixin,
    _diff_project_fields,
)
from src.core.modules.project_management.application.projects.project_events import (
    ProjectProfileUpdated,
    ProjectStatusChanged,
)
from src.core.modules.project_management.domain.enums import ProjectStatus
from src.core.modules.project_management.domain.projects.project import Project
from src.core.modules.project_management.domain.tasks.hierarchy import (
    select_leaf_tasks,
)
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)
from src.core.platform.common.exceptions import (
    BusinessRuleError,
    ConcurrencyError,
    NotFoundError,
)
from src.core.shared.activity import record_activity
from src.core.shared.audit import record_audit_entry


class ProjectUpdateMixin(ProjectSupportMixin):
    def update_dates_from_tasks(self, project_id: str) -> None:
        project = self._project_repo.get(project_id)
        if not project:
            raise NotFoundError("Project not found")

        tasks = select_leaf_tasks(self._task_repo.list_by_project(project_id))
        if not tasks:
            return

        start_dates = [task.start_date for task in tasks if task.start_date]
        end_dates = [task.end_date for task in tasks if task.end_date]

        if start_dates:
            project.start_date = min(start_dates)
        if end_dates:
            project.end_date = max(end_dates)

        self._project_repo.update(project)

    def update_project(
        self,
        project_id: str,
        expected_version: int | None = None,
        name: str | None = None,
        description: str | None = None,
        status: ProjectStatus | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        client_name: str | None = None,
        client_contact: str | None = None,
        organization_id: str | None = None,
        site_id: str | None = None,
        department_id: str | None = None,
        client_party_id: str | None = None,
        manager_user_id: str | None = None,
        code: str | None = None,
    ) -> Project:
        require_permission(self._user_session, "project.manage", operation_label="update project")
        project = self._project_repo.get(project_id)
        if not project:
            raise NotFoundError("Project not found.", code="PROJECT_NOT_FOUND")
        require_project_permission(
            self._user_session,
            project.id,
            "project.manage",
            operation_label="update project",
        )
        if expected_version is not None and project.version != expected_version:
            raise ConcurrencyError(
                "Project changed since you opened it. Refresh and try again.",
                code="STALE_WRITE",
            )
        original_project = project
        resolved_organization_id = (
            self._resolve_project_organization_id(
                organization_id,
                operation_label="update project",
            )
            if organization_id is not None
            else project.organization_id
        )
        if resolved_organization_id is None:
            raise BusinessRuleError(
                "Project organization is required.", code="PROJECT_ORGANIZATION_REQUIRED"
            )
        if client_party_id is not None and client_party_id != project.client_party_id:
            self._validate_client_party(client_party_id, resolved_organization_id)
        elif project.client_party_id and resolved_organization_id != project.organization_id:
            self._validate_client_party(project.client_party_id, resolved_organization_id)
        if department_id is not None and department_id != project.department_id:
            self._validate_department_reference(department_id, resolved_organization_id)
        elif project.department_id and resolved_organization_id != project.organization_id:
            self._validate_department_reference(project.department_id, resolved_organization_id)
        if manager_user_id is not None:
            self._validate_manager_user_id(manager_user_id, resolved_organization_id)
        elif project.manager_user_id and resolved_organization_id != project.organization_id:
            self._validate_manager_user_id(project.manager_user_id, resolved_organization_id)
        candidate = replace(
            project,
            name=project.name if name is None else name,
            description=project.description if description is None else description,
            status=project.status if status is None else status,
            start_date=project.start_date if start_date is None else start_date,
            end_date=project.end_date if end_date is None else end_date,
            client_name=project.client_name if client_name is None else client_name,
            client_contact=project.client_contact if client_contact is None else client_contact,
            organization_id=resolved_organization_id,
            site_id=project.site_id if site_id is None else site_id,
            department_id=project.department_id if department_id is None else department_id,
            client_party_id=project.client_party_id if client_party_id is None else client_party_id,
            manager_user_id=project.manager_user_id if manager_user_id is None else manager_user_id,
        )
        if name is not None:
            self._validate_project_name(
                candidate.name,
                organization_id=resolved_organization_id,
                exclude_id=project.id,
            )
        scope = self._require_project_scope_ids(operation_label="update project")

        try:
            with self._require_project_uow_factory().create(context=self._new_context()) as uow:
                if code is not None and code.strip():
                    candidate.code = self._resolve_project_code(
                        code,
                        candidate.name,
                        exclude_id=project.id,
                        organization_id=getattr(candidate, "organization_id", None),
                        project_repo=uow.projects,
                    )
                uow.projects.update(candidate)
                field_diff = _diff_project_fields(original_project, candidate)
                record_audit_entry(
                    uow,
                    operation="update",
                    entity_type="project",
                    entity_id=candidate.id,
                    module="project_management",
                    organization_id=scope.organization_id,
                    category="MASTER_DATA",
                    severity="low",
                    changed_fields={
                        field_name: {"before": diff["from"], "after": diff["to"]}
                        for field_name, diff in field_diff.items()
                    },
                    workspace_id=candidate.id,
                    metadata={"action": "project.update"},
                    commit=False,
                    fail_closed=True,
                )
                record_activity(
                    uow,
                    action="project.update",
                    entity_type="project",
                    entity_id=candidate.id,
                    module="project_management",
                    workspace_id=candidate.id,
                    message=f"Updated project {candidate.name}",
                    details={
                        "name": candidate.name,
                        "status": candidate.status.value,
                        "changes": field_diff,
                    },
                    commit=False,
                )
                uow.record_event(
                    ProjectProfileUpdated(
                        tenant_id=scope.tenant_id,
                        organization_id=scope.organization_id,
                        project_id=candidate.id,
                        occurred_at=datetime.now(timezone.utc),
                    )
                )
                if candidate.status != original_project.status:
                    uow.record_event(
                        ProjectStatusChanged(
                            tenant_id=scope.tenant_id,
                            organization_id=scope.organization_id,
                            project_id=candidate.id,
                            status=candidate.status,
                            occurred_at=datetime.now(timezone.utc),
                        )
                    )
                uow.commit()
        except IntegrityError as exc:
            if self._is_project_code_integrity_error(exc):
                self._raise_project_code_duplicate(candidate.code, exc)
            raise

        return candidate

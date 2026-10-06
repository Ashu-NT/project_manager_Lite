from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timezone

from src.core.modules.project_management.access.scope_permissions import (
    require_project_permission,
)
from src.core.modules.project_management.application.projects.commands.support import (
    ProjectSupportMixin,
)
from src.core.modules.project_management.application.projects.project_events import (
    ProjectStatusChanged,
)
from src.core.modules.project_management.domain.enums import ProjectStatus
from src.core.modules.project_management.domain.projects.project import Project
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)
from src.core.platform.common.exceptions import (
    ConcurrencyError,
    NotFoundError,
)
from src.core.shared.activity import record_activity
from src.core.shared.audit import record_audit_entry


class ProjectStatusMixin(ProjectSupportMixin):
    def set_status(
        self, project_id: str, status: ProjectStatus, *, expected_version: int | None = None
    ) -> Project:
        with self._require_project_uow_factory().create(context=self._new_context()) as uow:
            project = self._apply_project_status(
                uow, project_id, status, expected_version=expected_version
            )
            uow.commit()
        return project

    def bulk_set_status(self, project_ids: Sequence[str], status: ProjectStatus) -> list[Project]:
        """Same per-project work as set_status() (its own permission check,
        audit entry, activity entry, and ProjectStatusChanged event -- that's
        the audit trail's real granularity), but every selected project's
        change lands in ONE UnitOfWork/commit instead of one per project."""
        results: list[Project] = []
        with self._require_project_uow_factory().create(context=self._new_context()) as uow:
            for project_id in project_ids:
                results.append(self._apply_project_status(uow, project_id, status, expected_version=None))
            uow.commit()
        return results

    def _apply_project_status(
        self, uow, project_id: str, status: ProjectStatus, *, expected_version: int | None
    ) -> Project:
        """Mutates one project's status inside an already-open uow (no
        commit) -- the single unit of work shared by set_status() and
        bulk_set_status() above."""
        require_permission(self._user_session, "project.manage", operation_label="set project status")
        project = self._project_repo.get(project_id)
        if not project:
            raise NotFoundError("Project not found", code="PROJECT_NOT_FOUND")
        require_project_permission(
            self._user_session,
            project.id,
            "project.manage",
            operation_label="set project status",
        )
        if expected_version is not None and project.version != expected_version:
            raise ConcurrencyError(
                "Project changed since you opened it. Refresh and try again.",
                code="STALE_WRITE",
            )
        scope = self._require_project_scope_ids(operation_label="set project status")

        old_status = project.status
        project.status = status
        uow.projects.update(project)
        record_audit_entry(
            uow,
            operation="update",
            entity_type="project",
            entity_id=project.id,
            module="project_management",
            organization_id=scope.organization_id,
            category="MASTER_DATA",
            severity="low",
            changed_fields={
                "status": {"before": old_status.value, "after": project.status.value},
            },
            workspace_id=project.id,
            metadata={"action": "project.set_status"},
            commit=False,
            fail_closed=True,
        )
        record_activity(
            uow,
            action="project.set_status",
            entity_type="project",
            entity_id=project.id,
            module="project_management",
            workspace_id=project.id,
            message=(
                f"Changed project status from "
                f"{old_status.value.replace('_', ' ').title()} to "
                f"{project.status.value.replace('_', ' ').title()}"
            ),
            details={
                "status": project.status.value,
                "changes": {
                    "status": {
                        "from": old_status.value,
                        "to": project.status.value,
                    }
                },
            },
            commit=False,
        )
        uow.record_event(
            ProjectStatusChanged(
                tenant_id=scope.tenant_id,
                organization_id=scope.organization_id,
                project_id=project.id,
                status=project.status,
                occurred_at=datetime.now(timezone.utc),
            )
        )
        return project

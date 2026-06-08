from __future__ import annotations

from src.core.platform.common.exceptions import NotFoundError
from src.core.modules.project_management.domain.collaboration import (
    CollaborationMentionCandidate,
    TaskComment,
)


class CollaborationSupportMixin:
    def _list_accessible_comments(self, *, limit: int, tasks=None) -> list[TaskComment]:
        tasks = list(tasks) if tasks is not None else self._accessible_tasks_for_collaboration()
        return self._comment_repo.list_recent_for_tasks([task.id for task in tasks], limit=limit)

    def _accessible_tasks_for_collaboration(self):
        tasks, _project_name_by_id = self._accessible_task_context_for_collaboration()
        return tasks

    def _accessible_task_context_for_collaboration(self):
        tasks = []
        project_name_by_id: dict[str, str] = {}
        for project in self._collaboration_projects():
            if self._user_session is None:
                continue
            if not self._user_session.has_project_permission(project.id, "collaboration.read"):
                continue
            project_name_by_id[project.id] = project.name
            tasks.extend(self._task_repo.list_by_project(project.id))
        return tasks, project_name_by_id

    def _list_mention_candidates_for_project(self, project_id: str) -> list[CollaborationMentionCandidate]:
        candidates: list[CollaborationMentionCandidate] = []
        seen_user_ids: set[str] = set()
        for membership in self._project_membership_repo.list_by_project(project_id):
            permissions = {str(code).strip() for code in membership.permission_codes}
            if permissions.isdisjoint({"collaboration.read", "collaboration.manage"}):
                continue
            user = self._user_repo.get(membership.user_id)
            if user is None or not user.is_active:
                continue
            if user.id in seen_user_ids:
                continue
            seen_user_ids.add(user.id)
            candidates.append(
                CollaborationMentionCandidate(
                    user_id=user.id,
                    username=user.username,
                    display_name=user.display_name,
                    scope_role=membership.scope_role,
                )
            )

        principal = self._user_session.principal if self._user_session is not None else None
        principal_user_id = str(getattr(principal, "user_id", "") or "").strip()
        if principal_user_id and principal_user_id not in seen_user_ids:
            if self._user_session is not None and self._user_session.has_project_permission(project_id, "collaboration.read"):
                user = self._user_repo.get(principal_user_id)
                if user is not None and user.is_active:
                    candidates.append(
                        CollaborationMentionCandidate(
                            user_id=user.id,
                            username=user.username,
                            display_name=user.display_name,
                            scope_role="direct",
                        )
                    )

        return sorted(candidates, key=lambda item: ((item.display_name or item.username).lower(), item.username.lower()))

    def _principal_can_access_project(self, project_id: str | None) -> bool:
        if not project_id or self._user_session is None:
            return False
        return (
            self._project_in_active_organization(project_id)
            and self._user_session.has_project_permission(project_id, "collaboration.read")
        )

    def _project_name(self, project_id: str | None) -> str:
        if not project_id:
            return ""
        project = self._project_repo.get(project_id)
        if project is None or not self._project_in_active_organization(project.id):
            return ""
        return project.name if project is not None else ""

    def _collaboration_projects(self):
        organization_id = self._active_collaboration_organization_id(
            operation_label="view collaboration projects"
        )
        if organization_id and hasattr(self._project_repo, "list_for_organization"):
            return self._project_repo.list_for_organization(organization_id)
        return self._project_repo.list_all()

    def _active_collaboration_organization_id(self, *, operation_label: str) -> str | None:
        tenant_context = getattr(self, "_tenant_context_service", None)
        if tenant_context is None:
            return None
        return tenant_context.require_active_organization_id(operation_label=operation_label)

    def _project_in_active_organization(self, project_id: str) -> bool:
        organization_id = self._active_collaboration_organization_id(
            operation_label="view collaboration project"
        )
        if not organization_id:
            return True
        project = self._project_repo.get(project_id)
        return bool(project is not None and getattr(project, "organization_id", None) == organization_id)

    def _recent_audit_rows_for_collaboration(self, *, limit: int):
        organization_id = self._active_collaboration_organization_id(
            operation_label="view collaboration notifications"
        )
        if organization_id and hasattr(self._audit_repo, "list_recent_for_organization"):
            return self._audit_repo.list_recent_for_organization(organization_id, limit=limit)
        return self._audit_repo.list_recent(limit=limit)

    def _project_names_label(self, project_ids: list[str]) -> str:
        names = [project_name for project_id in project_ids if (project_name := self._project_name(project_id))]
        if len(names) == 1:
            return names[0]
        if names:
            return ", ".join(names[:2]) + ("..." if len(names) > 2 else "")
        return ""

    @staticmethod
    def _workflow_preview_from_details(details: dict) -> str:
        parts: list[str] = []
        for key in ("project_name", "decision_note", "resource_name", "status"):
            value = str(details.get(key) or "").strip()
            if not value:
                continue
            label = key.replace("_", " ").title()
            parts.append(f"{label}: {value}")
        return "; ".join(parts)

    @staticmethod
    def _audit_project_ids(row) -> list[str]:
        details = row.details or {}
        if row.project_id:
            return [row.project_id]
        raw = details.get("project_ids")
        if isinstance(raw, list):
            return [str(item).strip() for item in raw if str(item).strip()]
        project_id = str(details.get("project_id") or "").strip()
        return [project_id] if project_id else []

    def _require_task(self, task_id: str):
        task = self._task_repo.get(task_id)
        if task is None:
            raise NotFoundError("Task not found.", code="TASK_NOT_FOUND")
        return task

    @staticmethod
    def _body_preview(body: str) -> str:
        text = " ".join((body or "").split())
        return text if len(text) <= 120 else f"{text[:117]}..."


__all__ = ["CollaborationSupportMixin"]

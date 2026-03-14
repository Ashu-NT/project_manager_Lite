from __future__ import annotations

from core.platform.common.exceptions import NotFoundError
from core.platform.common.models import CollaborationMentionCandidate, TaskComment


class CollaborationSupportMixin:
    def _list_accessible_comments(self, *, limit: int) -> list[TaskComment]:
        tasks = self._accessible_tasks_for_collaboration()
        return self._comment_repo.list_recent_for_tasks([task.id for task in tasks], limit=limit)

    def _accessible_tasks_for_collaboration(self):
        tasks = []
        for project in self._project_repo.list_all():
            if self._user_session is None:
                continue
            if not self._user_session.has_project_permission(project.id, "collaboration.read"):
                continue
            tasks.extend(self._task_repo.list_by_project(project.id))
        return tasks

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

    def _comment_mentions_principal(self, comment: TaskComment) -> bool:
        principal = self._user_session.principal if self._user_session is not None else None
        principal_user_id = str(getattr(principal, "user_id", "") or "").strip()
        mentioned_user_ids = {str(item).strip() for item in comment.mentioned_user_ids if str(item).strip()}
        if principal_user_id and principal_user_id in mentioned_user_ids:
            return True
        mentions = {item.lower() for item in comment.mentions}
        aliases = self._principal_aliases()
        return bool(aliases and not mentions.isdisjoint(aliases))

    def _principal_can_access_project(self, project_id: str | None) -> bool:
        if not project_id or self._user_session is None:
            return False
        return self._user_session.has_project_permission(project_id, "collaboration.read")

    def _project_name(self, project_id: str | None) -> str:
        if not project_id:
            return ""
        project = self._project_repo.get(project_id)
        return project.name if project is not None else ""

    def _project_names_label(self, project_ids: list[str]) -> str:
        names = [self._project_name(project_id) for project_id in project_ids if self._project_name(project_id)]
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

    def _comment_is_unread_for_principal(self, comment: TaskComment) -> bool:
        if not self._comment_mentions_principal(comment):
            return False
        principal = self._user_session.principal if self._user_session is not None else None
        principal_user_id = str(getattr(principal, "user_id", "") or "").strip()
        if principal_user_id:
            read_by_user_ids = {str(item).strip() for item in comment.read_by_user_ids if str(item).strip()}
            if principal_user_id in read_by_user_ids:
                return False
        aliases = self._principal_aliases()
        read_by = {item.lower() for item in comment.read_by}
        return read_by.isdisjoint(aliases)

    def _require_task(self, task_id: str):
        task = self._task_repo.get(task_id)
        if task is None:
            raise NotFoundError("Task not found.", code="TASK_NOT_FOUND")
        return task

    def _principal_aliases(self) -> set[str]:
        principal = self._user_session.principal if self._user_session is not None else None
        if principal is None:
            return set()
        aliases: set[str] = set()
        if principal.username:
            aliases.add(principal.username.strip().lower())
        display_name = (principal.display_name or "").strip().lower()
        if display_name:
            aliases.add(display_name.strip(" @"))
            aliases.add(display_name.replace(" ", "").strip(" @"))
            aliases.add(display_name.replace(" ", ".").strip(" @"))
        return {alias for alias in aliases if alias}

    def _principal_primary_alias(self) -> str:
        principal = self._user_session.principal if self._user_session is not None else None
        if principal is None or not getattr(principal, "username", None):
            return ""
        return str(principal.username).strip().lower()

    @staticmethod
    def _body_preview(body: str) -> str:
        text = " ".join((body or "").split())
        return text if len(text) <= 120 else f"{text[:117]}..."


__all__ = ["CollaborationSupportMixin"]

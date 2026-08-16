from __future__ import annotations

from src.core.modules.project_management.access.scope_permissions import filter_project_rows
from src.core.modules.project_management.domain.collaboration import CollaborationMentionCandidate
from src.core.platform.common.exceptions import BusinessRuleError, NotFoundError


class CollaborationSupportMixin:
    def _collaboration_scope(self, *, operation_label: str):
        tenant_context = getattr(self, "_tenant_context_service", None)
        if tenant_context is None:
            raise BusinessRuleError(
                "Active tenant context is required to view collaboration workspace.",
                code="TENANT_CONTEXT_REQUIRED",
            )
        scope = tenant_context.require_active_scope_ids(operation_label=operation_label)
        projects = filter_project_rows(
            self._project_repo.list(),
            self._user_session,
            permission_code="collaboration.read",
            project_id_getter=lambda project: project.id,
        )
        return scope, {project.id: project.name for project in projects}

    def _list_mention_candidates_for_project(self, project_id: str) -> list[CollaborationMentionCandidate]:
        candidates: list[CollaborationMentionCandidate] = []
        seen_user_ids: set[str] = set()
        tenant_id = (
            self._tenant_context_service.get_active_tenant_id()
            if (
                self._role_repo is not None
                and self._role_binding_repo is not None
                and self._tenant_context_service is not None
            )
            else None
        )
        membership_rows = (
            list(self._canonical_project_membership_rows(project_id, tenant_id=tenant_id))
            if tenant_id is not None
            else []
        )
        for user_id, scope_role, permission_codes in membership_rows:
            permissions = {str(code).strip() for code in permission_codes}
            if permissions.isdisjoint({"collaboration.read", "collaboration.manage"}):
                continue
            user = self._user_repo.get(user_id)
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
                    scope_role=scope_role,
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

    def _canonical_project_membership_rows(self, project_id: str, *, tenant_id: str):
        for role_name in ("project_viewer", "project_contributor", "project_lead", "project_owner"):
            role = self._role_repo.get_by_name(role_name)
            if role is None:
                continue
            for binding in self._role_binding_repo.list_active_for_role(role.id, tenant_id=tenant_id):
                if binding.actual_scope_type == "project" and binding.actual_scope_id == project_id:
                    yield (
                        binding.principal_id,
                        role_name.removeprefix("project_"),
                        ("collaboration.read",),
                    )

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

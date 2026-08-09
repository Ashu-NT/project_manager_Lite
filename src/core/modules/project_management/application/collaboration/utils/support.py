from __future__ import annotations

from datetime import datetime, timedelta, timezone

from src.core.modules.project_management.access.scope_permissions import filter_project_rows
from src.core.modules.project_management.domain.collaboration import CollaborationMentionCandidate
from src.core.platform.common.exceptions import BusinessRuleError, NotFoundError


class CollaborationSupportMixin:
    def _read_cross_project_collaboration_facts(
        self,
        *,
        comment_limit: int,
        presence_limit: int = 0,
    ):
        tenant_context = getattr(self, "_tenant_context_service", None)
        if tenant_context is None:
            raise BusinessRuleError(
                "Active tenant context is required to view collaboration workspace.",
                code="TENANT_CONTEXT_REQUIRED",
            )
        scope = tenant_context.require_active_scope_ids(
            operation_label="view collaboration workspace"
        )
        projects = filter_project_rows(
            self._project_repo.list(),
            self._user_session,
            permission_code="collaboration.read",
            project_id_getter=lambda project: project.id,
        )
        project_names = {project.id: project.name for project in projects}
        facts = self._workspace_reader.read_facts(
            tenant_id=scope.tenant_id,
            organization_id=scope.organization_id,
            accessible_project_ids=tuple(project_names),
            comment_limit=max(0, int(comment_limit)),
            presence_since=(
                datetime.now(timezone.utc) - timedelta(seconds=self._presence_ttl_seconds)
                if presence_limit > 0
                else None
            ),
            presence_limit=max(0, int(presence_limit)),
        )
        return facts, project_names

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

    def _active_collaboration_organization_id(self, *, operation_label: str) -> str | None:
        tenant_context = getattr(self, "_tenant_context_service", None)
        if tenant_context is None:
            raise BusinessRuleError(
                f"Active organization context is required for {operation_label}.",
                code="TENANT_CONTEXT_REQUIRED",
            )
        return tenant_context.require_active_organization_id(operation_label=operation_label)

    def _recent_audit_rows_for_collaboration(self, *, limit: int):
        organization_id = self._active_collaboration_organization_id(
            operation_label="view collaboration notifications"
        )
        if organization_id and hasattr(self._audit_repo, "list_recent_for_organization"):
            return self._audit_repo.list_recent_for_organization(organization_id, limit=limit)
        return self._audit_repo.list_recent(limit=limit)

    @staticmethod
    def _project_names_label(
        project_ids: list[str],
        project_name_by_id: dict[str, str],
    ) -> str:
        names = [project_name_by_id[project_id] for project_id in project_ids if project_id in project_name_by_id]
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
        details = getattr(row, "details", None) or getattr(row, "metadata", None) or {}
        row_project_id = str(getattr(row, "project_id", None) or getattr(row, "entity_parent_id", None) or details.get("project_id") or "").strip()
        if row_project_id:
            return [row_project_id]
        raw = details.get("project_ids")
        if isinstance(raw, list):
            return [str(item).strip() for item in raw if str(item).strip()]
        return []

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

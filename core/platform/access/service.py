from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from core.platform.notifications.domain_events import domain_events
from core.platform.common.exceptions import NotFoundError, ValidationError
from core.platform.common.interfaces import ProjectMembershipRepository, ProjectRepository, UserRepository
from core.platform.common.models import ProjectMembership
from core.platform.access.policy import normalize_project_scope_role, resolve_project_scope_permissions
from core.platform.audit.helpers import record_audit
from core.platform.auth.authorization import require_permission

if TYPE_CHECKING:
    from core.platform.auth.service import AuthService
    from core.platform.auth.session import UserSessionContext
    from core.platform.audit.service import AuditService


class AccessControlService:
    def __init__(
        self,
        *,
        session: Session,
        membership_repo: ProjectMembershipRepository,
        project_repo: ProjectRepository,
        user_repo: UserRepository,
        auth_service: "AuthService",
        user_session: "UserSessionContext | None" = None,
        audit_service: "AuditService | None" = None,
    ) -> None:
        self._session = session
        self._membership_repo = membership_repo
        self._project_repo = project_repo
        self._user_repo = user_repo
        self._auth_service = auth_service
        self._user_session = user_session
        self._audit_service = audit_service

    def list_project_memberships(self, project_id: str) -> list[ProjectMembership]:
        require_permission(self._user_session, "access.manage", operation_label="list project memberships")
        return self._membership_repo.list_by_project(project_id)

    def list_user_memberships(self, user_id: str) -> list[ProjectMembership]:
        require_permission(self._user_session, "access.manage", operation_label="list user memberships")
        return self._membership_repo.list_by_user(user_id)

    def assign_project_membership(
        self,
        *,
        project_id: str,
        user_id: str,
        scope_role: str,
    ) -> ProjectMembership:
        require_permission(self._user_session, "access.manage", operation_label="assign project membership")
        project = self._project_repo.get(project_id)
        if project is None:
            raise NotFoundError("Project not found.", code="PROJECT_NOT_FOUND")
        user = self._user_repo.get(user_id)
        if user is None:
            raise NotFoundError("User not found.", code="USER_NOT_FOUND")
        role_name = normalize_project_scope_role(scope_role)
        permissions = sorted(resolve_project_scope_permissions(role_name))
        if not permissions:
            raise ValidationError("Project membership role must resolve to at least one permission.")

        membership = self._membership_repo.get_for_project_user(project_id, user_id)
        if membership is None:
            membership = ProjectMembership.create(
                project_id=project_id,
                user_id=user_id,
                scope_role=role_name,
                permission_codes=permissions,
            )
            self._membership_repo.add(membership)
        else:
            membership.scope_role = role_name
            membership.permission_codes = permissions
            self._membership_repo.update(membership)
        self._session.commit()
        record_audit(
            self,
            action="access.membership.upsert",
            entity_type="project_membership",
            entity_id=membership.id,
            project_id=project_id,
            details={
                "username": user.username,
                "scope_role": membership.scope_role,
            },
        )
        domain_events.access_changed.emit(project_id)
        self._refresh_current_session_if_needed(user_id)
        return membership

    def remove_project_membership(self, *, project_id: str, user_id: str) -> None:
        require_permission(self._user_session, "access.manage", operation_label="remove project membership")
        membership = self._membership_repo.get_for_project_user(project_id, user_id)
        if membership is None:
            raise NotFoundError("Project membership not found.", code="PROJECT_MEMBERSHIP_NOT_FOUND")
        user = self._user_repo.get(user_id)
        self._membership_repo.delete(membership.id)
        self._session.commit()
        record_audit(
            self,
            action="access.membership.remove",
            entity_type="project_membership",
            entity_id=membership.id,
            project_id=project_id,
            details={
                "username": user.username if user is not None else user_id,
                "scope_role": membership.scope_role,
            },
        )
        domain_events.access_changed.emit(project_id)
        self._refresh_current_session_if_needed(user_id)

    def _refresh_current_session_if_needed(self, user_id: str) -> None:
        principal = self._user_session.principal if self._user_session is not None else None
        if principal is None or principal.user_id != user_id:
            return
        user = self._user_repo.get(user_id)
        if user is None:
            self._user_session.clear()
            return
        self._user_session.set_principal(self._auth_service.build_principal(user))


__all__ = ["AccessControlService"]

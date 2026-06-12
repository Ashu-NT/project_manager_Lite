from __future__ import annotations

from typing import TYPE_CHECKING

from src.core.shared.events.domain_events import domain_events
from src.core.platform.auth.authorization import require_permission
from src.core.platform.auth.domain import UserRoleBinding

from .session_service import refresh_current_session_if_user
from .sod_enforcer import enforce_separation_of_duties

if TYPE_CHECKING:
    from .auth_service import AuthService


def assign_role(service: AuthService, user_id: str, role_name: str) -> None:
    require_permission(service._user_session, "auth.manage", operation_label="assign role")
    user = service._require_user(user_id)
    existing_role_names = service.get_user_role_names(user.id)
    enforce_separation_of_duties(service, tuple(existing_role_names) + (role_name,))
    role = service._require_role_by_name(role_name)
    if not service._user_role_repo.exists(user.id, role.id):
        service._user_role_repo.add(UserRoleBinding.create(user_id=user.id, role_id=role.id))
        service._session.commit()
        domain_events.auth_changed.emit(user.id)
    refresh_current_session_if_user(service, user.id)


def revoke_role(service: AuthService, user_id: str, role_name: str) -> None:
    require_permission(service._user_session, "auth.manage", operation_label="revoke role")
    user = service._require_user(user_id)
    role = service._require_role_by_name(role_name)
    service._user_role_repo.delete(user.id, role.id)
    service._session.commit()
    domain_events.auth_changed.emit(user.id)
    refresh_current_session_if_user(service, user.id)


__all__ = ["assign_role", "revoke_role"]

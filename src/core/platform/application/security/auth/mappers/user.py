from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

from src.core.platform.application.security.auth.dto.responses.user import (
    RoleDto,
    UserDto,
)
from src.core.platform.domain.security.auth import (
    Role,
    UserAccount,
)


def serialize_role(role: Role) -> RoleDto:
    return RoleDto(
        id=role.id,
        name=role.name,
        description=role.description,
        is_system=role.is_system,
    )


def serialize_user(user: UserAccount, *, role_names: tuple[str, ...]) -> UserDto:
    return UserDto(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        email=user.email,
        identity_provider=user.identity_provider,
        federated_subject=user.federated_subject,
        is_active=user.is_active,
        failed_login_attempts=int(user.failed_login_attempts or 0),
        locked_until=user.locked_until,
        last_login_at=user.last_login_at,
        last_login_auth_method=user.last_login_auth_method,
        last_login_device_label=user.last_login_device_label,
        session_expires_at=user.session_expires_at,
        session_timeout_minutes_override=user.session_timeout_minutes_override,
        must_change_password=user.must_change_password,
        version=user.version,
        role_names=role_names,
        account_type=getattr(user, "account_type", "human"),
    )

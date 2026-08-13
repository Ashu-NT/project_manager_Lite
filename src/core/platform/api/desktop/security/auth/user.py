from __future__ import annotations

from src.core.platform.api.desktop.support._support import execute_desktop_operation
from src.core.platform.api.desktop.models.common import DesktopApiResult
from src.core.platform.api.desktop.security.auth.models.user import (
    RoleDto,
    UserCreateCommand,
    UserDto,
    UserPasswordResetCommand,
    UserUpdateCommand,
)
from src.core.platform.application.security.auth import AuthService
from src.core.platform.domain.security.auth import (
    Role,
    UserAccount,
)


class PlatformUserDesktopApi:
    """Desktop-facing adapter for platform user administration flows."""

    def __init__(self, *, auth_service: AuthService) -> None:
        self._auth_service = auth_service

    def list_users(self) -> DesktopApiResult[tuple[UserDto, ...]]:
        return execute_desktop_operation(
            lambda: tuple(
                self._serialize_user(user)
                for user in self._auth_service.list_users()
            )
        )

    def list_roles(self) -> DesktopApiResult[tuple[RoleDto, ...]]:
        return execute_desktop_operation(
            lambda: tuple(
                self._serialize_role(role)
                for role in self._auth_service.list_customer_assignable_roles()
            )
        )

    def create_user(self, command: UserCreateCommand) -> DesktopApiResult[UserDto]:
        return execute_desktop_operation(
            lambda: self._serialize_user(
                self._auth_service.onboard_tenant_user(
                    username=command.username,
                    raw_password=command.password,
                    display_name=command.display_name,
                    email=command.email,
                    is_active=command.is_active,
                )
            )
        )

    def update_user(self, command: UserUpdateCommand) -> DesktopApiResult[UserDto]:
        return execute_desktop_operation(
            lambda: self._serialize_user(
                self._auth_service.update_user_profile(
                    command.user_id,
                    username=command.username,
                    display_name=command.display_name,
                    email=command.email,
                )
            )
        )

    def assign_role(self, user_id: str, role_name: str) -> DesktopApiResult[UserDto]:
        return execute_desktop_operation(
            lambda: self._assign_role_and_get_user(user_id=user_id, role_name=role_name)
        )

    def revoke_role(self, user_id: str, role_name: str) -> DesktopApiResult[UserDto]:
        return execute_desktop_operation(
            lambda: self._revoke_role_and_get_user(user_id=user_id, role_name=role_name)
        )

    def set_user_active(self, user_id: str, is_active: bool) -> DesktopApiResult[UserDto]:
        return execute_desktop_operation(
            lambda: self._serialize_user(
                self._auth_service.set_user_active(user_id, is_active)
            )
        )

    def reset_password(self, command: UserPasswordResetCommand) -> DesktopApiResult[UserDto]:
        return execute_desktop_operation(
            lambda: self._reset_password_and_get_user(command)
        )

    def unlock_user_account(self, user_id: str) -> DesktopApiResult[UserDto]:
        return execute_desktop_operation(
            lambda: self._serialize_user(
                self._auth_service.unlock_user_account(user_id)
            )
        )

    def force_user_password_reset(self, user_id: str) -> DesktopApiResult[None]:
        return execute_desktop_operation(
            lambda: self._auth_service.force_user_password_reset(user_id)
        )

    def revoke_user_sessions(
        self,
        user_id: str,
        *,
        note: str = "",
    ) -> DesktopApiResult[UserDto]:
        return execute_desktop_operation(
            lambda: self._serialize_user(
                self._auth_service.revoke_user_sessions(user_id, note=note)
            )
        )

    @staticmethod
    def _serialize_role(role: Role) -> RoleDto:
        return RoleDto(
            id=role.id,
            name=role.name,
            description=role.description,
            is_system=role.is_system,
        )

    def _serialize_user(self, user: UserAccount) -> UserDto:
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
            role_names=tuple(sorted(self._auth_service.get_user_role_names(user.id))),
            account_type=getattr(user, "account_type", "human"),
        )

    def _assign_role_and_get_user(self, *, user_id: str, role_name: str) -> UserDto:
        return self._serialize_user(
            self._auth_service.assign_customer_role(user_id, role_name)
        )

    def _revoke_role_and_get_user(self, *, user_id: str, role_name: str) -> UserDto:
        return self._serialize_user(
            self._auth_service.revoke_customer_role(user_id, role_name)
        )

    def _reset_password_and_get_user(self, command: UserPasswordResetCommand) -> UserDto:
        return self._serialize_user(
            self._auth_service.reset_user_password(command.user_id, command.new_password)
        )


__all__ = ["PlatformUserDesktopApi"]

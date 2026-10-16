from __future__ import annotations

from src.core.platform.api.desktop.models.common import DesktopApiResult
from src.core.platform.api.desktop.support._support import execute_desktop_operation
from src.core.platform.application.security.auth import (
    AuthQueryHandler,
    AuthSessionCommandHandler,
    PasswordCommandHandler,
    UserAdministrationCommandHandler,
    UserDirectoryQueryHandler,
    UserRegistrationHandler,
)
from src.core.platform.application.security.auth.dto.commands.users import (
    UserCreateCommand,
    UserPasswordResetCommand,
    UserUpdateCommand,
)
from src.core.platform.application.security.auth.dto.responses.user import (
    RoleDto,
    UserDto,
)
from src.core.platform.application.security.authorization.roles.commands import (
    RoleAssignmentHandler,
)
from src.core.platform.contract.read.overview.platform_overview_rollup_reader import (
    UserRollupSummary,
)


class PlatformUserDesktopApi:
    """Desktop-facing adapter for platform user administration flows."""

    def __init__(
        self,
        *,
        auth_queries: AuthQueryHandler,
        user_directory: UserDirectoryQueryHandler,
        registration: UserRegistrationHandler,
        user_administration: UserAdministrationCommandHandler,
        passwords: PasswordCommandHandler,
        session_commands: AuthSessionCommandHandler,
        role_assignment: RoleAssignmentHandler,
    ) -> None:
        self._auth_queries = auth_queries
        self._user_directory = user_directory
        self._registration = registration
        self._user_administration = user_administration
        self._passwords = passwords
        self._session_commands = session_commands
        self._role_assignment = role_assignment

    def list_users(self) -> DesktopApiResult[tuple[UserDto, ...]]:
        return execute_desktop_operation(
            lambda: tuple(
                user
                for user in self._user_directory.list_users()
            )
        )

    def get_user_rollup_summary(self) -> DesktopApiResult[UserRollupSummary]:
        return execute_desktop_operation(
            lambda: self._user_directory.get_user_rollup_summary()
        )

    def list_roles(self) -> DesktopApiResult[tuple[RoleDto, ...]]:
        return execute_desktop_operation(
            lambda: tuple(
                role
                for role in self._user_directory.list_customer_assignable_roles()
            )
        )

    def create_user(self, command: UserCreateCommand) -> DesktopApiResult[UserDto]:
        return execute_desktop_operation(
            lambda: self._registration.onboard_tenant_user(command)
        )

    def update_user(self, command: UserUpdateCommand) -> DesktopApiResult[UserDto]:
        return execute_desktop_operation(
            lambda: self._user_administration.update_user_profile(command)
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
            lambda: self._user_administration.set_user_active(user_id, is_active)
        )

    def reset_password(self, command: UserPasswordResetCommand) -> DesktopApiResult[UserDto]:
        return execute_desktop_operation(
            lambda: self._reset_password_and_get_user(command)
        )

    def unlock_user_account(self, user_id: str) -> DesktopApiResult[UserDto]:
        return execute_desktop_operation(
            lambda: self._user_administration.unlock_user_account(user_id)
        )

    def force_user_password_reset(self, user_id: str) -> DesktopApiResult[None]:
        return execute_desktop_operation(
            lambda: self._passwords.force_user_password_reset(user_id)
        )

    def revoke_user_sessions(
        self,
        user_id: str,
        *,
        note: str = "",
    ) -> DesktopApiResult[UserDto]:
        return execute_desktop_operation(
            lambda: self._session_commands.revoke_user_sessions(user_id, note=note)
        )




    def _assign_role_and_get_user(self, *, user_id: str, role_name: str) -> UserDto:
        return self._role_assignment.assign_customer_role(user_id, role_name)

    def _revoke_role_and_get_user(self, *, user_id: str, role_name: str) -> UserDto:
        return self._role_assignment.revoke_customer_role(user_id, role_name)

    def _reset_password_and_get_user(self, command: UserPasswordResetCommand) -> UserDto:
        return self._passwords.reset_user_password(command)


__all__ = ["PlatformUserDesktopApi"]

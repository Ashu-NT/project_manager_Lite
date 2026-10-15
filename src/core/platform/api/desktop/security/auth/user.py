from __future__ import annotations

from src.core.platform.api.desktop.models.common import DesktopApiResult
from src.core.platform.api.desktop.security.auth.models.user import (
    RoleDto,
    UserDto,
    UserRollupSummaryDto,
)
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
from src.core.platform.application.security.authorization.roles.commands import (
    RoleAssignmentHandler,
)
from src.core.platform.domain.security.auth import (
    Role,
    UserAccount,
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
                self._serialize_user(user)
                for user in self._user_directory.list_users()
            )
        )

    def get_user_rollup_summary(self) -> DesktopApiResult[UserRollupSummaryDto]:
        return execute_desktop_operation(
            lambda: self._serialize_user_rollup_summary(
                self._user_directory.get_user_rollup_summary()
            )
        )

    def list_roles(self) -> DesktopApiResult[tuple[RoleDto, ...]]:
        return execute_desktop_operation(
            lambda: tuple(
                self._serialize_role(role)
                for role in self._user_directory.list_customer_assignable_roles()
            )
        )

    def create_user(self, command: UserCreateCommand) -> DesktopApiResult[UserDto]:
        return execute_desktop_operation(
            lambda: self._serialize_user(
                self._registration.onboard_tenant_user(command)
            )
        )

    def update_user(self, command: UserUpdateCommand) -> DesktopApiResult[UserDto]:
        return execute_desktop_operation(
            lambda: self._serialize_user(
                self._user_administration.update_user_profile(command)
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
                self._user_administration.set_user_active(user_id, is_active)
            )
        )

    def reset_password(self, command: UserPasswordResetCommand) -> DesktopApiResult[UserDto]:
        return execute_desktop_operation(
            lambda: self._reset_password_and_get_user(command)
        )

    def unlock_user_account(self, user_id: str) -> DesktopApiResult[UserDto]:
        return execute_desktop_operation(
            lambda: self._serialize_user(
                self._user_administration.unlock_user_account(user_id)
            )
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
            lambda: self._serialize_user(
                self._session_commands.revoke_user_sessions(user_id, note=note)
            )
        )

    @staticmethod
    def _serialize_user_rollup_summary(summary) -> UserRollupSummaryDto:
        return UserRollupSummaryDto(total=summary.total, active=summary.active, locked=summary.locked)

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
            role_names=tuple(sorted(self._auth_queries.get_user_role_names(user.id))),
            account_type=getattr(user, "account_type", "human"),
        )

    def _assign_role_and_get_user(self, *, user_id: str, role_name: str) -> UserDto:
        return self._serialize_user(
            self._role_assignment.assign_customer_role(user_id, role_name)
        )

    def _revoke_role_and_get_user(self, *, user_id: str, role_name: str) -> UserDto:
        return self._serialize_user(
            self._role_assignment.revoke_customer_role(user_id, role_name)
        )

    def _reset_password_and_get_user(self, command: UserPasswordResetCommand) -> UserDto:
        return self._serialize_user(
            self._passwords.reset_user_password(command)
        )


__all__ = ["PlatformUserDesktopApi"]

from __future__ import annotations

from typing import Any

from src.api.desktop.platform import (
    PlatformUserDesktopApi,
    RoleDto,
    UserCreateCommand,
    UserDto,
    UserPasswordResetCommand,
    UserUpdateCommand,
)
from src.api.desktop.platform.models import DesktopApiResult
from src.ui_qml.platform.presenters.support import (
    bool_value,
    option_item,
    optional_string_value,
    preview_error_result,
    string_value,
)
from src.ui_qml.platform.view_models import (
    PlatformWorkspaceActionItemViewModel,
    PlatformWorkspaceActionListViewModel,
)


class PlatformUserCatalogPresenter:
    def __init__(self, *, user_api: PlatformUserDesktopApi | None = None) -> None:
        self._user_api = user_api

    def build_catalog(self) -> PlatformWorkspaceActionListViewModel:
        if self._user_api is None:
            return PlatformWorkspaceActionListViewModel(
                title="Users",
                subtitle="Identity records appear here once the platform user API is connected.",
                empty_state="Platform user API is not connected in this QML preview.",
            )

        users_result = self._user_api.list_users()
        if not users_result.ok or users_result.data is None:
            message = users_result.error.message if users_result.error is not None else "Unable to load users."
            return PlatformWorkspaceActionListViewModel(
                title="Users",
                subtitle=message,
                empty_state=message,
            )

        users = tuple(users_result.data)
        active_count = sum(1 for row in users if row.is_active)
        locked_count = sum(1 for row in users if row.locked_until is not None)
        return PlatformWorkspaceActionListViewModel(
            title="Users",
            subtitle=f"Identity accounts and role posture. {active_count} active, {locked_count} locked.",
            empty_state="No users are available yet.",
            items=tuple(self._serialize_user(row) for row in users),
        )

    def build_role_options(self) -> tuple[dict[str, str], ...]:
        if self._user_api is None:
            return ()
        result = self._user_api.list_roles()
        if not result.ok or result.data is None:
            return ()
        return tuple(self._serialize_role_option(row) for row in result.data)

    def create_user(self, payload: dict[str, Any]) -> DesktopApiResult[UserDto]:
        if self._user_api is None:
            return preview_error_result("Platform user API is not connected in this QML preview.")
        return self._user_api.create_user(
            UserCreateCommand(
                username=string_value(payload, "username"),
                password=string_value(payload, "password"),
                display_name=optional_string_value(payload, "displayName"),
                email=optional_string_value(payload, "email"),
                is_active=bool_value(payload, "isActive", default=True),
                role_names=tuple(self._selected_role_names(payload)),
            )
        )

    def update_user(self, payload: dict[str, Any]) -> DesktopApiResult[UserDto]:
        if self._user_api is None:
            return preview_error_result("Platform user API is not connected in this QML preview.")

        user_id = string_value(payload, "userId")
        result = self._user_api.update_user(
            UserUpdateCommand(
                user_id=user_id,
                username=string_value(payload, "username"),
                display_name=optional_string_value(payload, "displayName"),
                email=optional_string_value(payload, "email"),
            )
        )
        if not result.ok:
            return result

        current_roles = set(self._current_role_names(payload))
        desired_roles = set(self._selected_role_names(payload))
        for role_name in sorted(desired_roles - current_roles):
            result = self._user_api.assign_role(user_id, role_name)
            if not result.ok:
                return result
        for role_name in sorted(current_roles - desired_roles):
            result = self._user_api.revoke_role(user_id, role_name)
            if not result.ok:
                return result

        current_is_active = bool_value(
            payload,
            "currentIsActive",
            default=bool_value(payload, "isActive", default=True),
        )
        desired_is_active = bool_value(payload, "isActive", default=current_is_active)
        if desired_is_active != current_is_active:
            result = self._user_api.set_user_active(user_id, desired_is_active)
            if not result.ok:
                return result

        password = string_value(payload, "password")
        if password:
            result = self._user_api.reset_password(
                UserPasswordResetCommand(
                    user_id=user_id,
                    new_password=password,
                )
            )
        return result

    def toggle_user_active(
        self,
        *,
        user_id: str,
        is_active: bool,
    ) -> DesktopApiResult[UserDto]:
        if self._user_api is None:
            return preview_error_result("Platform user API is not connected in this QML preview.")
        return self._user_api.set_user_active(user_id, not is_active)

    @staticmethod
    def _serialize_role_option(role: RoleDto) -> dict[str, str]:
        return option_item(
            label=role.name.replace("_", " ").title(),
            value=role.name,
            supporting_text=role.description,
        )

    @staticmethod
    def _serialize_user(row: UserDto) -> PlatformWorkspaceActionItemViewModel:
        status_label = "Locked" if row.locked_until is not None else ("Active" if row.is_active else "Inactive")
        subtitle_parts = [row.username]
        if row.email:
            subtitle_parts.append(row.email)
        supporting_text = ", ".join(role.replace("_", " ").title() for role in row.role_names) or "No roles assigned"
        posture_parts = []
        posture_parts.append("Must change password" if row.must_change_password else "Password normal")
        if row.failed_login_attempts:
            posture_parts.append(f"{row.failed_login_attempts} failed attempts")
        if row.locked_until is not None:
            posture_parts.append("Account locked")
        return PlatformWorkspaceActionItemViewModel(
            id=row.id,
            title=row.display_name or row.username,
            status_label=status_label,
            subtitle=" | ".join(subtitle_parts),
            supporting_text=supporting_text,
            meta_text=" | ".join(posture_parts),
            can_primary_action=True,
            can_secondary_action=True,
            state={
                "id": row.id,
                "userId": row.id,
                "username": row.username,
                "displayName": row.display_name or "",
                "email": row.email or "",
                "roleNames": list(row.role_names),
                "currentRoleNames": list(row.role_names),
                "isActive": row.is_active,
                "currentIsActive": row.is_active,
            },
        )

    @staticmethod
    def _selected_role_names(payload: dict[str, Any]) -> tuple[str, ...]:
        value = payload.get("roleNames")
        if not isinstance(value, (list, tuple)):
            return ()
        return tuple(
            role_name
            for item in value
            if (role_name := str(item).strip())
        )

    @staticmethod
    def _current_role_names(payload: dict[str, Any]) -> tuple[str, ...]:
        value = payload.get("currentRoleNames")
        if not isinstance(value, (list, tuple)):
            return ()
        return tuple(
            role_name
            for item in value
            if (role_name := str(item).strip())
        )


__all__ = ["PlatformUserCatalogPresenter"]

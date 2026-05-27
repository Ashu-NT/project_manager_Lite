from __future__ import annotations

from datetime import datetime

from src.api.desktop.platform import (
    DesktopApiError,
    DesktopApiResult,
    PlatformAccessDesktopApi,
    PlatformUserDesktopApi,
    ScopedAccessGrantAssignCommand,
    ScopedAccessGrantRemoveCommand,
    UserDto,
)
from src.ui_qml.platform.presenters.support import preview_error_result
from src.ui_qml.platform.view_models import (
    PlatformWorkspaceActionItemViewModel,
    PlatformWorkspaceActionListViewModel,
)


class PlatformAccessWorkspacePresenter:
    def __init__(
        self,
        *,
        access_api: PlatformAccessDesktopApi | None = None,
        user_api: PlatformUserDesktopApi | None = None,
    ) -> None:
        self._access_api = access_api
        self._user_api = user_api

    def build_scope_type_options(self) -> tuple[dict[str, object], ...]:
        if self._access_api is None:
            return ()
        result = self._access_api.list_scope_types()
        if not result.ok or result.data is None:
            return ()
        return tuple(
            {
                "label": row.label,
                "value": row.value,
                "supportingText": row.supporting_text,
                "enabled": row.enabled,
            }
            for row in result.data
        )

    def build_scope_options(self, scope_type: str) -> tuple[dict[str, object], ...]:
        if self._access_api is None:
            return ()
        normalized_scope_type = scope_type.strip().lower()
        if not normalized_scope_type:
            return ()
        result = self._access_api.list_scope_targets(normalized_scope_type)
        if not result.ok or result.data is None:
            return ()
        return tuple(
            {
                "label": row.label,
                "value": row.id,
                "supportingText": row.supporting_text,
            }
            for row in result.data
        )

    def build_user_options(self) -> tuple[dict[str, object], ...]:
        if self._user_api is None:
            return ()
        result = self._user_api.list_users()
        if not result.ok or result.data is None:
            return ()
        return tuple(
            {
                "label": row.display_name or row.username,
                "value": row.id,
                "supportingText": row.username,
            }
            for row in result.data
        )

    def build_role_options(self, scope_type: str) -> tuple[dict[str, object], ...]:
        if self._access_api is None:
            return ()
        normalized_scope_type = scope_type.strip().lower()
        if not normalized_scope_type:
            return ()
        result = self._access_api.list_scope_role_choices(normalized_scope_type)
        if not result.ok or result.data is None:
            return ()
        return tuple(
            {
                "label": role_name.replace("_", " ").title(),
                "value": role_name,
                "supportingText": "",
            }
            for role_name in result.data
        )

    def build_scope_grants(
        self,
        *,
        scope_type: str,
        scope_id: str,
    ) -> PlatformWorkspaceActionListViewModel:
        if self._access_api is None:
            return PlatformWorkspaceActionListViewModel(
                title="Scoped Access",
                subtitle="Scope grants appear here once the platform access API is connected.",
                empty_state="Platform access API is not connected in this QML preview.",
            )
        normalized_scope_type = scope_type.strip().lower()
        normalized_scope_id = scope_id.strip()
        if not normalized_scope_type or not normalized_scope_id:
            return PlatformWorkspaceActionListViewModel(
                title="Scoped Access",
                subtitle="Choose a scope type and scope to review access grants.",
                empty_state="No scope is selected yet.",
            )

        result = self._access_api.list_scope_grants(
            scope_type=normalized_scope_type,
            scope_id=normalized_scope_id,
        )
        if not result.ok or result.data is None:
            message = result.error.message if result.error is not None else "Unable to load scope grants."
            return PlatformWorkspaceActionListViewModel(
                title="Scoped Access",
                subtitle=message,
                empty_state=message,
            )

        user_lookup = self._user_lookup()
        return PlatformWorkspaceActionListViewModel(
            title="Scoped Access",
            subtitle=f"Access grants for {normalized_scope_type.title()} {normalized_scope_id}.",
            empty_state="No access grants are assigned to this scope yet.",
            items=tuple(
                self._serialize_grant(row, user_lookup=user_lookup)
                for row in result.data
            ),
        )

    def build_security_users(self) -> PlatformWorkspaceActionListViewModel:
        if self._user_api is None:
            return PlatformWorkspaceActionListViewModel(
                title="Security",
                subtitle="Account security records appear here once the platform user API is connected.",
                empty_state="Platform user API is not connected in this QML preview.",
            )
        result = self._user_api.list_users()
        if not result.ok or result.data is None:
            message = result.error.message if result.error is not None else "Unable to load security users."
            return PlatformWorkspaceActionListViewModel(
                title="Security",
                subtitle=message,
                empty_state=message,
            )
        return PlatformWorkspaceActionListViewModel(
            title="Security",
            subtitle="Unlock accounts and revoke live sessions from the QML admin workspace.",
            empty_state="No user accounts are available yet.",
            items=tuple(self._serialize_security_user(row) for row in result.data),
        )

    def assign_scope_grant(
        self,
        *,
        scope_type: str,
        scope_id: str,
        user_id: str,
        scope_role: str,
    ) -> DesktopApiResult[object]:
        if self._access_api is None:
            return preview_error_result("Platform access API is not connected in this QML preview.")
        if not scope_type.strip() or not scope_id.strip() or not user_id.strip():
            return self._validation_error("Choose a scope, user, and role before assigning access.")
        return self._access_api.assign_scope_grant(
            ScopedAccessGrantAssignCommand(
                scope_type=scope_type.strip().lower(),
                scope_id=scope_id.strip(),
                user_id=user_id.strip(),
                scope_role=scope_role.strip().lower() or "viewer",
            )
        )

    def remove_scope_grant(
        self,
        *,
        scope_type: str,
        scope_id: str,
        user_id: str,
    ) -> DesktopApiResult[object]:
        if self._access_api is None:
            return preview_error_result("Platform access API is not connected in this QML preview.")
        if not scope_type.strip() or not scope_id.strip() or not user_id.strip():
            return self._validation_error("Choose a scope and membership before removing access.")
        return self._access_api.remove_scope_grant(
            ScopedAccessGrantRemoveCommand(
                scope_type=scope_type.strip().lower(),
                scope_id=scope_id.strip(),
                user_id=user_id.strip(),
            )
        )

    def unlock_user(self, user_id: str) -> DesktopApiResult[object]:
        if self._user_api is None:
            return preview_error_result("Platform user API is not connected in this QML preview.")
        return self._user_api.unlock_user_account(user_id.strip())

    def revoke_sessions(self, user_id: str) -> DesktopApiResult[object]:
        if self._user_api is None:
            return preview_error_result("Platform user API is not connected in this QML preview.")
        return self._user_api.revoke_user_sessions(
            user_id.strip(),
            note="Revoked from the QML access security surface.",
        )

    def scope_hint(self, scope_type: str, scope_options: tuple[dict[str, object], ...]) -> str:
        options = self.build_scope_type_options()
        selected = next(
            (row for row in options if str(row.get("value", "")) == scope_type.strip().lower()),
            None,
        )
        if selected is None:
            return "Choose a scope type to review access grants."
        if not bool(selected.get("enabled", True)):
            return str(selected.get("supportingText", "") or "This scope is not available right now.")
        if not scope_options:
            return "No scopes are available yet for the selected type."
        return "Assign scoped access and remove grants from the selected scope."

    def _user_lookup(self) -> dict[str, UserDto]:
        if self._user_api is None:
            return {}
        result = self._user_api.list_users()
        if not result.ok or result.data is None:
            return {}
        return {
            row.id: row
            for row in result.data
        }

    @staticmethod
    def _serialize_grant(row, *, user_lookup: dict[str, UserDto]) -> PlatformWorkspaceActionItemViewModel:
        user = user_lookup.get(row.user_id)
        username = user.username if user is not None else row.user_id
        display_name = user.display_name if user is not None and user.display_name else username
        permissions = ", ".join(row.permission_codes) or "No effective permissions"
        return PlatformWorkspaceActionItemViewModel(
            id=row.user_id,
            title=display_name,
            status_label=row.scope_role.replace("_", " ").title(),
            subtitle=username,
            supporting_text=permissions,
            meta_text=PlatformAccessWorkspacePresenter._format_timestamp(row.created_at),
            can_primary_action=True,
            state={
                "grantId": row.id,
                "userId": row.user_id,
                "scopeType": row.scope_type,
                "scopeId": row.scope_id,
            },
        )

    @staticmethod
    def _serialize_security_user(row: UserDto) -> PlatformWorkspaceActionItemViewModel:
        posture = []
        posture.append("Locked" if row.locked_until is not None else "Not locked")
        posture.append(f"{row.failed_login_attempts} failed attempts")
        if row.session_expires_at is not None:
            posture.append("Session active")
        return PlatformWorkspaceActionItemViewModel(
            id=row.id,
            title=row.display_name or row.username,
            status_label="Locked" if row.locked_until is not None else ("Active" if row.is_active else "Inactive"),
            subtitle=row.username,
            supporting_text=" | ".join(posture),
            meta_text=(
                f"Locked until: {PlatformAccessWorkspacePresenter._format_timestamp(row.locked_until)} | "
                f"Session expires: {PlatformAccessWorkspacePresenter._format_timestamp(row.session_expires_at)}"
            ),
            can_primary_action=row.locked_until is not None,
            can_secondary_action=row.session_expires_at is not None,
            state={
                "userId": row.id,
                "isActive": row.is_active,
            },
        )

    @staticmethod
    def _format_timestamp(value: datetime | None) -> str:
        if value is None:
            return "-"
        return value.strftime("%Y-%m-%d %H:%M")

    @staticmethod
    def _validation_error(message: str) -> DesktopApiResult[object]:
        return DesktopApiResult(
            ok=False,
            error=DesktopApiError(
                code="validation_error",
                message=message,
                category="validation",
            ),
        )


__all__ = ["PlatformAccessWorkspacePresenter"]

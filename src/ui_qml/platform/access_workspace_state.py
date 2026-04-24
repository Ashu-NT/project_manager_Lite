from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Property, QObject, Signal, Slot

from src.ui_qml.platform.presenters.access_workspace_presenter import PlatformAccessWorkspacePresenter
from src.ui_qml.platform.workspace_state import (
    _BasePlatformWorkspaceController,
    serialize_action_list,
    serialize_operation_result,
)


class PlatformAdminAccessWorkspaceController(_BasePlatformWorkspaceController):
    scopeTypeOptionsChanged = Signal()
    selectedScopeTypeChanged = Signal()
    scopeOptionsChanged = Signal()
    selectedScopeIdChanged = Signal()
    userOptionsChanged = Signal()
    selectedUserIdChanged = Signal()
    roleOptionsChanged = Signal()
    selectedRoleChanged = Signal()
    scopeHintChanged = Signal()
    scopeGrantsChanged = Signal()
    securityUsersChanged = Signal()

    def __init__(
        self,
        *,
        presenter: PlatformAccessWorkspacePresenter,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._presenter = presenter
        self._scope_type_options: list[dict[str, object]] = []
        self._selected_scope_type = ""
        self._scope_options: list[dict[str, object]] = []
        self._selected_scope_id = ""
        self._user_options: list[dict[str, object]] = []
        self._selected_user_id = ""
        self._role_options: list[dict[str, object]] = []
        self._selected_role = ""
        self._scope_hint = ""
        self._scope_grants: dict[str, object] = {"title": "", "subtitle": "", "emptyState": "", "items": []}
        self._security_users: dict[str, object] = {"title": "", "subtitle": "", "emptyState": "", "items": []}
        self.refresh()

    @Property("QVariantList", notify=scopeTypeOptionsChanged)
    def scopeTypeOptions(self) -> list[dict[str, object]]:
        return self._scope_type_options

    @Property(str, notify=selectedScopeTypeChanged)
    def selectedScopeType(self) -> str:
        return self._selected_scope_type

    @Property("QVariantList", notify=scopeOptionsChanged)
    def scopeOptions(self) -> list[dict[str, object]]:
        return self._scope_options

    @Property(str, notify=selectedScopeIdChanged)
    def selectedScopeId(self) -> str:
        return self._selected_scope_id

    @Property("QVariantList", notify=userOptionsChanged)
    def userOptions(self) -> list[dict[str, object]]:
        return self._user_options

    @Property(str, notify=selectedUserIdChanged)
    def selectedUserId(self) -> str:
        return self._selected_user_id

    @Property("QVariantList", notify=roleOptionsChanged)
    def roleOptions(self) -> list[dict[str, object]]:
        return self._role_options

    @Property(str, notify=selectedRoleChanged)
    def selectedRole(self) -> str:
        return self._selected_role

    @Property(str, notify=scopeHintChanged)
    def scopeHint(self) -> str:
        return self._scope_hint

    @Property("QVariantMap", notify=scopeGrantsChanged)
    def scopeGrants(self) -> dict[str, object]:
        return self._scope_grants

    @Property("QVariantMap", notify=securityUsersChanged)
    def securityUsers(self) -> dict[str, object]:
        return self._security_users

    @Slot()
    def refresh(self) -> None:
        self._set_is_loading(True)
        self._set_error_message("")
        self._refresh_scope_type_options()
        self._refresh_user_options()
        self._refresh_role_options()
        self._refresh_scope_options()
        self._refresh_scope_grants()
        self._refresh_security_users()
        self._refresh_scope_hint()
        self._refresh_empty_state()
        self._set_is_loading(False)

    @Slot(str)
    def setScopeType(self, scope_type: str) -> None:
        normalized_scope_type = scope_type.strip().lower()
        if not normalized_scope_type or normalized_scope_type == self._selected_scope_type:
            return
        self._set_selected_scope_type(normalized_scope_type)
        self._refresh_role_options()
        self._refresh_scope_options()
        self._refresh_scope_grants()
        self._refresh_scope_hint()
        self._refresh_empty_state()

    @Slot(str)
    def setScopeId(self, scope_id: str) -> None:
        normalized_scope_id = scope_id.strip()
        if normalized_scope_id == self._selected_scope_id:
            return
        self._set_selected_scope_id(normalized_scope_id)
        self._refresh_scope_grants()
        self._refresh_scope_hint()
        self._refresh_empty_state()

    @Slot(str)
    def setSelectedUserId(self, user_id: str) -> None:
        self._set_selected_user_id(user_id.strip())

    @Slot(str)
    def setSelectedRole(self, role_name: str) -> None:
        self._set_selected_role(role_name.strip().lower())

    @Slot(result="QVariantMap")
    def assignMembership(self) -> dict[str, object]:
        return self._run_mutation(
            operation=lambda: self._presenter.assign_scope_grant(
                scope_type=self._selected_scope_type,
                scope_id=self._selected_scope_id,
                user_id=self._selected_user_id,
                scope_role=self._selected_role,
            ),
            success_message="Access grant assigned.",
            on_success=self._refresh_after_access_change,
        )

    @Slot(str, result="QVariantMap")
    def removeMembership(self, user_id: str) -> dict[str, object]:
        return self._run_mutation(
            operation=lambda: self._presenter.remove_scope_grant(
                scope_type=self._selected_scope_type,
                scope_id=self._selected_scope_id,
                user_id=user_id,
            ),
            success_message="Access grant removed.",
            on_success=self._refresh_after_access_change,
        )

    @Slot(str, result="QVariantMap")
    def unlockUser(self, user_id: str) -> dict[str, object]:
        return self._run_mutation(
            operation=lambda: self._presenter.unlock_user(user_id),
            success_message="User account unlocked.",
            on_success=self._refresh_after_security_change,
        )

    @Slot(str, result="QVariantMap")
    def revokeSessions(self, user_id: str) -> dict[str, object]:
        return self._run_mutation(
            operation=lambda: self._presenter.revoke_sessions(user_id),
            success_message="User sessions revoked.",
            on_success=self._refresh_after_security_change,
        )

    def _run_mutation(
        self,
        *,
        operation: Callable[[], object],
        success_message: str,
        on_success: Callable[[], None],
    ) -> dict[str, object]:
        self._set_is_busy(True)
        self._set_error_message("")
        result = operation()
        payload = serialize_operation_result(result, success_message=success_message)
        self._set_operation_result(payload)
        if payload["ok"]:
            self._set_feedback_message(str(payload["message"]))
            on_success()
        else:
            self._set_feedback_message("")
            self._set_error_message(str(payload["message"]))
        self._set_is_busy(False)
        return dict(self.operationResult)

    def _refresh_after_access_change(self) -> None:
        self._refresh_scope_grants()
        self._refresh_security_users()
        self._refresh_empty_state()

    def _refresh_after_security_change(self) -> None:
        self._refresh_security_users()
        self._refresh_empty_state()

    def _refresh_scope_type_options(self) -> None:
        options = list(self._presenter.build_scope_type_options())
        self._set_scope_type_options(options)
        available_types = [str(option.get("value", "")) for option in options]
        selected_scope_type = self._selected_scope_type
        if selected_scope_type not in available_types:
            fallback = next(
                (str(option.get("value", "")) for option in options if bool(option.get("enabled", True))),
                next(iter(available_types), ""),
            )
            self._set_selected_scope_type(fallback)

    def _refresh_scope_options(self) -> None:
        options = list(self._presenter.build_scope_options(self._selected_scope_type))
        self._set_scope_options(options)
        available_ids = [str(option.get("value", "")) for option in options]
        if self._selected_scope_id not in available_ids:
            self._set_selected_scope_id(next(iter(available_ids), ""))

    def _refresh_user_options(self) -> None:
        options = list(self._presenter.build_user_options())
        self._set_user_options(options)
        available_ids = [str(option.get("value", "")) for option in options]
        if self._selected_user_id not in available_ids:
            self._set_selected_user_id(next(iter(available_ids), ""))

    def _refresh_role_options(self) -> None:
        options = list(self._presenter.build_role_options(self._selected_scope_type))
        self._set_role_options(options)
        available_roles = [str(option.get("value", "")) for option in options]
        if self._selected_role not in available_roles:
            self._set_selected_role(next(iter(available_roles), "viewer"))

    def _refresh_scope_hint(self) -> None:
        hint = self._presenter.scope_hint(
            self._selected_scope_type,
            tuple(self._scope_options),
        )
        self._set_scope_hint(hint)

    def _refresh_scope_grants(self) -> None:
        self._set_scope_grants(
            serialize_action_list(
                self._presenter.build_scope_grants(
                    scope_type=self._selected_scope_type,
                    scope_id=self._selected_scope_id,
                )
            )
        )

    def _refresh_security_users(self) -> None:
        self._set_security_users(serialize_action_list(self._presenter.build_security_users()))

    def _refresh_empty_state(self) -> None:
        has_items = bool(self._scope_grants.get("items") or self._security_users.get("items"))
        self._set_empty_state("" if has_items else "No access or security records are available yet.")

    def _set_scope_type_options(self, options: list[dict[str, object]]) -> None:
        if options == self._scope_type_options:
            return
        self._scope_type_options = options
        self.scopeTypeOptionsChanged.emit()

    def _set_selected_scope_type(self, value: str) -> None:
        if value == self._selected_scope_type:
            return
        self._selected_scope_type = value
        self.selectedScopeTypeChanged.emit()

    def _set_scope_options(self, options: list[dict[str, object]]) -> None:
        if options == self._scope_options:
            return
        self._scope_options = options
        self.scopeOptionsChanged.emit()

    def _set_selected_scope_id(self, value: str) -> None:
        if value == self._selected_scope_id:
            return
        self._selected_scope_id = value
        self.selectedScopeIdChanged.emit()

    def _set_user_options(self, options: list[dict[str, object]]) -> None:
        if options == self._user_options:
            return
        self._user_options = options
        self.userOptionsChanged.emit()

    def _set_selected_user_id(self, value: str) -> None:
        if value == self._selected_user_id:
            return
        self._selected_user_id = value
        self.selectedUserIdChanged.emit()

    def _set_role_options(self, options: list[dict[str, object]]) -> None:
        if options == self._role_options:
            return
        self._role_options = options
        self.roleOptionsChanged.emit()

    def _set_selected_role(self, value: str) -> None:
        if value == self._selected_role:
            return
        self._selected_role = value
        self.selectedRoleChanged.emit()

    def _set_scope_hint(self, value: str) -> None:
        if value == self._scope_hint:
            return
        self._scope_hint = value
        self.scopeHintChanged.emit()

    def _set_scope_grants(self, scope_grants: dict[str, object]) -> None:
        if scope_grants == self._scope_grants:
            return
        self._scope_grants = scope_grants
        self.scopeGrantsChanged.emit()

    def _set_security_users(self, security_users: dict[str, object]) -> None:
        if security_users == self._security_users:
            return
        self._security_users = security_users
        self.securityUsersChanged.emit()


__all__ = ["PlatformAdminAccessWorkspaceController"]

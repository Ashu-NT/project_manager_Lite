from __future__ import annotations

import logging
from typing import Callable

from PySide6.QtCore import Property, QObject, Signal, Slot
from PySide6.QtQml import QmlElement, QmlUncreatable

from src.ui_qml.shell.context import ShellContext
from src.ui_qml.shell.presenters.global_overview_presenter import GlobalOverviewPresenter, SectionResult
from src.ui_qml.shell.view_models.global_overview import (
    ActionCenterRowViewModel,
    ActivityRowViewModel,
    AttentionCardViewModel,
    GlobalOverviewContextViewModel,
    ModuleCardViewModel,
    QuickActionViewModel,
)

QML_IMPORT_NAME = "Shell.Controllers"
QML_IMPORT_MAJOR_VERSION = 1

logger = logging.getLogger(__name__)

_EMPTY_STATE: dict[str, object] = {"loading": False, "errorMessage": "", "empty": False}
_EMPTY_CONTEXT: dict[str, object] = {
    "tenantName": "",
    "organizationName": "",
    "roleLabel": "",
    "contextLine": "",
}


def _serialize_context(vm: GlobalOverviewContextViewModel) -> dict[str, object]:
    return {
        "tenantName": vm.tenant_name,
        "organizationName": vm.organization_name,
        "roleLabel": vm.role_label or "",
        "contextLine": vm.context_line,
    }


def _serialize_attention_card(vm: AttentionCardViewModel) -> dict[str, object]:
    return {
        "key": vm.key,
        "label": vm.label,
        "value": vm.value,
        "supportingText": vm.supporting_text,
        "routeId": vm.route_id,
        "filterKey": vm.filter_key,
    }


def _serialize_module_card(vm: ModuleCardViewModel) -> dict[str, object]:
    return {
        "moduleCode": vm.module_code,
        "title": vm.title,
        "description": vm.description,
        "iconKey": vm.icon_key,
        "summaryText": vm.summary_text,
        "routeId": vm.route_id,
    }


def _serialize_activity_row(vm: ActivityRowViewModel) -> dict[str, object]:
    return {
        "id": vm.id,
        "title": vm.title,
        "actorLabel": vm.actor_label,
        "moduleLabel": vm.module_label,
        "timestampLabel": vm.timestamp_label,
        "icon": vm.icon or "",
        "color": vm.color or "",
        "activityType": vm.activity_type,
    }


def _serialize_action_center_row(vm: ActionCenterRowViewModel) -> dict[str, object]:
    return {
        "id": vm.id,
        "title": vm.title,
        "moduleLabel": vm.module_label,
        "subjectDisplay": vm.subject_display,
        "actionState": vm.action_state,
        "statusLabel": vm.status_label,
        "priorityLabel": vm.priority_label or "",
        "dueLabel": vm.due_label or "",
        "routeId": vm.route_id,
        "kind": vm.kind,
    }


def _serialize_quick_action(vm: QuickActionViewModel) -> dict[str, object]:
    return {
        "key": vm.key,
        "label": vm.label,
        "icon": vm.icon,
        "routeId": vm.route_id,
        "actionType": vm.action_type,
    }


@QmlElement
@QmlUncreatable("Global Overview controllers are provided by the application shell.")
class GlobalOverviewController(QObject):
    contextChanged = Signal()
    contextStateChanged = Signal()
    attentionChanged = Signal()
    attentionStateChanged = Signal()
    modulesChanged = Signal()
    modulesStateChanged = Signal()
    recentActivityChanged = Signal()
    recentActivityStateChanged = Signal()
    actionCenterChanged = Signal()
    actionCenterStateChanged = Signal()
    quickActionsChanged = Signal()
    quickActionsStateChanged = Signal()

    def __init__(
        self,
        *,
        presenter: GlobalOverviewPresenter,
        shell_context: ShellContext | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._presenter = presenter
        self._shell_context = shell_context
        self._context: dict[str, object] = dict(_EMPTY_CONTEXT)
        self._context_state: dict[str, object] = dict(_EMPTY_STATE)
        self._attention: list[dict[str, object]] = []
        self._attention_state: dict[str, object] = dict(_EMPTY_STATE)
        self._modules: list[dict[str, object]] = []
        self._modules_state: dict[str, object] = dict(_EMPTY_STATE)
        self._recent_activity: list[dict[str, object]] = []
        self._recent_activity_state: dict[str, object] = dict(_EMPTY_STATE)
        self._action_center: list[dict[str, object]] = []
        self._action_center_state: dict[str, object] = dict(_EMPTY_STATE)
        self._quick_actions: list[dict[str, object]] = []
        self._quick_actions_state: dict[str, object] = dict(_EMPTY_STATE)
        if shell_context is not None:
            shell_context.scopeChanged.connect(self._on_scope_changed)

    # -- properties ----------------------------------------------------------

    @Property("QVariantMap", notify=contextChanged)
    def context(self) -> dict[str, object]:
        return self._context

    @Property("QVariantMap", notify=contextStateChanged)
    def contextState(self) -> dict[str, object]:
        return self._context_state

    @Property("QVariantList", notify=attentionChanged)
    def attention(self) -> list[dict[str, object]]:
        return self._attention

    @Property("QVariantMap", notify=attentionStateChanged)
    def attentionState(self) -> dict[str, object]:
        return self._attention_state

    @Property("QVariantList", notify=modulesChanged)
    def modules(self) -> list[dict[str, object]]:
        return self._modules

    @Property("QVariantMap", notify=modulesStateChanged)
    def modulesState(self) -> dict[str, object]:
        return self._modules_state

    @Property("QVariantList", notify=recentActivityChanged)
    def recentActivity(self) -> list[dict[str, object]]:
        return self._recent_activity

    @Property("QVariantMap", notify=recentActivityStateChanged)
    def recentActivityState(self) -> dict[str, object]:
        return self._recent_activity_state

    @Property("QVariantList", notify=actionCenterChanged)
    def actionCenter(self) -> list[dict[str, object]]:
        return self._action_center

    @Property("QVariantMap", notify=actionCenterStateChanged)
    def actionCenterState(self) -> dict[str, object]:
        return self._action_center_state

    @Property("QVariantList", notify=quickActionsChanged)
    def quickActions(self) -> list[dict[str, object]]:
        return self._quick_actions

    @Property("QVariantMap", notify=quickActionsStateChanged)
    def quickActionsState(self) -> dict[str, object]:
        return self._quick_actions_state

    # -- reload slots ----------------------------------------------------------

    @Slot()
    def reload(self) -> None:
        """Reload every section independently. One section raising/failing
        never prevents the others from loading or being attempted."""
        for reload_one in (
            self.reloadContext,
            self.reloadAttention,
            self.reloadModules,
            self.reloadRecentActivity,
            self.reloadActionCenter,
            self.reloadQuickActions,
        ):
            try:
                reload_one()
            except Exception:  # noqa: BLE001
                logger.exception("Global Overview section reload raised unexpectedly")

    @Slot()
    def reloadContext(self) -> None:
        self._run_section_load(
            loading_setter=lambda: self._set_context_state(dict(_EMPTY_STATE) | {"loading": True}),
            load=self._presenter.load_context,
            on_success=lambda data: self._set_context(_serialize_context(data)),
            set_state=self._set_context_state,
            clear_data=lambda: self._set_context(dict(_EMPTY_CONTEXT)),
        )

    @Slot()
    def reloadAttention(self) -> None:
        self._run_section_load(
            loading_setter=lambda: self._set_attention_state(dict(_EMPTY_STATE) | {"loading": True}),
            load=self._presenter.load_attention,
            on_success=lambda data: self._set_attention(
                [_serialize_attention_card(card) for card in data]
            ),
            set_state=self._set_attention_state,
            clear_data=lambda: self._set_attention([]),
        )

    @Slot()
    def reloadModules(self) -> None:
        self._run_section_load(
            loading_setter=lambda: self._set_modules_state(dict(_EMPTY_STATE) | {"loading": True}),
            load=self._presenter.load_modules,
            on_success=lambda data: self._set_modules(
                [_serialize_module_card(card) for card in data]
            ),
            set_state=self._set_modules_state,
            clear_data=lambda: self._set_modules([]),
        )

    @Slot()
    def reloadRecentActivity(self) -> None:
        self._run_section_load(
            loading_setter=lambda: self._set_recent_activity_state(
                dict(_EMPTY_STATE) | {"loading": True}
            ),
            load=self._presenter.load_recent_activity,
            on_success=lambda data: self._set_recent_activity(
                [_serialize_activity_row(row) for row in data]
            ),
            set_state=self._set_recent_activity_state,
            clear_data=lambda: self._set_recent_activity([]),
        )

    @Slot()
    def reloadActionCenter(self) -> None:
        self._run_section_load(
            loading_setter=lambda: self._set_action_center_state(
                dict(_EMPTY_STATE) | {"loading": True}
            ),
            load=self._presenter.load_action_center,
            on_success=lambda data: self._set_action_center(
                [_serialize_action_center_row(row) for row in data]
            ),
            set_state=self._set_action_center_state,
            clear_data=lambda: self._set_action_center([]),
        )

    @Slot()
    def reloadQuickActions(self) -> None:
        self._run_section_load(
            loading_setter=lambda: self._set_quick_actions_state(
                dict(_EMPTY_STATE) | {"loading": True}
            ),
            load=self._presenter.load_quick_actions,
            on_success=lambda data: self._set_quick_actions(
                [_serialize_quick_action(action) for action in data]
            ),
            set_state=self._set_quick_actions_state,
            clear_data=lambda: self._set_quick_actions([]),
        )

    # -- navigation ----------------------------------------------------------

    @Slot(str)
    def selectRoute(self, route_id: str) -> None:
        """Delegates navigation to ShellContext -- the controller never owns
        routing state itself (Attention/Module/Action Center/Recent Activity
        rows all carry a route_id that ultimately reaches this slot)."""
        if not route_id:
            return
        if self._shell_context is None:
            logger.warning("Global Overview route selection ignored: no ShellContext wired.")
            return
        self._shell_context.selectRoute(route_id)

    # -- scope change ----------------------------------------------------------

    def _on_scope_changed(self) -> None:
        """Clears every section's stale, previous-scope data before
        reloading so nothing from the old organization is ever shown as
        current while (or after) the reload runs. Reads authoritative
        tenant/org state only through the Desktop API on reload -- never
        from a locally-cached id."""
        self._set_context(dict(_EMPTY_CONTEXT))
        self._set_attention([])
        self._set_modules([])
        self._set_recent_activity([])
        self._set_action_center([])
        self._set_quick_actions([])
        self.reload()

    # -- internal helpers ----------------------------------------------------------

    def _run_section_load(
        self,
        *,
        loading_setter: Callable[[], None],
        load: Callable[[], SectionResult],
        on_success: Callable[[object], None],
        set_state: Callable[[dict[str, object]], None],
        clear_data: Callable[[], None],
    ) -> None:
        loading_setter()
        try:
            result = load()
        except Exception:  # noqa: BLE001
            logger.exception("Global Overview section load raised unexpectedly")
            clear_data()
            set_state({"loading": False, "errorMessage": "This section could not be loaded.", "empty": False})
            return
        if not result.ok:
            clear_data()
            set_state({"loading": False, "errorMessage": result.error_message or "", "empty": False})
            return
        on_success(result.data)
        set_state({"loading": False, "errorMessage": "", "empty": result.empty})

    def _set_context(self, value: dict[str, object]) -> None:
        if value == self._context:
            return
        self._context = value
        self.contextChanged.emit()

    def _set_context_state(self, value: dict[str, object]) -> None:
        if value == self._context_state:
            return
        self._context_state = value
        self.contextStateChanged.emit()

    def _set_attention(self, value: list[dict[str, object]]) -> None:
        if value == self._attention:
            return
        self._attention = value
        self.attentionChanged.emit()

    def _set_attention_state(self, value: dict[str, object]) -> None:
        if value == self._attention_state:
            return
        self._attention_state = value
        self.attentionStateChanged.emit()

    def _set_modules(self, value: list[dict[str, object]]) -> None:
        if value == self._modules:
            return
        self._modules = value
        self.modulesChanged.emit()

    def _set_modules_state(self, value: dict[str, object]) -> None:
        if value == self._modules_state:
            return
        self._modules_state = value
        self.modulesStateChanged.emit()

    def _set_recent_activity(self, value: list[dict[str, object]]) -> None:
        if value == self._recent_activity:
            return
        self._recent_activity = value
        self.recentActivityChanged.emit()

    def _set_recent_activity_state(self, value: dict[str, object]) -> None:
        if value == self._recent_activity_state:
            return
        self._recent_activity_state = value
        self.recentActivityStateChanged.emit()

    def _set_action_center(self, value: list[dict[str, object]]) -> None:
        if value == self._action_center:
            return
        self._action_center = value
        self.actionCenterChanged.emit()

    def _set_action_center_state(self, value: dict[str, object]) -> None:
        if value == self._action_center_state:
            return
        self._action_center_state = value
        self.actionCenterStateChanged.emit()

    def _set_quick_actions(self, value: list[dict[str, object]]) -> None:
        if value == self._quick_actions:
            return
        self._quick_actions = value
        self.quickActionsChanged.emit()

    def _set_quick_actions_state(self, value: dict[str, object]) -> None:
        if value == self._quick_actions_state:
            return
        self._quick_actions_state = value
        self.quickActionsStateChanged.emit()


__all__ = ["GlobalOverviewController"]

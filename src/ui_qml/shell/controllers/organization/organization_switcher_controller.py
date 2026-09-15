from __future__ import annotations

from PySide6.QtCore import Property, QObject, Signal, Slot
from PySide6.QtQml import QmlElement, QmlUncreatable

from src.ui_qml.shell.presenters.organization.organization_switcher_presenter import (
    OrganizationSwitcherPresenter,
)

QML_IMPORT_NAME = "Shell.Controllers"
QML_IMPORT_MAJOR_VERSION = 1


@QmlElement
@QmlUncreatable("Shell organization switcher controllers are provided by the application shell.")
class OrganizationSwitcherController(QObject):
    """Shell-owned controller for the global-header organization switcher.

    Deliberately independent of GlobalOverviewController, NotificationsController,
    PM controllers, and any future module controller -- it only exposes
    `organizationSwitched`. The shared shell-wide invalidation
    (ShellContext.scopeChanged) is wired from this signal at the composition
    root (app.py), not known to this class.
    """

    organizationsChanged = Signal()
    activeOrganizationIdChanged = Signal()
    isMultiOrganizationChanged = Signal()
    isLoadingChanged = Signal()
    errorMessageChanged = Signal()
    organizationSwitched = Signal()

    def __init__(
        self,
        *,
        presenter: OrganizationSwitcherPresenter,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._presenter = presenter
        self._organizations: list[dict[str, object]] = []
        self._active_organization_id: str = ""
        self._is_loading = False
        self._error_message = ""

    # -- properties ----------------------------------------------------------

    @Property("QVariantList", notify=organizationsChanged)
    def organizations(self) -> list[dict[str, object]]:
        return self._organizations

    @Property(str, notify=activeOrganizationIdChanged)
    def activeOrganizationId(self) -> str:
        return self._active_organization_id

    @Property(bool, notify=isMultiOrganizationChanged)
    def isMultiOrganization(self) -> bool:
        return len(self._organizations) > 1

    @Property(bool, notify=isLoadingChanged)
    def isLoading(self) -> bool:
        return self._is_loading

    @Property(str, notify=errorMessageChanged)
    def errorMessage(self) -> str:
        return self._error_message

    # -- slots ----------------------------------------------------------

    @Slot()
    def refresh(self) -> None:
        self._set_is_loading(True)
        self._set_error_message("")
        self._load_organizations()
        self._load_active_organization_id()
        self._set_is_loading(False)

    @Slot(str, result=bool)
    def switchToOrganization(self, organization_id: str) -> bool:
        normalized = str(organization_id or "").strip()
        if not normalized:
            return False
        self._set_is_loading(True)
        result = self._presenter.switch_to_organization(normalized)
        self._set_is_loading(False)
        if not result.ok:
            message = result.error.message if result.error is not None else "Organization switch failed."
            self._set_error_message(message)
            return False
        self._set_error_message("")
        self._load_organizations()
        self._load_active_organization_id()
        self.organizationSwitched.emit()
        return True

    # -- internal ----------------------------------------------------------

    def _load_organizations(self) -> None:
        items = [
            {
                "id": vm.id,
                "displayName": vm.display_name,
                "organizationCode": vm.organization_code,
                "isEnabled": vm.is_enabled,
            }
            for vm in self._presenter.build_organization_list()
        ]
        if items != self._organizations:
            self._organizations = items
            self.organizationsChanged.emit()
            self.isMultiOrganizationChanged.emit()

    def _load_active_organization_id(self) -> None:
        value = self._presenter.get_active_organization_id()
        if value != self._active_organization_id:
            self._active_organization_id = value
            self.activeOrganizationIdChanged.emit()

    def _set_is_loading(self, value: bool) -> None:
        if value == self._is_loading:
            return
        self._is_loading = value
        self.isLoadingChanged.emit()

    def _set_error_message(self, value: str) -> None:
        if value == self._error_message:
            return
        self._error_message = value
        self.errorMessageChanged.emit()


__all__ = ["OrganizationSwitcherController"]

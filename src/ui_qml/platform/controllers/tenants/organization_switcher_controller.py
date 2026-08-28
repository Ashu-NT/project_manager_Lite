from __future__ import annotations

from PySide6.QtCore import Property, Signal, Slot
from PySide6.QtQml import QmlElement, QmlUncreatable

from src.ui_qml.platform.controllers.common import (
    PlatformWorkspaceControllerBase,
    run_mutation,
)
from src.ui_qml.platform.presenters.tenants.organization_switcher_presenter import (
    OrganizationSwitcherPresenter,
)

QML_IMPORT_NAME = "Platform.Controllers"
QML_IMPORT_MAJOR_VERSION = 1


@QmlElement
@QmlUncreatable("Organization switcher controller is provided by the shell runtime.")
class OrganizationSwitcherController(PlatformWorkspaceControllerBase):
    """Shell-level controller for listing and switching the current session's working
    Organization. Sibling of `TenantSwitcherController`, not a merged concept: a tenant switch
    rebuilds the whole authority context (RBAC, module mix, every workspace), while an
    organization switch only rescopes the organization-owned adapters -- P10C keeps them as two
    independently-lifecycled controllers, exactly mirroring how the backend keeps
    `TenantContextService.switch_to_tenant`/`set_active_organization` as two separate methods
    rather than one parameterized switch."""

    organizationsChanged = Signal()
    activeOrganizationIdChanged = Signal()
    isMultiOrganizationChanged = Signal()
    organizationSwitched = Signal()

    def __init__(
        self,
        presenter: OrganizationSwitcherPresenter,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._presenter = presenter
        self._organizations: list[dict[str, object]] = []
        self._active_organization_id: str = ""

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @Property("QVariantList", notify=organizationsChanged)
    def organizations(self) -> list[dict[str, object]]:
        return self._organizations

    @Property(str, notify=activeOrganizationIdChanged)
    def activeOrganizationId(self) -> str:
        return self._active_organization_id

    @Property(bool, notify=isMultiOrganizationChanged)
    def isMultiOrganization(self) -> bool:
        return len(self._organizations) > 1

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    @Slot()
    def refresh(self) -> None:
        self._set_is_loading(True)
        self._load_organizations()
        self._load_active_organization_id()
        self._set_is_loading(False)

    @Slot(str, result="QVariantMap")
    def switchToOrganization(self, organization_id: str) -> dict[str, object]:
        normalized = (organization_id or "").strip()
        if not normalized:
            return dict(self.operationResult)
        return run_mutation(
            operation=lambda: self._presenter.switch_to_organization(normalized),
            success_message="Organization switched.",
            on_success=self._on_switch_success,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_operation_result=self._set_operation_result,
            set_feedback_message=self._set_feedback_message,
        )

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _on_switch_success(self) -> None:
        self._load_active_organization_id()
        self.organizationSwitched.emit()

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
        if self._organizations != items:
            self._organizations = items
            self.organizationsChanged.emit()
            self.isMultiOrganizationChanged.emit()

    def _load_active_organization_id(self) -> None:
        value = self._presenter.get_active_organization_id()
        if self._active_organization_id != value:
            self._active_organization_id = value
            self.activeOrganizationIdChanged.emit()


__all__ = ["OrganizationSwitcherController"]

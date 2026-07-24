from __future__ import annotations

from PySide6.QtCore import Property, Signal, Slot
from PySide6.QtQml import QmlElement, QmlUncreatable

from src.ui_qml.platform.controllers.common import (
    PlatformWorkspaceControllerBase,
    run_mutation,
)
from src.ui_qml.platform.presenters.tenant_switcher_presenter import TenantSwitcherPresenter

QML_IMPORT_NAME = "Platform.Controllers"
QML_IMPORT_MAJOR_VERSION = 1


@QmlElement
@QmlUncreatable("Tenant switcher controller is provided by the shell runtime.")
class TenantSwitcherController(PlatformWorkspaceControllerBase):
    """Shell-level controller for listing and switching tenants.

    Extends PlatformWorkspaceControllerBase so QML gets the standard
    isBusy / errorMessage / feedbackMessage / operationResult properties.
    """

    tenantsChanged = Signal()
    activeTenantIdChanged = Signal()
    isMultiTenantChanged = Signal()
    tenantSwitched = Signal()

    def __init__(
        self,
        presenter: TenantSwitcherPresenter,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._presenter = presenter
        self._tenants: list[dict[str, object]] = []
        self._active_tenant_id: str = ""

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @Property("QVariantList", notify=tenantsChanged)
    def tenants(self) -> list[dict[str, object]]:
        return self._tenants

    @Property(str, notify=activeTenantIdChanged)
    def activeTenantId(self) -> str:
        return self._active_tenant_id

    @Property(bool, notify=isMultiTenantChanged)
    def isMultiTenant(self) -> bool:
        return len(self._tenants) > 1

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    @Slot()
    def refresh(self) -> None:
        self._set_is_loading(True)
        self._load_tenants()
        self._load_active_tenant_id()
        self._set_is_loading(False)

    @Slot(str, result="QVariantMap")
    def switchToTenant(self, tenant_id: str) -> dict[str, object]:
        normalized = (tenant_id or "").strip()
        if not normalized:
            return dict(self.operationResult)
        return run_mutation(
            operation=lambda: self._presenter.switch_to_tenant(normalized),
            success_message="Tenant switched.",
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
        self._load_tenants()
        self._load_active_tenant_id()
        self.tenantSwitched.emit()

    def _load_tenants(self) -> None:
        items = [
            {
                "id": vm.id,
                "displayName": vm.display_name,
                "tenantCode": vm.tenant_code,
                "tenantStatus": vm.tenant_status,
                "isActive": vm.is_active,
            }
            for vm in self._presenter.build_tenant_list()
        ]
        if self._tenants != items:
            self._tenants = items
            self.tenantsChanged.emit()
            self.isMultiTenantChanged.emit()

    def _load_active_tenant_id(self) -> None:
        value = self._presenter.get_active_tenant_id()
        if self._active_tenant_id != value:
            self._active_tenant_id = value
            self.activeTenantIdChanged.emit()


__all__ = ["TenantSwitcherController"]

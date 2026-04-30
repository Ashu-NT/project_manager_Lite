from __future__ import annotations

from typing import Any

from PySide6.QtCore import Property, QObject, Signal, Slot

from src.ui_qml.platform.presenters import (
    PlatformSettingsCatalogPresenter,
    PlatformSettingsWorkspacePresenter,
)

from ..common import (
    PlatformWorkspaceControllerBase,
    serialize_action_list,
    serialize_operation_result,
    serialize_workspace_overview,
)


class PlatformSettingsWorkspaceController(PlatformWorkspaceControllerBase):
    moduleEntitlementsChanged = Signal()
    organizationProfilesChanged = Signal()
    lifecycleOptionsChanged = Signal()

    def __init__(
        self,
        *,
        overview_presenter: PlatformSettingsWorkspacePresenter,
        catalog_presenter: PlatformSettingsCatalogPresenter,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._overview_presenter = overview_presenter
        self._catalog_presenter = catalog_presenter
        self._module_entitlements: dict[str, object] = {"title": "", "subtitle": "", "emptyState": "", "items": []}
        self._organization_profiles: dict[str, object] = {"title": "", "subtitle": "", "emptyState": "", "items": []}
        self._lifecycle_options = [dict(option) for option in self._catalog_presenter.lifecycle_options()]
        self.refresh()

    @Property("QVariantMap", notify=moduleEntitlementsChanged)
    def moduleEntitlements(self) -> dict[str, object]:
        return self._module_entitlements

    @Property("QVariantMap", notify=organizationProfilesChanged)
    def organizationProfiles(self) -> dict[str, object]:
        return self._organization_profiles

    @Property("QVariantList", notify=lifecycleOptionsChanged)
    def lifecycleOptions(self) -> list[dict[str, str]]:
        return self._lifecycle_options

    @Slot()
    def refresh(self) -> None:
        self._set_is_loading(True)
        self._set_error_message("")
        self._set_overview(serialize_workspace_overview(self._overview_presenter.build_overview()))
        self._set_module_entitlements(serialize_action_list(self._catalog_presenter.build_module_entitlements()))
        self._set_organization_profiles(serialize_action_list(self._catalog_presenter.build_organization_profiles()))
        has_items = bool(self._module_entitlements.get("items") or self._organization_profiles.get("items"))
        self._set_empty_state("" if has_items else str(self._module_entitlements.get("emptyState") or self._organization_profiles.get("emptyState") or ""))
        self._set_is_loading(False)

    @Slot(str)
    def toggleModuleLicensed(self, module_code: str) -> None:
        self._apply_entitlement_action(
            module_code=module_code,
            operation=self._catalog_presenter.toggle_module_license,
            success_message="Module license state updated.",
        )

    @Slot(str)
    def toggleModuleEnabled(self, module_code: str) -> None:
        self._apply_entitlement_action(
            module_code=module_code,
            operation=self._catalog_presenter.toggle_module_enabled,
            success_message="Module runtime state updated.",
        )

    @Slot(str, str)
    def changeModuleLifecycleStatus(self, module_code: str, lifecycle_status: str) -> None:
        self._apply_entitlement_action(
            module_code=module_code,
            operation=lambda normalized_code: self._catalog_presenter.change_module_lifecycle_status(
                normalized_code,
                lifecycle_status,
            ),
            success_message="Module lifecycle status updated.",
        )

    def _apply_entitlement_action(
        self,
        *,
        module_code: str,
        operation,
        success_message: str,
    ) -> None:
        normalized_code = module_code.strip()
        if not normalized_code:
            return
        self._set_is_busy(True)
        self._set_error_message("")
        result = operation(normalized_code)
        payload = serialize_operation_result(result, success_message=success_message)
        self._set_operation_result(payload)
        if payload["ok"] and getattr(result, "data", None) is not None:
            self._set_feedback_message(str(payload["message"]))
            self._apply_entitlement_update(result.data)
        else:
            self._set_feedback_message("")
            self._set_error_message(str(payload["message"]))
        self._set_is_busy(False)

    def _apply_entitlement_update(self, entitlement) -> None:
        items = [dict(item) for item in self._module_entitlements.get("items", [])]
        updated = False
        for index, item in enumerate(items):
            if item.get("id") != entitlement.module_code:
                continue
            items[index] = self._serialize_entitlement_item(entitlement)
            updated = True
            break
        if not updated:
            self.refresh()
            return
        module_entitlements = dict(self._module_entitlements)
        module_entitlements["items"] = items
        self._set_module_entitlements(module_entitlements)
        self._update_settings_metrics()

    def _update_settings_metrics(self) -> None:
        items = self._module_entitlements.get("items", [])
        licensed_count = sum(1 for item in items if bool((item.get("state") or {}).get("licensed")))
        enabled_count = sum(1 for item in items if bool((item.get("state") or {}).get("runtimeEnabled")))
        planned_count = sum(1 for item in items if bool((item.get("state") or {}).get("planned")))
        metrics = [
            {
                "label": "Licensed modules",
                "value": str(licensed_count),
                "supportingText": "Currently licensed",
            },
            {
                "label": "Enabled modules",
                "value": str(enabled_count),
                "supportingText": "Runtime active",
            },
            {
                "label": "Planned modules",
                "value": str(planned_count),
                "supportingText": "Not yet enabled",
            },
            {
                "label": "Organizations",
                "value": str(len(self._organization_profiles.get("items", []))),
                "supportingText": "Install profiles",
            },
        ]
        overview = dict(self._overview)
        overview["metrics"] = metrics
        self._set_overview(overview)

    @staticmethod
    def _serialize_entitlement_item(entitlement) -> dict[str, Any]:
        return {
            "id": entitlement.module_code,
            "title": entitlement.label,
            "statusLabel": entitlement.lifecycle_label,
            "subtitle": (
                f"{entitlement.stage.title()} | "
                f"{'Licensed' if entitlement.licensed else 'Unlicensed'} | "
                f"{'Enabled' if entitlement.enabled else 'Disabled'}"
            ),
            "supportingText": entitlement.module.description,
            "metaText": (
                f"Runtime: {'Yes' if entitlement.runtime_enabled else 'No'} | "
                f"Capabilities: {', '.join(entitlement.module.primary_capabilities) or '-'}"
            ),
            "canPrimaryAction": not entitlement.planned,
            "canSecondaryAction": (
                not entitlement.planned
                and entitlement.licensed
                and not (
                    not entitlement.runtime_enabled
                    and entitlement.lifecycle_status in {"suspended", "expired"}
                )
            ),
            "canTertiaryAction": not entitlement.planned and entitlement.licensed,
            "state": {
                "licensed": entitlement.licensed,
                "enabled": entitlement.enabled,
                "planned": entitlement.planned,
                "runtimeEnabled": entitlement.runtime_enabled,
                "lifecycleStatus": entitlement.lifecycle_status,
            },
        }

    def _set_module_entitlements(self, module_entitlements: dict[str, object]) -> None:
        if module_entitlements == self._module_entitlements:
            return
        self._module_entitlements = module_entitlements
        self.moduleEntitlementsChanged.emit()

    def _set_organization_profiles(self, organization_profiles: dict[str, object]) -> None:
        if organization_profiles == self._organization_profiles:
            return
        self._organization_profiles = organization_profiles
        self.organizationProfilesChanged.emit()


__all__ = ["PlatformSettingsWorkspaceController"]

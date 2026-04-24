from __future__ import annotations

from src.api.desktop.platform import (
    DesktopApiError,
    DesktopApiResult,
    ModuleEntitlementDto,
    ModuleStatePatchCommand,
    PlatformRuntimeDesktopApi,
)
from src.ui_qml.platform.view_models import (
    PlatformWorkspaceActionItemViewModel,
    PlatformWorkspaceActionListViewModel,
)


class PlatformSettingsCatalogPresenter:
    def __init__(self, *, runtime_api: PlatformRuntimeDesktopApi | None = None) -> None:
        self._runtime_api = runtime_api

    def build_module_entitlements(self) -> PlatformWorkspaceActionListViewModel:
        if self._runtime_api is None:
            return PlatformWorkspaceActionListViewModel(
                title="Module Entitlements",
                subtitle="Module state controls appear here once the platform runtime API is connected.",
                empty_state="Platform runtime API is not connected in this QML preview.",
            )

        runtime_result = self._runtime_api.get_runtime_context()
        if not runtime_result.ok or runtime_result.data is None:
            message = runtime_result.error.message if runtime_result.error is not None else "Unable to load module entitlements."
            return PlatformWorkspaceActionListViewModel(
                title="Module Entitlements",
                subtitle=message,
                empty_state=message,
            )

        context = runtime_result.data
        return PlatformWorkspaceActionListViewModel(
            title="Module Entitlements",
            subtitle=f"{context.context_label} | license and runtime-state controls prepared for QML.",
            empty_state="No module entitlements are available yet.",
            items=tuple(
                PlatformWorkspaceActionItemViewModel(
                    id=entitlement.module_code,
                    title=entitlement.label,
                    status_label=entitlement.lifecycle_label,
                    subtitle=(
                        f"{entitlement.stage.title()} | "
                        f"{'Licensed' if entitlement.licensed else 'Unlicensed'} | "
                        f"{'Enabled' if entitlement.enabled else 'Disabled'}"
                    ),
                    supporting_text=entitlement.module.description,
                    meta_text=(
                        f"Runtime: {'Yes' if entitlement.runtime_enabled else 'No'} | "
                        f"Capabilities: {', '.join(entitlement.module.primary_capabilities) or '-'}"
                    ),
                    can_primary_action=not entitlement.planned,
                    can_secondary_action=(
                        not entitlement.planned
                        and entitlement.licensed
                        and not (
                            not entitlement.runtime_enabled
                            and entitlement.lifecycle_status in {"suspended", "expired"}
                        )
                    ),
                    state={
                        "licensed": entitlement.licensed,
                        "enabled": entitlement.enabled,
                        "planned": entitlement.planned,
                        "runtimeEnabled": entitlement.runtime_enabled,
                        "lifecycleStatus": entitlement.lifecycle_status,
                    },
                )
                for entitlement in context.entitlements
            ),
        )

    def build_organization_profiles(self) -> PlatformWorkspaceActionListViewModel:
        if self._runtime_api is None:
            return PlatformWorkspaceActionListViewModel(
                title="Organization Profiles",
                subtitle="Install profiles appear here once the platform runtime API is connected.",
                empty_state="Platform runtime API is not connected in this QML preview.",
            )

        result = self._runtime_api.list_organizations(active_only=None)
        if not result.ok or result.data is None:
            message = result.error.message if result.error is not None else "Unable to load organization profiles."
            return PlatformWorkspaceActionListViewModel(
                title="Organization Profiles",
                subtitle=message,
                empty_state=message,
            )

        return PlatformWorkspaceActionListViewModel(
            title="Organization Profiles",
            subtitle="Organization tenancy remains visible here while the dedicated admin surface is migrated.",
            empty_state="No organizations are configured yet.",
            items=tuple(
                PlatformWorkspaceActionItemViewModel(
                    id=org.id,
                    title=org.display_name,
                    status_label="Active" if org.is_active else "Inactive",
                    subtitle=org.organization_code,
                    supporting_text=f"{org.timezone_name} | {org.base_currency}",
                    meta_text=f"Version {org.version}",
                    state={
                        "isActive": org.is_active,
                    },
                )
                for org in result.data
            ),
        )

    def toggle_module_license(self, module_code: str) -> DesktopApiResult[object]:
        entitlement_result = self._find_entitlement(module_code)
        if not entitlement_result.ok or entitlement_result.data is None:
            return entitlement_result
        entitlement = entitlement_result.data
        if entitlement.planned:
            return self._validation_error(
                f"{entitlement.label} is still planned and cannot be licensed yet."
            )
        return self._runtime_api.patch_module_state(
            ModuleStatePatchCommand(
                module_code=entitlement.module_code,
                licensed=not entitlement.licensed,
                enabled=entitlement.enabled if entitlement.licensed else False,
            )
        )

    def toggle_module_enabled(self, module_code: str) -> DesktopApiResult[object]:
        entitlement_result = self._find_entitlement(module_code)
        if not entitlement_result.ok or entitlement_result.data is None:
            return entitlement_result
        entitlement = entitlement_result.data
        if entitlement.planned:
            return self._validation_error(
                f"{entitlement.label} is still planned and cannot be enabled yet."
            )
        if not entitlement.licensed:
            return self._validation_error(
                f"{entitlement.label} must be licensed before it can be enabled."
            )
        if not entitlement.runtime_enabled and entitlement.lifecycle_status in {"suspended", "expired"}:
            return self._validation_error(
                f"{entitlement.label} is {entitlement.lifecycle_label.lower()}. Change its lifecycle status before enabling it."
            )
        return self._runtime_api.patch_module_state(
            ModuleStatePatchCommand(
                module_code=entitlement.module_code,
                enabled=not entitlement.enabled,
            )
        )

    def _find_entitlement(self, module_code: str) -> DesktopApiResult[ModuleEntitlementDto]:
        if self._runtime_api is None:
            return self._preview_error("Platform runtime API is not connected in this QML preview.")
        runtime_result = self._runtime_api.get_runtime_context()
        if not runtime_result.ok or runtime_result.data is None:
            return DesktopApiResult(
                ok=False,
                error=runtime_result.error
                or DesktopApiError(
                    code="runtime_context_unavailable",
                    message="Unable to load module entitlements.",
                    category="domain",
                ),
            )
        entitlement = next(
            (
                item
                for item in runtime_result.data.entitlements
                if item.module_code == module_code
            ),
            None,
        )
        if entitlement is None:
            return self._validation_error(f"Module '{module_code}' was not found in the runtime entitlements.")
        return DesktopApiResult(ok=True, data=entitlement)

    @staticmethod
    def _preview_error(message: str) -> DesktopApiResult[object]:
        return DesktopApiResult(
            ok=False,
            error=DesktopApiError(
                code="preview_only",
                message=message,
                category="preview",
            ),
        )

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


__all__ = ["PlatformSettingsCatalogPresenter"]

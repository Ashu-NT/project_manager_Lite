from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from src.api.desktop.platform import PlatformRuntimeDesktopApi
from src.application.runtime.platform_runtime import (
    PlatformRuntimeApplicationService,
    resolve_platform_runtime_application_service,
)


@dataclass(frozen=True)
class DesktopApiRegistry:
    platform_runtime: PlatformRuntimeDesktopApi


def build_desktop_api_registry(services: Mapping[str, object]) -> DesktopApiRegistry:
    platform_runtime_application_service = resolve_platform_runtime_application_service(
        platform_runtime_application_service=services.get("platform_runtime_application_service"),
        module_runtime_service=services.get("module_runtime_service"),
        module_catalog_service=services.get("module_catalog_service"),
        organization_service=services.get("organization_service"),
    )
    if not isinstance(platform_runtime_application_service, PlatformRuntimeApplicationService):
        raise RuntimeError("Platform runtime application service is not configured.")
    return DesktopApiRegistry(
        platform_runtime=PlatformRuntimeDesktopApi(
            platform_runtime_application_service=platform_runtime_application_service,
        )
    )


__all__ = ["DesktopApiRegistry", "build_desktop_api_registry"]

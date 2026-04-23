from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from src.api.desktop.platform import (
    PlatformDocumentDesktopApi,
    PlatformDepartmentDesktopApi,
    PlatformEmployeeDesktopApi,
    PlatformPartyDesktopApi,
    PlatformRuntimeDesktopApi,
    PlatformSiteDesktopApi,
    PlatformUserDesktopApi,
)
from src.application.runtime.platform_runtime import (
    PlatformRuntimeApplicationService,
    resolve_platform_runtime_application_service,
)
from src.core.platform.auth.application import AuthService
from src.core.platform.documents import DocumentService
from src.core.platform.org import DepartmentService, EmployeeService, SiteService
from src.core.platform.party import PartyService


@dataclass(frozen=True)
class DesktopApiRegistry:
    platform_runtime: PlatformRuntimeDesktopApi
    platform_site: PlatformSiteDesktopApi
    platform_department: PlatformDepartmentDesktopApi
    platform_employee: PlatformEmployeeDesktopApi
    platform_document: PlatformDocumentDesktopApi
    platform_party: PlatformPartyDesktopApi
    platform_user: PlatformUserDesktopApi


def build_desktop_api_registry(services: Mapping[str, object]) -> DesktopApiRegistry:
    platform_runtime_application_service = resolve_platform_runtime_application_service(
        platform_runtime_application_service=services.get("platform_runtime_application_service"),
        module_runtime_service=services.get("module_runtime_service"),
        module_catalog_service=services.get("module_catalog_service"),
        organization_service=services.get("organization_service"),
    )
    if not isinstance(platform_runtime_application_service, PlatformRuntimeApplicationService):
        raise RuntimeError("Platform runtime application service is not configured.")
    site_service = services.get("site_service")
    if not isinstance(site_service, SiteService):
        raise RuntimeError("Platform site service is not configured.")
    department_service = services.get("department_service")
    if not isinstance(department_service, DepartmentService):
        raise RuntimeError("Platform department service is not configured.")
    employee_service = services.get("employee_service")
    if not isinstance(employee_service, EmployeeService):
        raise RuntimeError("Platform employee service is not configured.")
    document_service = services.get("document_service")
    if not isinstance(document_service, DocumentService):
        raise RuntimeError("Platform document service is not configured.")
    party_service = services.get("party_service")
    if not isinstance(party_service, PartyService):
        raise RuntimeError("Platform party service is not configured.")
    auth_service = services.get("auth_service")
    if not isinstance(auth_service, AuthService):
        raise RuntimeError("Platform auth service is not configured.")
    return DesktopApiRegistry(
        platform_runtime=PlatformRuntimeDesktopApi(
            platform_runtime_application_service=platform_runtime_application_service,
        ),
        platform_site=PlatformSiteDesktopApi(site_service=site_service),
        platform_department=PlatformDepartmentDesktopApi(
            department_service=department_service,
        ),
        platform_employee=PlatformEmployeeDesktopApi(
            employee_service=employee_service,
        ),
        platform_document=PlatformDocumentDesktopApi(
            document_service=document_service,
        ),
        platform_party=PlatformPartyDesktopApi(
            party_service=party_service,
        ),
        platform_user=PlatformUserDesktopApi(
            auth_service=auth_service,
        ),
    )


__all__ = ["DesktopApiRegistry", "build_desktop_api_registry"]

from __future__ import annotations

from typing import Any

from src.core.platform.api.desktop.history.activity.activity import PlatformActivityDesktopApi
from src.core.platform.api.desktop.master_data.org.models.organization import (
    OrganizationDto,
    OrganizationProvisionCommand,
    OrganizationUpdateCommand,
)
from src.core.platform.api.desktop.platform_runtime.runtime import PlatformRuntimeDesktopApi
from src.core.platform.api.desktop.models.common import DesktopApiResult
from src.ui_qml.platform.presenters.common.presenter_support_helpers import (
    bool_value,
    int_value,
    option_item,
    preview_error_result,
    string_value,
    tuple_of_strings,
)
from src.ui_qml.platform.view_models import (
    PlatformWorkspaceActionItemViewModel,
    PlatformWorkspaceActionListViewModel,
)

class PlatformOrganizationCatalogPresenter:
    def __init__(
        self,
        *,
        runtime_api: PlatformRuntimeDesktopApi | None = None,
        activity_api: PlatformActivityDesktopApi | None = None,
    ) -> None:
        self._runtime_api = runtime_api
        self._activity_api = activity_api

    def build_detail_context(self, organization_id: str) -> dict[str, Any]:
        """Real composed data for Organization Detail's Overview section:
        per-organization statistics (site/department/employee/document
        counts, one aggregate query each) and recent curated business
        activity scoped to this organization specifically -- never the
        caller's currently active organization, and never the raw
        compliance audit trail (see terminology-glossary.md)."""
        statistics = {"siteCount": 0, "departmentCount": 0, "employeeCount": 0, "documentCount": 0}
        if self._runtime_api is not None:
            result = self._runtime_api.get_organization_statistics(organization_id)
            if result.ok and result.data is not None:
                statistics = {
                    "siteCount": result.data.site_count,
                    "departmentCount": result.data.department_count,
                    "employeeCount": result.data.employee_count,
                    "documentCount": result.data.document_count,
                }
        recent_activity: list[dict[str, Any]] = []
        if self._activity_api is not None:
            recent_activity = self._activity_api.list_for_organization_overview(organization_id, limit=5)
        return {"statistics": statistics, "recentActivity": recent_activity}

    def build_audit_activity(self, organization_id: str, *, limit: int = 25) -> list[dict[str, Any]]:
        if self._activity_api is None:
            return []
        return self._activity_api.list_for_organization_overview(organization_id, limit=limit)

    def build_catalog_page(
        self,
        *,
        page: int = 1,
        page_size: int = 25,
        search: str = "",
    ) -> PlatformWorkspaceActionListViewModel:
        if self._runtime_api is None:
            return PlatformWorkspaceActionListViewModel(
                title="Organizations",
                subtitle="Organization records appear here once the platform runtime API is connected.",
                empty_state="Platform runtime API is not connected in this QML preview.",
                paginated=True,
                page=page,
                page_size=page_size,
            )

        result = self._runtime_api.list_organizations_page(
            page=page, page_size=page_size, search=search.strip() or None
        )
        if not result.ok or result.data is None:
            message = result.error.message if result.error is not None else "Unable to load organizations."
            return PlatformWorkspaceActionListViewModel(
                title="Organizations",
                subtitle=message,
                empty_state=message,
                paginated=True,
                page=page,
                page_size=page_size,
            )

        catalog_page = result.data
        return PlatformWorkspaceActionListViewModel(
            title="Organizations",
            subtitle="Install profiles and hosting boundaries across the enterprise.",
            empty_state="No organizations yet. Organizations will appear here once they are created.",
            no_results_state="No organizations match your current filters.",
            items=tuple(self._serialize_organization(row) for row in catalog_page.items),
            paginated=True,
            page=catalog_page.page,
            page_size=catalog_page.page_size,
            total_count=catalog_page.total,
            filtered_total=catalog_page.filtered_total,
        )

    def build_country_options(self) -> tuple[dict[str, str], ...]:
        if self._runtime_api is None:
            return ()
        result = self._runtime_api.list_countries()
        if not result.ok or result.data is None:
            return ()
        return tuple(
            option_item(label=country.name, value=country.code)
            for country in result.data
        )

    def build_module_options(self) -> tuple[dict[str, str], ...]:
        if self._runtime_api is None:
            return ()
        result = self._runtime_api.list_modules()
        if not result.ok or result.data is None:
            return ()
        return tuple(
            option_item(
                label=module.label,
                value=module.code,
                supporting_text=module.description,
            )
            for module in result.data
        )

    def suggest_code(self, payload: dict[str, Any]) -> str:
        """Suggest a unique organization code (ORG-<NAME>-0001 / ORG-<YEAR>-0001).

        Uniqueness is checked against existing organization codes; the backend
        still re-validates on save (ORGANIZATION_CODE_EXISTS).
        """
        from src.core.platform.common.code_generation import CodeGenerator

        existing: set[str] = set()
        if self._runtime_api is not None:
            result = self._runtime_api.list_organizations(enabled_only=None)
            if result.ok and result.data is not None:
                existing = {str(row.organization_code or "").upper() for row in result.data}
        name = string_value(payload, "displayName")
        return CodeGenerator().generate(
            "organization",
            exists=lambda code: code.upper() in existing,
            name=name or None,
            use_year=not bool(name),
        )

    def create_organization(self, payload: dict[str, Any]) -> DesktopApiResult[OrganizationDto]:
        if self._runtime_api is None:
            return preview_error_result("Platform runtime API is not connected in this QML preview.")
        return self._runtime_api.provision_organization(
            OrganizationProvisionCommand(
                organization_code=string_value(payload, "organizationCode"),
                display_name=string_value(payload, "displayName"),
                timezone_name=string_value(payload, "timezoneName", default="UTC"),
                base_currency=string_value(payload, "baseCurrency", default="USD").upper(),
                is_enabled=bool_value(payload, "isEnabled", default=True),
                initial_module_codes=tuple_of_strings(payload, "initialModuleCodes"),
                legal_name=string_value(payload, "legalName"),
                registration_number=string_value(payload, "registrationNumber"),
                tax_id=string_value(payload, "taxId"),
                address_line_1=string_value(payload, "addressLine1"),
                address_line_2=string_value(payload, "addressLine2"),
                postal_code=string_value(payload, "postalCode"),
                city=string_value(payload, "city"),
                state_region=string_value(payload, "stateRegion"),
                country_code=string_value(payload, "countryCode").upper(),
                email=string_value(payload, "email"),
                phone=string_value(payload, "phone"),
                website=string_value(payload, "website"),
            )
        )

    def update_organization(self, payload: dict[str, Any]) -> DesktopApiResult[OrganizationDto]:
        if self._runtime_api is None:
            return preview_error_result("Platform runtime API is not connected in this QML preview.")
        return self._runtime_api.update_organization(
            OrganizationUpdateCommand(
                organization_id=string_value(payload, "organizationId"),
                organization_code=string_value(payload, "organizationCode"),
                display_name=string_value(payload, "displayName"),
                timezone_name=string_value(payload, "timezoneName", default="UTC"),
                base_currency=string_value(payload, "baseCurrency", default="USD").upper(),
                is_enabled=bool_value(payload, "isEnabled", default=True),
                expected_version=int_value(payload, "expectedVersion"),
                legal_name=string_value(payload, "legalName"),
                registration_number=string_value(payload, "registrationNumber"),
                tax_id=string_value(payload, "taxId"),
                address_line_1=string_value(payload, "addressLine1"),
                address_line_2=string_value(payload, "addressLine2"),
                postal_code=string_value(payload, "postalCode"),
                city=string_value(payload, "city"),
                state_region=string_value(payload, "stateRegion"),
                country_code=string_value(payload, "countryCode").upper(),
                email=string_value(payload, "email"),
                phone=string_value(payload, "phone"),
                website=string_value(payload, "website"),
            )
        )

    def enable_organization(self, organization_id: str) -> DesktopApiResult[OrganizationDto]:
        if self._runtime_api is None:
            return preview_error_result("Platform runtime API is not connected in this QML preview.")
        return self._runtime_api.enable_organization(organization_id)

    @staticmethod
    def _serialize_organization(row: OrganizationDto) -> PlatformWorkspaceActionItemViewModel:
        return PlatformWorkspaceActionItemViewModel(
            id=row.id,
            title=row.display_name,
            status_label="Enabled" if row.is_enabled else "Disabled",
            subtitle=f"{row.organization_code} | {row.timezone_name}",
            supporting_text=f"Base currency: {row.base_currency}",
            meta_text=f"Version {row.version}",
            can_primary_action=True,
            can_secondary_action=not row.is_enabled,
            state={
                "id": row.id,
                "organizationId": row.id,
                "organizationCode": row.organization_code,
                "displayName": row.display_name,
                "timezoneName": row.timezone_name,
                "baseCurrency": row.base_currency,
                "isEnabled": row.is_enabled,
                "version": row.version,
                "legalName": row.legal_name,
                "registrationNumber": row.registration_number,
                "taxId": row.tax_id,
                "addressLine1": row.address_line_1,
                "addressLine2": row.address_line_2,
                "postalCode": row.postal_code,
                "city": row.city,
                "stateRegion": row.state_region,
                "countryCode": row.country_code,
                "email": row.email,
                "phone": row.phone,
                "website": row.website,
            },
        )

__all__ = ["PlatformOrganizationCatalogPresenter"]

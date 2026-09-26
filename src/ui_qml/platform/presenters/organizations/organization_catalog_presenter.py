from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from src.core.platform.api.desktop.history.activity.activity import (
    PlatformActivityDesktopApi,
)
from src.core.platform.api.desktop.history.activity.models.activity import (
    ActivityEntryDto,
)
from src.core.platform.api.desktop.master_data.org.models.organization import (
    OrganizationDto,
    OrganizationProvisionCommand,
    OrganizationUpdateCommand,
)
from src.core.platform.api.desktop.models.common import DesktopApiResult
from src.core.platform.api.desktop.platform_runtime.runtime import (
    PlatformRuntimeDesktopApi,
)
from src.core.platform.domain.master_data.org import (
    ORGANIZATION_STATUS_ACTIVE,
    ORGANIZATION_STATUS_ARCHIVED,
    ORGANIZATION_STATUS_INACTIVE,
)
from src.core.shared.reference_data import country_name_for_code
from src.ui_qml.platform.presenters.common.calendar_summary_support import (
    holiday_set_label as _holiday_set_label,
)
from src.ui_qml.platform.presenters.common.calendar_summary_support import (
    working_week_label as _working_week_label,
)
from src.ui_qml.platform.presenters.common.presenter_support_helpers import (
    int_value,
    option_item,
    preview_error_result,
    string_value,
    tuple_of_strings,
)
from src.ui_qml.platform.presenters.organizations.organization_activity_presenter import (
    ORGANIZATION_ACTIVITY_ENTITY_TYPES,
)
from src.ui_qml.platform.view_models import (
    PlatformWorkspaceActionItemViewModel,
    PlatformWorkspaceActionListViewModel,
)
from src.ui_qml.shared.models.activity_item import (
    ActivityItemViewModel,
    humanize_action,
    icon_key_for_entity_type,
    serialize_activity_items,
    tone_for_action,
)
from src.ui_qml.shared.models.currency_options import CURRENCY_OPTIONS

# StatusChip tone per lifecycle status -- explicit, presenter-owned mapping.
# QML never infers a tone from status text (see StatusChip.qml).
_ORGANIZATION_STATUS_TONE: dict[str, str] = {
    ORGANIZATION_STATUS_ACTIVE: "success",
    ORGANIZATION_STATUS_INACTIVE: "neutral",
    ORGANIZATION_STATUS_ARCHIVED: "neutral",
}

def _organization_status_label(status: str) -> dict[str, str]:
    return {"label": status.capitalize(), "tone": _ORGANIZATION_STATUS_TONE.get(status, "neutral")}


def _to_activity_item(entry: ActivityEntryDto) -> ActivityItemViewModel:
    return ActivityItemViewModel(
        id=entry.id,
        title=entry.human_message or humanize_action(entry.action),
        occurred_at=entry.timestamp,
        occurred_at_label=entry.timestamp.strftime("%Y-%m-%d %H:%M UTC") if entry.timestamp else "",
        icon_key=entry.icon or icon_key_for_entity_type(entry.entity_type),
        tone=tone_for_action(entry.action),
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
        counts, one aggregate query each) and the 5 most recent business
        activity items scoped to this organization -- never the caller's
        currently active organization, and never the raw compliance audit
        trail."""
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
        return {"statistics": statistics, "recentActivity": self.build_recent_activity(organization_id, limit=5)}

    def build_calendar_summary(self, organization_id: str) -> dict[str, Any]:
        """Read-only summary of the organization's one default calendar for
        Organization Overview/Inspector -- never a full calendar editor.
        Scoped to `organization_id` explicitly, so it is correct even when
        this is not the caller's currently active organization."""
        empty = {
            "hasCalendar": False,
            "calendarId": "",
            "calendarName": "",
            "workingWeekLabel": "No working days configured",
            "timeZone": "",
            "holidaySetLabel": "No holidays configured",
        }
        if self._runtime_api is None:
            return empty
        result = self._runtime_api.get_organization_calendar_summary(organization_id)
        if not result.ok or result.data is None or not result.data.has_calendar:
            return empty
        summary = result.data
        return {
            "hasCalendar": True,
            "calendarId": summary.calendar_id,
            "calendarName": summary.calendar_name,
            "workingWeekLabel": _working_week_label(tuple(summary.working_weekdays)),
            "timeZone": summary.timezone,
            "holidaySetLabel": _holiday_set_label(summary.locale, summary.holiday_count),
        }

    def build_recent_activity(self, organization_id: str, *, limit: int = 25) -> list[dict[str, Any]]:
        if self._activity_api is None:
            return []
        entries = self._activity_api.list_for_organization_overview(
            organization_id, limit=limit, entity_types=ORGANIZATION_ACTIVITY_ENTITY_TYPES
        )
        return serialize_activity_items(_to_activity_item(entry) for entry in entries)

    def build_catalog_page(
        self,
        *,
        page: int = 1,
        page_size: int = 25,
        search: str = "",
        status: str | None = None,
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
            page=page, page_size=page_size, search=search.strip() or None, status=status
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

    def build_timezone_options(self) -> tuple[dict[str, str], ...]:
        if self._runtime_api is None:
            return ()
        result = self._runtime_api.list_timezones()
        if not result.ok or result.data is None:
            return ()
        return tuple(
            option_item(label=timezone.name, value=timezone.name)
            for timezone in result.data
        )

    def build_currency_options(self) -> tuple[dict[str, str], ...]:
        """CURRENCY_OPTIONS is the same shared ISO 4217 reference list Financials
        already uses (src.ui_qml.shared.models.currency_options) -- no separate
        currency reference data lives here."""
        return tuple(CURRENCY_OPTIONS)

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
            result = self._runtime_api.list_organizations(status=None)
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

    def activate_organization(self, organization_id: str) -> DesktopApiResult[OrganizationDto]:
        if self._runtime_api is None:
            return preview_error_result("Platform runtime API is not connected in this QML preview.")
        return self._runtime_api.activate_organization(organization_id)

    def deactivate_organization(self, organization_id: str) -> DesktopApiResult[OrganizationDto]:
        if self._runtime_api is None:
            return preview_error_result("Platform runtime API is not connected in this QML preview.")
        return self._runtime_api.deactivate_organization(organization_id)

    def archive_organization(self, organization_id: str) -> DesktopApiResult[OrganizationDto]:
        if self._runtime_api is None:
            return preview_error_result("Platform runtime API is not connected in this QML preview.")
        return self._runtime_api.archive_organization(organization_id)

    def update_organization_currency(
        self, organization_id: str, base_currency: str
    ) -> DesktopApiResult[OrganizationDto]:
        """Narrow single-field update for the bulk currency action -- unlike
        update_organization() above, sends only organization_id + base_currency
        (every other OrganizationUpdateCommand field stays None/untouched),
        since a bulk action never has the rest of each selected organization's
        current form data to send."""
        if self._runtime_api is None:
            return preview_error_result("Platform runtime API is not connected in this QML preview.")
        return self._runtime_api.update_organization(
            OrganizationUpdateCommand(
                organization_id=organization_id,
                base_currency=base_currency.strip().upper(),
            )
        )

    def update_organization_timezone(
        self, organization_id: str, timezone_name: str
    ) -> DesktopApiResult[OrganizationDto]:
        if self._runtime_api is None:
            return preview_error_result("Platform runtime API is not connected in this QML preview.")
        return self._runtime_api.update_organization(
            OrganizationUpdateCommand(
                organization_id=organization_id,
                timezone_name=timezone_name.strip(),
            )
        )

    def license_module_for_organization(self, organization_id: str, module_code: str) -> DesktopApiResult[Any]:
        if self._runtime_api is None:
            return preview_error_result("Platform runtime API is not connected in this QML preview.")
        return self._runtime_api.license_module_for_organization(organization_id, module_code)

    def revoke_module_license_for_organization(
        self, organization_id: str, module_code: str
    ) -> DesktopApiResult[Any]:
        if self._runtime_api is None:
            return preview_error_result("Platform runtime API is not connected in this QML preview.")
        return self._runtime_api.revoke_module_license_for_organization(organization_id, module_code)


    def bulk_set_organization_status(
        self, organization_ids: Sequence[str], *, status: str
    ) -> DesktopApiResult[Any]:
        if self._runtime_api is None:
            return preview_error_result("Platform runtime API is not connected in this QML preview.")
        ids = tuple(organization_ids)
        if status == ORGANIZATION_STATUS_ACTIVE:
            return self._runtime_api.bulk_activate_organizations(ids)
        if status == ORGANIZATION_STATUS_ARCHIVED:
            return self._runtime_api.bulk_archive_organizations(ids)
        return self._runtime_api.bulk_deactivate_organizations(ids)

    def bulk_update_organization_currency(
        self, organization_ids: Sequence[str], base_currency: str
    ) -> DesktopApiResult[Any]:
        if self._runtime_api is None:
            return preview_error_result("Platform runtime API is not connected in this QML preview.")
        return self._runtime_api.bulk_update_organization_currency(
            tuple(organization_ids), base_currency.strip().upper()
        )

    def bulk_update_organization_timezone(
        self, organization_ids: Sequence[str], timezone_name: str
    ) -> DesktopApiResult[Any]:
        if self._runtime_api is None:
            return preview_error_result("Platform runtime API is not connected in this QML preview.")
        return self._runtime_api.bulk_update_organization_timezone(tuple(organization_ids), timezone_name.strip())

    def bulk_assign_modules(
        self, organization_ids: Sequence[str], module_codes: Sequence[str], *, grant: bool
    ) -> DesktopApiResult[Any]:
        if self._runtime_api is None:
            return preview_error_result("Platform runtime API is not connected in this QML preview.")
        pairs = tuple((org_id, module_code) for org_id in organization_ids for module_code in module_codes)
        return self._runtime_api.bulk_set_module_license(pairs, licensed=grant)

    @staticmethod
    def _serialize_organization(row: OrganizationDto) -> PlatformWorkspaceActionItemViewModel:
        country_name = country_name_for_code(row.country_code) or row.country_code
        location = ", ".join(part for part in (row.city, country_name) if part)
        return PlatformWorkspaceActionItemViewModel(
            id=row.id,
            title=row.display_name,
            status_label=_organization_status_label(row.status),
            subtitle=f"{row.organization_code} | {row.timezone_name}",
            supporting_text=f"Base currency: {row.base_currency}",
            meta_text=f"Version {row.version}",
            can_primary_action=True,
            can_secondary_action=row.status != ORGANIZATION_STATUS_ACTIVE,
            state={
                "id": row.id,
                "organizationId": row.id,
                "organizationCode": row.organization_code,
                "displayName": row.display_name,
                "timezoneName": row.timezone_name,
                "baseCurrency": row.base_currency,
                "status": row.status,
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
                "countryName": country_name,
                "location": location,
                "email": row.email,
                "phone": row.phone,
                "website": row.website,
            },
        )

__all__ = ["PlatformOrganizationCatalogPresenter"]

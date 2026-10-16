from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.core.platform.application.master_data.org.queries.organization_queries import (
        OrganizationCalendarSummary,
        OrganizationPage,
        OrganizationStatistics,
    )
    from src.core.platform.domain.master_data.org import Organization

from src.core.platform.application.master_data.org.dto.responses.organization import (
    OrganizationCalendarSummaryDto,
    OrganizationCatalogPageDto,
    OrganizationDto,
    OrganizationStatisticsDto,
)
from src.core.platform.domain.master_data.org import Organization


def serialize_organization(organization: Organization) -> OrganizationDto:
    return OrganizationDto(
        id=organization.id,
        organization_code=organization.organization_code,
        display_name=organization.display_name,
        timezone_name=organization.timezone_name,
        base_currency=organization.base_currency,
        status=organization.status,
        version=organization.version,
        legal_name=organization.legal_name,
        registration_number=organization.registration_number,
        tax_id=organization.tax_id,
        address_line_1=organization.address_line_1,
        address_line_2=organization.address_line_2,
        postal_code=organization.postal_code,
        city=organization.city,
        state_region=organization.state_region,
        country_code=organization.country_code,
        email=organization.email,
        phone=organization.phone,
        website=organization.website,
        tenant_id=organization.tenant_id,
    )


def serialize_organization_calendar_summary(summary: OrganizationCalendarSummary) -> OrganizationCalendarSummaryDto:
    return OrganizationCalendarSummaryDto(
        has_calendar=summary.has_calendar,
        calendar_id=summary.calendar_id,
        calendar_name=summary.calendar_name,
        timezone=summary.timezone,
        locale=summary.locale or "",
        working_weekdays=summary.working_weekdays,
        holiday_count=summary.holiday_count,
    )


def serialize_organization_statistics(statistics: OrganizationStatistics) -> OrganizationStatisticsDto:
    return OrganizationStatisticsDto(
        site_count=statistics.site_count,
        department_count=statistics.department_count,
        employee_count=statistics.employee_count,
        document_count=statistics.document_count,
    )


def serialize_organization_context(organization: Organization) -> OrganizationDto:
    return OrganizationDto(
        id=organization.id,
        organization_code=organization.organization_code,
        display_name=organization.display_name,
        timezone_name=organization.timezone_name,
        base_currency=organization.base_currency,
        status=organization.status,
        version=organization.version,
        tenant_id=organization.tenant_id,
    )


def serialize_organization_page(page: OrganizationPage) -> OrganizationCatalogPageDto:
    return OrganizationCatalogPageDto(
        items=tuple(serialize_organization(row) for row in page.items),
        total=page.total,
        filtered_total=page.filtered_total,
        page=page.page,
        page_size=page.page_size,
    )

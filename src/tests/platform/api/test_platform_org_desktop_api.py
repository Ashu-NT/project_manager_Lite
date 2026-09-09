from __future__ import annotations

from src.core.platform.api.desktop.master_data.department.department import PlatformDepartmentDesktopApi
from src.core.platform.api.desktop.master_data.department.models.department import (
    DepartmentCreateCommand,
    DepartmentUpdateCommand,
)
from src.core.platform.api.desktop.master_data.employee.employee import PlatformEmployeeDesktopApi
from src.core.platform.api.desktop.master_data.employee.models.employee import (
    EmployeeCreateCommand,
    EmployeeUpdateCommand,
)
from src.core.platform.api.desktop.master_data.site.models.site import (
    SiteCreateCommand,
    SiteUpdateCommand,
)
from src.core.platform.api.desktop.master_data.site.site import PlatformSiteDesktopApi
from src.application.runtime import build_desktop_api_registry


def _build_site_api(services) -> PlatformSiteDesktopApi:
    return PlatformSiteDesktopApi(site_service=services["site_service"])


def _build_department_api(services) -> PlatformDepartmentDesktopApi:
    return PlatformDepartmentDesktopApi(department_service=services["department_service"])


def _build_employee_api(services) -> PlatformEmployeeDesktopApi:
    return PlatformEmployeeDesktopApi(employee_service=services["employee_service"])


def test_platform_site_desktop_api_manages_site_dtos(services):
    api = _build_site_api(services)

    context_result = api.get_context()
    create_result = api.create_site(
        SiteCreateCommand(
            site_code="OPS",
            name="Operations Yard",
            city="Lagos",
            country="NG",
            currency_code="USD",
        )
    )

    assert context_result.ok is True
    assert context_result.data is not None
    assert context_result.data.display_name == "Default Organization"
    assert create_result.ok is True
    assert create_result.data is not None
    assert create_result.data.site_code == "OPS"
    assert create_result.data.name == "Operations Yard"
    assert create_result.data.city == "Lagos"

    update_result = api.update_site(
        SiteUpdateCommand(
            site_id=create_result.data.id,
            name="Operations Hub",
            is_active=False,
            expected_version=create_result.data.version,
        )
    )

    assert update_result.ok is True
    assert update_result.data is not None
    assert update_result.data.name == "Operations Hub"
    assert update_result.data.is_active is False
    assert update_result.data.status == "INACTIVE"

    list_result = api.list_sites(active_only=None)

    assert list_result.ok is True
    assert list_result.data is not None
    assert [site.site_code for site in list_result.data] == ["OPS"]


def test_platform_site_desktop_api_maps_site_validation_errors(services):
    api = _build_site_api(services)
    api.create_site(SiteCreateCommand(site_code="HQ", name="Headquarters"))

    duplicate_result = api.create_site(SiteCreateCommand(site_code="HQ", name="Second HQ"))

    assert duplicate_result.ok is False
    assert duplicate_result.data is None
    assert duplicate_result.error is not None
    assert duplicate_result.error.category == "validation"
    assert duplicate_result.error.code == "SITE_CODE_EXISTS"


def test_platform_department_desktop_api_manages_department_dtos(services):
    api = _build_department_api(services)
    site = services["site_service"].create_site(site_code="DEPT", name="Department Site")

    create_result = api.create_department(
        DepartmentCreateCommand(
            department_code="OPS",
            name="Operations",
            site_id=site.id,
            department_type="OPERATIONS",
        )
    )

    assert create_result.ok is True
    assert create_result.data is not None
    assert create_result.data.department_code == "OPS"

    update_result = api.update_department(
        DepartmentUpdateCommand(
            department_id=create_result.data.id,
            name="Operations Team",
            is_active=False,
            expected_version=create_result.data.version,
        )
    )
    assert update_result.ok is True
    assert update_result.data is not None
    assert update_result.data.name == "Operations Team"
    assert update_result.data.is_active is False


def test_platform_employee_desktop_api_manages_employee_dtos(services):
    site_api = _build_site_api(services)
    department_api = _build_department_api(services)
    employee_api = _build_employee_api(services)
    site_result = site_api.create_site(SiteCreateCommand(site_code="EMP", name="Employee Site"))
    assert site_result.data is not None
    department_result = department_api.create_department(
        DepartmentCreateCommand(
            department_code="PMO",
            name="PMO",
            site_id=site_result.data.id,
        )
    )
    assert department_result.data is not None

    create_result = employee_api.create_employee(
        EmployeeCreateCommand(
            employee_code="EMP-001",
            full_name="Alice Admin",
            department_id=department_result.data.id,
            site_id=site_result.data.id,
            title="Planner",
            employment_type="FULL_TIME",
            email="alice@example.com",
        )
    )

    assert create_result.ok is True
    assert create_result.data is not None
    assert create_result.data.department == "PMO"
    assert create_result.data.site_name == "Employee Site"

    update_result = employee_api.update_employee(
        EmployeeUpdateCommand(
            employee_id=create_result.data.id,
            full_name="Alice Smith",
            phone="+49-555-0101",
            email="",
            is_active=False,
            expected_version=create_result.data.version,
        )
    )

    assert update_result.ok is True
    assert update_result.data is not None
    assert update_result.data.full_name == "Alice Smith"
    assert update_result.data.phone == "+49-555-0101"
    assert update_result.data.email is None
    assert update_result.data.is_active is False


def test_build_desktop_api_registry_exposes_platform_master_data_adapters(services):
    registry = build_desktop_api_registry(services)

    result = registry.platform_site.list_sites(active_only=None)

    assert result.ok is True
    assert result.data == ()


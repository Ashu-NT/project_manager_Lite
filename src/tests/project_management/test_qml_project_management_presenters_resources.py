from types import SimpleNamespace

from src.ui_qml.modules.project_management.context import ProjectManagementWorkspaceCatalog
from src.core.modules.project_management.api.desktop import (
    build_project_management_resources_desktop_api,
)
from src.core.modules.project_management.domain.enums import CostType, WorkerType
from src.core.modules.project_management.contracts.reads.resources import (
    ResourceCatalogReadItem,
    ResourceCatalogReadPage,
    ResourceCatalogSummary,
)


class _FakeResourceService:
    def __init__(self, resources: list[SimpleNamespace] | None = None) -> None:
        self._resources = {resource.id: resource for resource in (resources or [])}

    def list_resources(self) -> list[SimpleNamespace]:
        return list(self._resources.values())

    def query_catalog_page(
        self,
        *,
        search_text="",
        active=None,
        category=None,
        page=1,
        page_size=25,
    ) -> ResourceCatalogReadPage:
        all_resources = list(self._resources.values())
        filtered = [
            resource
            for resource in all_resources
            if (active is None or resource.is_active is active)
            and (category is None or resource.cost_type == category)
            and (
                not search_text
                or search_text.casefold() in resource.name.casefold()
                or search_text.casefold() in resource.role.casefold()
            )
        ]
        offset = (page - 1) * page_size
        return ResourceCatalogReadPage(
            items=tuple(
                ResourceCatalogReadItem(resource=resource)
                for resource in filtered[offset:offset + page_size]
            ),
            filtered_total=len(filtered),
            page=page,
            page_size=page_size,
            summary=ResourceCatalogSummary(
                total=len(all_resources),
                active=sum(1 for resource in all_resources if resource.is_active),
                employees=sum(
                    1 for resource in all_resources
                    if resource.worker_type == WorkerType.EMPLOYEE
                ),
                external=sum(
                    1 for resource in all_resources
                    if resource.worker_type == WorkerType.EXTERNAL
                ),
                average_capacity=(
                    sum(resource.capacity_percent for resource in all_resources)
                    / len(all_resources)
                    if all_resources else 0.0
                ),
            ),
        )


class _FakeEmployeeService:
    def list_employees(self, *, active_only: bool | None = None) -> list[SimpleNamespace]:
        employees = [
            SimpleNamespace(
                id="emp-1",
                employee_code="EMP-001",
                full_name="Alex Taylor",
                title="Planner",
                department="Operations",
                site_name="Plant North",
                email="alex@example.com",
                phone="555-0100",
                is_active=True,
            ),
            SimpleNamespace(
                id="emp-2",
                employee_code="EMP-002",
                full_name="Jordan Blake",
                title="Supervisor",
                department="Maintenance",
                site_name="Plant South",
                email="jordan@example.com",
                phone="555-0101",
                is_active=False,
            ),
        ]
        if active_only is None:
            return employees
        return [e for e in employees if bool(e.is_active) == bool(active_only)]


def test_project_management_workspace_catalog_exposes_typed_resources_controller() -> None:
    resources_api = build_project_management_resources_desktop_api(
        resource_service=_FakeResourceService(
            [
                SimpleNamespace(
                    id="res-1",
                    name="Electrical Crew",
                    role="Lead Technician",
                    hourly_rate=95.0,
                    is_active=True,
                    cost_type=CostType.LABOR,
                    currency_code="EUR",
                    version=3,
                    capacity_percent=110.0,
                    address="Site Office",
                    contact="crew@example.com",
                    worker_type=WorkerType.EXTERNAL,
                    employee_id=None,
                ),
                SimpleNamespace(
                    id="res-2",
                    name="Alex Taylor",
                    role="Planner",
                    hourly_rate=80.0,
                    is_active=False,
                    cost_type=CostType.LABOR,
                    currency_code="USD",
                    version=2,
                    capacity_percent=100.0,
                    address="",
                    contact="alex@example.com",
                    worker_type=WorkerType.EMPLOYEE,
                    employee_id="emp-1",
                ),
            ]
        ),
        employee_service=_FakeEmployeeService(),
    )
    catalog = ProjectManagementWorkspaceCatalog(
        desktop_api_registry=SimpleNamespace(project_management_resources=resources_api)
    )

    controller = catalog.resourcesWorkspace

    assert controller.workspace["routeId"] == "project_management.resources"
    assert controller.overview["title"] == "Resources"
    assert controller.categoryOptions[1]["value"] == "LABOR"
    assert controller.employeeOptions[0]["context"] == "Operations | Plant North"
    assert controller.resources["items"][0]["title"] == "Electrical Crew"
    assert controller.selectedResource["title"] == "Electrical Crew"

    controller.setActiveFilter("inactive")

    assert controller.selectedActiveFilter == "inactive"
    assert [item["title"] for item in controller.resources["items"]] == ["Alex Taylor"]

    controller.setSearchText("crew")

    assert controller.resources["items"] == []
    assert controller.emptyState == "No resources match the current filters."

from __future__ import annotations

from dataclasses import fields
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from src.core.modules.project_management.api.desktop import (
    build_project_management_projects_desktop_api,
)
from src.core.modules.project_management.api.desktop.projects.commands.project_commands import (
    ProjectCreateCommand,
    ProjectUpdateCommand,
)
from src.core.modules.project_management.domain.financials.budget import BudgetStatus
from src.core.modules.project_management.domain.projects.project import Project
from src.core.modules.project_management.infrastructure.persistence.orm.project import ProjectORM
from src.core.platform.domain.security.auth.session import UserSessionPrincipal
from src.core.shared.events.domain_events import domain_events
from src.ui_qml.modules.project_management.controllers.common.workspace_controller_base import (
    ProjectManagementWorkspaceControllerBase,
)
from src.ui_qml.modules.project_management.controllers.projects.project_domain_event_binder import (
    bind_project_domain_events,
)
from src.ui_qml.modules.project_management.presenters.projects.projects_workspace_presenter import (
    ProjectProjectsWorkspacePresenter,
)


def _approve_budget(services, project_id: str, *amounts: str, currency: str = "GBP"):
    suffix = uuid4().hex[:8]
    cost_code = services["financial_configuration_service"].create_cost_code(
        code=f"R42-{suffix}",
        name=f"R4.2 {suffix}",
    )
    budget_service = services["budget_service"]
    budget = budget_service.create_budget(
        project_id,
        f"Approved {suffix}",
        currency_code=currency,
    )
    for index, amount in enumerate(amounts, start=1):
        budget_service.add_line(
            budget.id,
            cost_code_id=cost_code.id,
            description=f"Line {index}",
            amount=Decimal(amount),
            expected_budget_version=budget.row_version,
        )
        budget = budget_service.get_budget(budget.id)
    budget = budget_service.submit_budget(
        budget.id,
        submitted_by="r42-author",
        expected_version=budget.row_version,
    )
    budget_service.approve_budget(
        budget.id,
        approved_by="r42-approver",
        expected_version=budget.row_version,
    )
    return budget_service.get_budget(budget.id)


def _set_principal(
    services,
    *,
    permissions: set[str],
    project_access: dict[str, frozenset[str]] | None = None,
) -> None:
    session = services["user_session"]
    session.set_principal(
        UserSessionPrincipal(
            user_id="r42-reader",
            username="r42-reader",
            display_name="R4.2 Reader",
            role_names=frozenset({"viewer"}),
            permissions=frozenset(permissions),
            project_access=project_access or {},
            active_tenant_id=session.stored_active_tenant_id(),
            active_organization_id=session.stored_active_organization_id(),
        )
    )


def _desktop_api(services):
    return build_project_management_projects_desktop_api(
        project_service=services["project_service"],
        site_service=services["site_service"],
        department_service=services["department_service"],
    )


def test_approved_budget_projection_sums_lines_and_uses_budget_currency(services) -> None:
    project = services["project_service"].create_project(
        "Currency Authority",
        financial_currency_code="EUR",
    )
    _approve_budget(services, project.id, "90", "10", currency="GBP")

    catalog_item = services["project_service"].query_catalog_page().items[0]
    detail_item = services["project_service"].query_project_detail(project.id)
    catalog_dto = _desktop_api(services).list_project_page().items[0]
    detail_dto = _desktop_api(services).get_project(project.id)

    assert catalog_item.approved_budget == Decimal("100")
    assert catalog_item.approved_budget_currency == "GBP"
    assert detail_item is not None
    assert detail_item.approved_budget == catalog_item.approved_budget
    assert detail_item.approved_budget_currency == catalog_item.approved_budget_currency
    assert catalog_dto.approved_budget == "100"
    assert catalog_dto.approved_budget_label == "GBP 100.00"
    assert detail_dto is not None
    assert detail_dto.approved_budget == catalog_dto.approved_budget
    assert detail_dto.approved_budget_currency == catalog_dto.approved_budget_currency
    assert detail_dto.approved_budget_label == catalog_dto.approved_budget_label
    assert detail_dto.financial_currency_code == "EUR"

    presenter = ProjectProjectsWorkspacePresenter(desktop_api=_desktop_api(services))
    catalog_state = presenter.build_workspace_state()
    detail_state = presenter.build_project_detail_state(project_id=project.id)
    assert catalog_state.projects[0].state["approvedBudgetVisible"] is True
    assert catalog_state.projects[0].state["approvedBudgetLabel"] == "GBP 100.00"
    assert detail_state.selected_project_detail.state["approvedBudgetLabel"] == "GBP 100.00"
    assert "Approved Budget" in {
        field.label for field in detail_state.selected_project_detail.fields
    }


def test_project_read_without_finance_read_redacts_catalog_and_detail(services) -> None:
    project = services["project_service"].create_project(
        "Redacted Budget",
        financial_currency_code="EUR",
    )
    _approve_budget(services, project.id, "777", currency="GBP")
    _set_principal(services, permissions={"project.read"})

    page = services["project_service"].query_catalog_page()
    detail = services["project_service"].query_project_detail(project.id)
    page_dto = _desktop_api(services).list_project_page()
    detail_dto = _desktop_api(services).get_project(project.id)

    assert page.approved_budget_visible is False
    assert page.items[0].approved_budget is None
    assert page.items[0].approved_budget_currency == ""
    assert page.items[0].approved_budget_visible is False
    assert detail is not None
    assert detail.approved_budget is None
    assert detail.approved_budget_currency == ""
    assert detail.approved_budget_visible is False
    assert page_dto.approved_budget_visible is False
    assert page_dto.items[0].approved_budget is None
    assert page_dto.items[0].approved_budget_label == ""
    assert page_dto.items[0].approved_budget_currency == ""
    assert detail_dto is not None
    assert detail_dto.approved_budget is None
    assert detail_dto.approved_budget_label == ""
    assert detail_dto.approved_budget_currency == ""
    assert detail_dto.approved_budget_visible is False

    presenter = ProjectProjectsWorkspacePresenter(desktop_api=_desktop_api(services))
    catalog_state = presenter.build_workspace_state()
    detail_state = presenter.build_project_detail_state(project_id=project.id)
    catalog_record = catalog_state.projects[0]
    assert catalog_record.state["approvedBudgetVisible"] is False
    assert catalog_record.state["approvedBudgetLabel"] == ""
    assert "Approved budget:" not in catalog_record.supporting_text
    assert detail_state.selected_project_detail.state["approvedBudgetVisible"] is False
    assert "Approved Budget" not in {
        field.label for field in detail_state.selected_project_detail.fields
    }


def test_project_scoped_finance_access_redacts_only_unauthorized_project(services) -> None:
    project_a = services["project_service"].create_project("Scoped Finance A")
    project_b = services["project_service"].create_project("Scoped Finance B")
    _approve_budget(services, project_a.id, "100", currency="USD")
    _approve_budget(services, project_b.id, "900", currency="CAD")
    _set_principal(
        services,
        permissions={"project.read", "finance.read"},
        project_access={
            project_a.id: frozenset({"project.read", "finance.read"}),
            project_b.id: frozenset({"project.read"}),
        },
    )

    page = services["project_service"].query_catalog_page(page_size=25)
    by_id = {item.project.id: item for item in page.items}

    assert page.approved_budget_visible is True
    assert by_id[project_a.id].approved_budget == Decimal("100")
    assert by_id[project_a.id].approved_budget_currency == "USD"
    assert by_id[project_a.id].approved_budget_visible is True
    assert by_id[project_b.id].approved_budget is None
    assert by_id[project_b.id].approved_budget_currency == ""
    assert by_id[project_b.id].approved_budget_visible is False
    assert services["project_service"].query_project_detail(project_b.id).approved_budget is None


def test_approved_budget_sort_is_numeric_stable_and_cross_page(services) -> None:
    values = ("9", "100", "1000", None, "100")
    projects = []
    for index, amount in enumerate(values):
        project = services["project_service"].create_project(f"Budget Sort {index}")
        projects.append(project)
        if amount is not None:
            _approve_budget(services, project.id, amount, currency="USD")

    ascending = [
        item
        for page in (1, 2, 3)
        for item in services["project_service"].query_catalog_page(
            sort_key="approvedBudgetLabel",
            sort_direction="asc",
            page=page,
            page_size=2,
        ).items
    ]
    descending = [
        item
        for page in (1, 2, 3)
        for item in services["project_service"].query_catalog_page(
            sort_key="approvedBudgetLabel",
            sort_direction="desc",
            page=page,
            page_size=2,
        ).items
    ]

    assert [item.approved_budget for item in ascending if item.approved_budget is not None] == [
        Decimal("9"),
        Decimal("100"),
        Decimal("100"),
        Decimal("1000"),
    ]
    assert [item.approved_budget for item in descending if item.approved_budget is not None] == [
        Decimal("1000"),
        Decimal("100"),
        Decimal("100"),
        Decimal("9"),
    ]
    assert {item.project.id for item in ascending} == {project.id for project in projects}
    assert [
        item.project.id for item in ascending if item.approved_budget == Decimal("100")
    ] == sorted(
        item.project.id for item in ascending if item.approved_budget == Decimal("100")
    )


def test_only_currently_approved_budget_is_projected(services) -> None:
    project = services["project_service"].create_project("Budget Lifecycle")
    assert services["project_service"].query_project_detail(project.id).approved_budget is None

    first = _approve_budget(services, project.id, "10", currency="USD")
    assert services["project_service"].query_project_detail(project.id).approved_budget == Decimal("10")

    successor = _approve_budget(services, project.id, "25", currency="CAD")
    assert services["budget_service"].get_budget(first.id).status is BudgetStatus.SUPERSEDED
    current = services["project_service"].query_project_detail(project.id)
    assert current.approved_budget == Decimal("25")
    assert current.approved_budget_currency == "CAD"

    services["budget_service"].close_budget(
        successor.id,
        closed_by="r42-closer",
        expected_version=successor.row_version,
    )
    closed = _desktop_api(services).get_project(project.id)
    assert closed is not None
    assert closed.approved_budget is None
    assert closed.approved_budget_label == "No approved budget"
    assert closed.approved_budget_currency == ""


def test_single_project_reader_enforces_tenant_and_organization_scope(services) -> None:
    project = services["project_service"].create_project("Scoped Detail")
    _approve_budget(services, project.id, "333", currency="USD")
    session = services["user_session"]
    reader = services["project_service"]._project_catalog_reader

    assert reader.read_one(
        tenant_id=session.stored_active_tenant_id(),
        organization_id=session.stored_active_organization_id(),
        project_id=project.id,
        include_approved_budget=True,
    ) is not None
    assert reader.read_one(
        tenant_id="another-tenant",
        organization_id=session.stored_active_organization_id(),
        project_id=project.id,
        include_approved_budget=True,
    ) is None
    assert reader.read_one(
        tenant_id=session.stored_active_tenant_id(),
        organization_id="another-organization",
        project_id=project.id,
        include_approved_budget=True,
    ) is None


class _RefreshProbe(ProjectManagementWorkspaceControllerBase):
    def __init__(self) -> None:
        super().__init__()
        self.refresh_count = 0
        self.selected_project_id = "project-kept"
        bind_project_domain_events(self)

    def refresh(self) -> None:
        self.refresh_count += 1


def test_project_budget_event_uses_existing_queued_refresh_behavior() -> None:
    controller = _RefreshProbe()
    controller._set_is_busy(True)

    domain_events.budgets_changed.emit("project-kept")

    assert controller.refresh_count == 0
    assert controller._pending_domain_refresh is True
    assert controller.selected_project_id == "project-kept"

    controller._set_is_busy(False)

    assert controller.refresh_count == 1
    assert controller._pending_domain_refresh is False
    assert controller.selected_project_id == "project-kept"


def test_qml_budget_surfaces_are_deny_safe_and_sortable() -> None:
    root = Path("src/ui_qml/modules/project_management/qml/workspaces/projects")
    columns = (root / "ProjectsColumnConfig.js").read_text(encoding="utf-8")
    state = (root / "ProjectsWorkspaceState.qml").read_text(encoding="utf-8")
    page = (root / "ProjectsWorkspacePage.qml").read_text(encoding="utf-8")
    overview = (root / "sections/ProjectsOverviewSection.qml").read_text(encoding="utf-8")

    assert '"key": "approvedBudgetLabel"' in columns
    assert '"sortable": true' in columns
    assert "baseColumns(root.approvedBudgetVisible)" in state
    assert "s.approvedBudgetVisible === true" in page
    assert "approvedBudgetVisible === true" in overview
    assert 'root._sv("approvedBudgetCurrency")' in overview


def test_project_write_model_and_editor_remain_budget_free() -> None:
    forbidden = {"approved_budget", "planned_budget"}
    assert forbidden.isdisjoint({field.name for field in fields(Project)})
    assert forbidden.isdisjoint(ProjectORM.__table__.columns.keys())
    assert forbidden.isdisjoint({field.name for field in fields(ProjectCreateCommand)})
    assert forbidden.isdisjoint({field.name for field in fields(ProjectUpdateCommand)})

    editor = Path(
        "src/ui_qml/modules/project_management/qml/workspaces/projects/dialogs/ProjectEditorDialog.qml"
    ).read_text(encoding="utf-8")
    assert "approvedBudget" not in editor
    assert "plannedBudget" not in editor

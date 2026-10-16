"""One application mapping for domain-bearing reads; no desktop result clones."""
from dataclasses import FrozenInstanceError
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from src.core.modules.project_management.api.desktop.register.api import ProjectManagementRegisterDesktopApi
from src.core.modules.project_management.api.desktop.dashboard.api import ProjectManagementDashboardDesktopApi
from src.core.modules.project_management.application.risk.mappers.entries import map_register_catalog
from src.core.modules.project_management.application.portfolio.mappers.scenarios import map_scenario
from src.core.modules.project_management.contracts.reads.register.models import RegisterCatalogReadPage, RegisterCatalogReadItem
from src.core.modules.project_management.domain.risk.register import RegisterEntry
from src.core.modules.project_management.domain.portfolio import PortfolioScenario
from src.ui_qml.modules.project_management.presenters.register.entry_mapper import build_entry_state


def test_register_overdue_is_authored_as_of_read_date_not_presenter_clock():
    entry = RegisterEntry.create("p1", title="Risk", due_date=date(2020, 2, 2))
    result = map_register_catalog(
        RegisterCatalogReadPage(items=(RegisterCatalogReadItem(entry, "Project"),)),
        as_of=date(2020, 1, 1),
    )
    assert result.items[0].is_overdue is False
    assert build_entry_state(result.items[0])["isOverdue"] is False
    entry.title = "Changed domain"
    assert result.items[0].title == "Risk"
    with pytest.raises(FrozenInstanceError):
        result.items[0].title = "Changed response"


def test_register_api_returns_application_page_by_identity():
    result = map_register_catalog(RegisterCatalogReadPage(), as_of=date(2020, 1, 1))
    api = ProjectManagementRegisterDesktopApi(
        register_query=SimpleNamespace(query_catalog_page=lambda **kwargs: result),
    )
    assert api.list_entry_page() is result


@pytest.mark.parametrize("budget", [None, Decimal("0.00"), Decimal("12.3400")])
def test_scenario_mapping_preserves_optional_decimal_and_copies_selection(budget):
    scenario = PortfolioScenario.create(
        organization_id="org", name="Scenario", budget_limit=budget, project_ids=("p1",),
    )
    result = map_scenario(scenario)
    assert result.budget_limit is budget
    assert result.project_ids == ("p1",)
    scenario.project_ids.append("p2")
    assert result.project_ids == ("p1",)


def test_dashboard_delayed_page_reuses_application_result_by_identity():
    result = SimpleNamespace(items=(), filtered_total=0, page=2, page_size=25)
    api = ProjectManagementDashboardDesktopApi(
        task_workspace_query=SimpleNamespace(query_workspace_page=lambda **kwargs: result),
    )
    assert api.list_delayed_tasks_page(page=2) is result

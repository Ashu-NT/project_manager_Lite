from __future__ import annotations

from datetime import date, timedelta

from src.core.modules.project_management.api.desktop.financials import (
    ProjectManagementFinancialsDesktopApi,
)
from src.core.modules.project_management.contracts.reads.financials.models.finance_lookup_facts import (
    FinanceLookupQuery,
)


def test_project_lookup_is_bounded_searchable_and_visibility_filtered(services) -> None:
    prefix = "R6B-LKP-PROJECT"
    projects = [
        services["project_service"].create_project(
            f"{prefix} {index:02d}", financial_currency_code="XAF"
        )
        for index in range(6)
    ]
    desktop = ProjectManagementFinancialsDesktopApi(
        finance_workspace_query=services["finance_workspace_query"]
    )

    first = desktop.search_manual_actual_projects(
        search=prefix, page=1, page_size=2
    )
    second = desktop.search_manual_actual_projects(
        search=prefix, page=2, page_size=2
    )

    assert first.total == 6
    assert len(first.items) == 2
    assert first.has_more is True
    assert len(second.items) == 2
    assert {item.value for item in first.items}.isdisjoint(
        {item.value for item in second.items}
    )

    scope = services["tenant_context_service"].require_active_scope_ids(
        operation_label="test Finance project lookup visibility"
    )
    reader = services["finance_workspace_query"]._lookup_reader
    visible = reader.search_projects(
        tenant_id=scope.tenant_id,
        organization_id=scope.organization_id,
        allowed_project_ids=(projects[-1].id,),
        require_active_finance_profile=True,
        request=FinanceLookupQuery(search=prefix, page=1, page_size=25),
    )
    assert [item.id for item in visible.items] == [projects[-1].id]
    assert reader.search_projects(
        tenant_id="foreign-tenant",
        organization_id=scope.organization_id,
        allowed_project_ids=None,
        require_active_finance_profile=True,
        request=FinanceLookupQuery(search=prefix),
    ).total == 0


def test_task_lookup_is_project_dependent_paged_and_resolvable(services) -> None:
    project = services["project_service"].create_project(
        "R6B Lookup Tasks", financial_currency_code="XAF"
    )
    other = services["project_service"].create_project(
        "R6B Lookup Other Tasks", financial_currency_code="XAF"
    )
    tasks = [
        services["task_service"].create_task(project.id, f"Lookup Task {index:02d}")
        for index in range(5)
    ]
    services["task_service"].create_task(other.id, "Lookup Task foreign")
    desktop = ProjectManagementFinancialsDesktopApi(
        finance_workspace_query=services["finance_workspace_query"]
    )

    page = desktop.search_manual_actual_tasks(
        project.id, search="Lookup Task", page=2, page_size=2
    )
    resolved = desktop.resolve_manual_actual_task(project.id, tasks[-1].id)

    assert page.total == 5
    assert page.page == 2
    assert len(page.items) == 2
    assert all(item.value != tasks[-1].id for item in page.items)
    assert resolved is not None
    assert resolved.value == tasks[-1].id
    assert desktop.resolve_manual_actual_task(project.id, "missing-task") is None


def test_cost_code_lookup_preserves_restriction_and_effective_date_policy(services) -> None:
    project = services["project_service"].create_project(
        "R6B Lookup Cost Codes", financial_currency_code="XAF"
    )
    configuration = services["financial_configuration_service"]
    profile = configuration.get_profile(project.id)
    configuration.configure_profile(
        project.id,
        expected_version=profile.version,
        cost_code_policy="restricted",
    )
    allowed = configuration.create_cost_code(
        code="R6B-LKP-ALLOW",
        name="Allowed",
        available_to_project_id=project.id,
    )
    configuration.create_cost_code(
        code="R6B-LKP-GLOBAL",
        name="Not restricted to project",
    )
    configuration.create_cost_code(
        code="R6B-LKP-EXPIRED",
        name="Expired",
        available_to_project_id=project.id,
        effective_to=date.today() - timedelta(days=1),
    )
    desktop = ProjectManagementFinancialsDesktopApi(
        finance_workspace_query=services["finance_workspace_query"]
    )

    page = desktop.search_manual_actual_cost_codes(
        project.id,
        search="R6B-LKP",
        page=1,
        page_size=2,
        effective_on=date.today(),
    )
    resolved = desktop.resolve_manual_actual_cost_code(
        project.id, allowed.id, effective_on=date.today()
    )

    assert page.total == 1
    assert [item.value for item in page.items] == [allowed.id]
    assert resolved is not None
    assert resolved.value == allowed.id


def test_manual_actual_defaults_and_selected_ids_do_not_require_full_lists(services) -> None:
    project = services["project_service"].create_project(
        "R6B Lookup Defaults", financial_currency_code="XAF"
    )
    desktop = ProjectManagementFinancialsDesktopApi(
        finance_workspace_query=services["finance_workspace_query"]
    )

    defaults = desktop.get_manual_actual_defaults(project.id)
    selected = desktop.resolve_manual_actual_project(project.id)

    assert defaults.currency_code == "XAF"
    assert selected is not None
    assert selected.value == project.id
    assert not hasattr(desktop, "list_projects")
    assert not hasattr(desktop, "list_tasks")
    assert not hasattr(desktop, "get_manual_actual_options")

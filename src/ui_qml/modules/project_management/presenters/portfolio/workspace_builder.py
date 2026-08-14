from __future__ import annotations

from time import perf_counter

from src.core.modules.project_management.api.desktop import (
    ProjectManagementPortfolioDesktopApi,
)
from src.ui_qml.modules.project_management.view_models.portfolio import (
    PortfolioCollectionViewModel,
    PortfolioPagedCollectionViewModel,
    PortfolioSelectorOptionViewModel,
    PortfolioWorkspaceViewModel,
)

from .action_mapper import to_recent_action_record
from .capacity_pool_builder import build_capacity_pool_view_model
from .comparison_builder import build_comparison_summary
from .dependency_mapper import to_dependency_record
from .evaluation_builder import build_evaluation_summary
from .filtering import build_empty_state, normalize_filter
from .heatmap_mapper import to_heatmap_record
from .intake_mapper import to_intake_record
from .overview_builder import build_overview
from .scenario_mapper import to_scenario_record
from .selection import resolve_compare_id, resolve_selected_id
from .template_mapper import to_template_record
from .performance_logging import log_build_complete

_ACTIVE_TABS = (
    "executive",
    "heatmap",
    "intake",
    "scenarios",
    "capacity",
    "dependencies",
)


def build_workspace_state(
    desktop_api: ProjectManagementPortfolioDesktopApi,
    *,
    active_tab: str = "executive",
    intake_status_filter: str = "all",
    intake_search_text: str = "",
    intake_page: int = 1,
    intake_page_size: int = 25,
    intake_sort_key: str = "updatedAt",
    intake_sort_direction: str = "desc",
    heatmap_search_text: str = "",
    heatmap_status_filter: str | None = None,
    heatmap_page: int = 1,
    heatmap_page_size: int = 25,
    heatmap_sort_key: str = "projectName",
    heatmap_sort_direction: str = "asc",
    dependencies_search_text: str = "",
    dependencies_page: int = 1,
    dependencies_page_size: int = 25,
    dependencies_sort_key: str = "updatedAt",
    dependencies_sort_direction: str = "desc",
    selected_scenario_id: str | None = None,
    base_compare_scenario_id: str | None = None,
    compare_scenario_id: str | None = None,
) -> PortfolioWorkspaceViewModel:
    started = perf_counter()
    normalized_active_tab = active_tab if active_tab in _ACTIVE_TABS else "executive"

    templates = desktop_api.list_templates()
    scenarios = desktop_api.list_scenarios()
    executive_snapshot = desktop_api.get_executive_snapshot()
    recent_actions = desktop_api.list_recent_actions(limit=12)

    intake_status_options = (
        PortfolioSelectorOptionViewModel(value="all", label="All statuses"),
        *(
            PortfolioSelectorOptionViewModel(value=option.value, label=option.label)
            for option in desktop_api.list_intake_statuses()
        ),
    )
    normalized_intake_status_filter = normalize_filter(
        intake_status_filter,
        intake_status_options,
        default_value="all",
    )
    intake_page_result = desktop_api.list_intake_items_page(
        status=(normalized_intake_status_filter if normalized_intake_status_filter != "all" else None),
        search_text=intake_search_text,
        page=intake_page,
        page_size=intake_page_size,
        sort_key=intake_sort_key,
        sort_direction=intake_sort_direction,
    )
    heatmap_page_result = desktop_api.list_heatmap_page(
        search_text=heatmap_search_text,
        status=heatmap_status_filter,
        page=heatmap_page,
        page_size=heatmap_page_size,
        sort_key=heatmap_sort_key,
        sort_direction=heatmap_sort_direction,
    )
    dependencies_page_result = desktop_api.list_dependencies_page(
        search_text=dependencies_search_text,
        page=dependencies_page,
        page_size=dependencies_page_size,
        sort_key=dependencies_sort_key,
        sort_direction=dependencies_sort_direction,
    )

    template_options = tuple(
        PortfolioSelectorOptionViewModel(value=option.id, label=option.name)
        for option in templates
    )
    project_options = tuple(
        PortfolioSelectorOptionViewModel(value=option.value, label=option.label)
        for option in desktop_api.list_projects()
    )
    scenario_options = tuple(
        PortfolioSelectorOptionViewModel(value=option.id, label=option.name)
        for option in scenarios
    )
    dependency_type_options = tuple(
        PortfolioSelectorOptionViewModel(value=option.value, label=option.label)
        for option in desktop_api.list_dependency_types()
    )
    resolved_scenario_id = resolve_selected_id(selected_scenario_id, scenarios)
    resolved_base_compare_id = resolve_selected_id(
        base_compare_scenario_id,
        scenarios,
        preferred_fallback_index=0,
    )
    resolved_compare_scenario_id = resolve_compare_id(
        compare_scenario_id,
        scenarios,
        disallowed_id=resolved_base_compare_id,
    )
    active_template = next(
        (template for template in templates if template.is_active),
        None,
    )
    empty_state = build_empty_state(
        intake_total=intake_page_result.total,
        intake_status_filter=normalized_intake_status_filter,
        templates=templates,
        scenarios=scenarios,
    )
    log_build_complete(
        started,
        intake_count=intake_page_result.total,
        filtered_intake_count=len(intake_page_result.items),
        template_count=len(templates),
        scenario_count=len(scenarios),
        heatmap_count=heatmap_page_result.total,
        dependency_count=dependencies_page_result.total,
        filter_value=normalized_intake_status_filter,
        scenario_id=resolved_scenario_id,
    )
    return PortfolioWorkspaceViewModel(
        active_tab=normalized_active_tab,
        overview=build_overview(
            intake_total=intake_page_result.total,
            scenario_count=len(scenarios),
            hot_projects=executive_snapshot.hot_project_count,
            dependency_count=executive_snapshot.dependency_count,
            active_template=active_template,
        ),
        intake_status_options=intake_status_options,
        template_options=template_options,
        project_options=project_options,
        scenario_options=scenario_options,
        dependency_type_options=dependency_type_options,
        selected_intake_status_filter=normalized_intake_status_filter,
        selected_scenario_id=resolved_scenario_id,
        selected_base_scenario_id=resolved_base_compare_id,
        selected_compare_scenario_id=resolved_compare_scenario_id,
        intake_items=PortfolioPagedCollectionViewModel(
            title="Portfolio Intake",
            subtitle="Capture proposed work, budgets, and capacity demand before it becomes committed project scope.",
            empty_state=(
                "No intake items match the current filter."
                if intake_page_result.total == 0 and normalized_intake_status_filter != "all"
                else "No intake items are available yet."
            ),
            items=tuple(to_intake_record(item) for item in intake_page_result.items),
            total=intake_page_result.total,
            page=intake_page_result.page,
            page_size=intake_page_result.page_size,
            sort_key=intake_page_result.sort_key,
            sort_direction=intake_page_result.sort_direction,
            search_text=intake_page_result.search_text,
        ),
        templates=PortfolioCollectionViewModel(
            title="Scoring Templates",
            subtitle="Keep one active scoring model for intake decisions and swap it only when governance rules change.",
            empty_state="No scoring templates are available yet.",
            items=tuple(to_template_record(item) for item in templates),
        ),
        scenarios=PortfolioCollectionViewModel(
            title="Scenario Library",
            subtitle="Review saved what-if portfolios and compare their budget, capacity, and intake impact.",
            empty_state="No portfolio scenarios are available yet.",
            items=tuple(to_scenario_record(item) for item in scenarios),
        ),
        evaluation=build_evaluation_summary(desktop_api, resolved_scenario_id),
        comparison=build_comparison_summary(
            desktop_api,
            base_scenario_id=resolved_base_compare_id,
            compare_scenario_id=resolved_compare_scenario_id,
        ),
        heatmap=PortfolioPagedCollectionViewModel(
            title="Portfolio Heatmap",
            subtitle="Cross-project delivery pressure across the accessible PM portfolio.",
            empty_state="No heatmap rows are available yet.",
            items=tuple(to_heatmap_record(item) for item in heatmap_page_result.items),
            total=heatmap_page_result.total,
            page=heatmap_page_result.page,
            page_size=heatmap_page_result.page_size,
            sort_key=heatmap_page_result.sort_key,
            sort_direction=heatmap_page_result.sort_direction,
            search_text=heatmap_page_result.search_text,
        ),
        dependencies=PortfolioPagedCollectionViewModel(
            title="Cross-project Dependencies",
            subtitle="Shared delivery links that shape sequencing across project boundaries.",
            empty_state="No cross-project dependencies are available yet.",
            items=tuple(to_dependency_record(item) for item in dependencies_page_result.items),
            total=dependencies_page_result.total,
            page=dependencies_page_result.page,
            page_size=dependencies_page_result.page_size,
            sort_key=dependencies_page_result.sort_key,
            sort_direction=dependencies_page_result.sort_direction,
            search_text=dependencies_page_result.search_text,
        ),
        recent_actions=PortfolioCollectionViewModel(
            title="Recent Actions",
            subtitle="The latest project, task, baseline, approval, timesheet, and portfolio events worth executive review.",
            empty_state="No recent PM actions are available yet.",
            items=tuple(to_recent_action_record(item) for item in recent_actions),
        ),
        capacity_pool=build_capacity_pool_view_model(desktop_api),
        top_at_risk_projects=PortfolioCollectionViewModel(
            title="Top At-Risk Projects",
            subtitle="Ranked across the complete accessible portfolio, not the current Heatmap page.",
            empty_state="No projects currently show elevated delivery pressure.",
            items=tuple(to_heatmap_record(item) for item in executive_snapshot.top_at_risk_projects),
        ),
        hot_project_count=executive_snapshot.hot_project_count,
        dependency_count=executive_snapshot.dependency_count,
        active_template_summary=(
            f"Active template: {active_template.name}. {active_template.weight_summary}"
            if active_template
            else "No active scoring template."
        ),
        empty_state=empty_state,
    )

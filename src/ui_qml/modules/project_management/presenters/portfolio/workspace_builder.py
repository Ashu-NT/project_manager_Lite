from __future__ import annotations

from time import perf_counter

from src.core.modules.project_management.api.desktop import (
    ProjectManagementPortfolioDesktopApi,
)
from src.ui_qml.modules.project_management.view_models.portfolio import (
    PortfolioCollectionViewModel,
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
from .utils import log_build_complete


def build_workspace_state(
    desktop_api: ProjectManagementPortfolioDesktopApi,
    *,
    intake_status_filter: str = "all",
    selected_scenario_id: str | None = None,
    base_compare_scenario_id: str | None = None,
    compare_scenario_id: str | None = None,
) -> PortfolioWorkspaceViewModel:
    started = perf_counter()
    templates = desktop_api.list_templates()
    intake_items = desktop_api.list_intake_items()
    scenarios = desktop_api.list_scenarios()
    heatmap = desktop_api.list_heatmap()
    dependencies = desktop_api.list_dependencies()
    recent_actions = desktop_api.list_recent_actions(limit=12)
    intake_status_options = (
        PortfolioSelectorOptionViewModel(value="all", label="All statuses"),
        *(
            PortfolioSelectorOptionViewModel(value=option.value, label=option.label)
            for option in desktop_api.list_intake_statuses()
        ),
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
    normalized_intake_status_filter = normalize_filter(
        intake_status_filter,
        intake_status_options,
        default_value="all",
    )
    filtered_intake_items = tuple(
        item
        for item in intake_items
        if normalized_intake_status_filter == "all"
        or item.status == normalized_intake_status_filter
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
    hot_projects = sum(1 for row in heatmap if row.pressure_label == "Hot")
    empty_state = build_empty_state(
        filtered_intake_items=filtered_intake_items,
        all_intake_items=intake_items,
        intake_status_filter=normalized_intake_status_filter,
        templates=templates,
        scenarios=scenarios,
    )
    log_build_complete(
        started,
        intake_count=len(intake_items),
        filtered_intake_count=len(filtered_intake_items),
        template_count=len(templates),
        scenario_count=len(scenarios),
        heatmap_count=len(heatmap),
        dependency_count=len(dependencies),
        filter_value=normalized_intake_status_filter,
        scenario_id=resolved_scenario_id,
    )
    return PortfolioWorkspaceViewModel(
        overview=build_overview(
            filtered_intake_items=filtered_intake_items,
            intake_items=intake_items,
            scenarios=scenarios,
            hot_projects=hot_projects,
            dependencies=dependencies,
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
        intake_items=PortfolioCollectionViewModel(
            title="Portfolio Intake",
            subtitle="Capture proposed work, budgets, and capacity demand before it becomes committed project scope.",
            empty_state=(
                "No intake items match the current filter."
                if intake_items and not filtered_intake_items
                else "No intake items are available yet."
            ),
            items=tuple(to_intake_record(item) for item in filtered_intake_items),
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
        heatmap=PortfolioCollectionViewModel(
            title="Portfolio Heatmap",
            subtitle="Cross-project delivery pressure across the accessible PM portfolio.",
            empty_state="No heatmap rows are available yet.",
            items=tuple(to_heatmap_record(item) for item in heatmap),
        ),
        dependencies=PortfolioCollectionViewModel(
            title="Cross-project Dependencies",
            subtitle="Shared delivery links that shape sequencing across project boundaries.",
            empty_state="No cross-project dependencies are available yet.",
            items=tuple(to_dependency_record(item) for item in dependencies),
        ),
        recent_actions=PortfolioCollectionViewModel(
            title="Recent Actions",
            subtitle="The latest project, task, baseline, approval, timesheet, and portfolio events worth executive review.",
            empty_state="No recent PM actions are available yet.",
            items=tuple(to_recent_action_record(item) for item in recent_actions),
        ),
        capacity_pool=build_capacity_pool_view_model(desktop_api),
        active_template_summary=(
            f"Active template: {active_template.name}. {active_template.weight_summary}"
            if active_template
            else "No active scoring template."
        ),
        empty_state=empty_state,
    )

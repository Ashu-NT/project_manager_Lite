from datetime import date, datetime, timedelta
from types import SimpleNamespace

from src.core.modules.project_management.api.desktop import (
    build_project_management_portfolio_desktop_api,
)
from src.core.modules.project_management.domain.enums import (
    DependencyType,
    ProjectStatus,
    TaskStatus,
)
from src.core.modules.project_management.domain.portfolio import (
    PortfolioExecutiveRow,
    PortfolioIntakeItem,
    PortfolioIntakeStatus,
    PortfolioProjectDependency,
    PortfolioProjectDependencyView,
    PortfolioRecentAction,
    PortfolioScenario,
    PortfolioScenarioComparison,
    PortfolioScenarioEvaluation,
    PortfolioScoringTemplate,
)
from src.core.modules.project_management.domain.projects.project import Project
from src.tests.project_management.test_project_management_desktop_api_portfolio_fakes import (
    _FakeProjectService,
)
from src.tests.project_management.test_project_management_desktop_api_portfolio_service import (
    _FakePortfolioService,
)


def test_project_management_portfolio_desktop_api_mutates_portfolio_records() -> None:
    project_service = _FakeProjectService()
    project_alpha = project_service.create_project(
        name="Plant Upgrade",
        description="Replace switchgear and commission the new line.",
        financial_currency_code="eur",
    )
    project_beta = project_service.create_project(
        name="Warehouse Retrofit",
        description="Upgrade lighting and controls.",
        financial_currency_code="eur",
    )
    project_service.update_project(project_alpha.id, status=ProjectStatus.ACTIVE)
    project_service.update_project(project_beta.id, status=ProjectStatus.ON_HOLD)
    portfolio_service = _FakePortfolioService(project_service)
    api = build_project_management_portfolio_desktop_api(
        project_service=project_service,
        portfolio_service=portfolio_service,
    )

    assert [option.label for option in api.list_projects()] == [
        "Plant Upgrade",
        "Warehouse Retrofit",
    ]
    assert api.list_intake_statuses()[0].value == "PROPOSED"
    assert api.list_dependency_types()[0].label == "Finish -> Start"

    created_template = api.create_scoring_template(
        SimpleNamespace(
            name="Balanced PMO",
            summary="Weighted intake rubric for governance.",
            strategic_weight=3,
            value_weight=2,
            urgency_weight=2,
            risk_weight=1,
            activate=True,
        )
    )
    created_intake = api.create_intake_item(
        SimpleNamespace(
            title="Packaging Line Expansion",
            sponsor_name="Operations Director",
            summary="Capacity uplift on the secondary line.",
            requested_budget=180000.0,
            requested_capacity_percent=40.0,
            target_start_date=date(2026, 6, 1),
            strategic_score=5,
            value_score=4,
            urgency_score=3,
            risk_score=2,
            scoring_template_id=created_template.id,
            status="APPROVED",
        )
    )
    created_scenario = api.create_scenario(
        SimpleNamespace(
            name="Q3 Balanced Plan",
            budget_limit=500000.0,
            capacity_limit_percent=280.0,
            project_ids=(project_alpha.id,),
            intake_item_ids=(created_intake.id,),
            notes="Protect active execution first.",
        )
    )
    comparison_scenario = api.create_scenario(
        SimpleNamespace(
            name="Aggressive Expansion",
            budget_limit=650000.0,
            capacity_limit_percent=340.0,
            project_ids=(project_alpha.id, project_beta.id),
            intake_item_ids=(created_intake.id,),
            notes="Bring forward more intake if labor opens up.",
        )
    )

    listed_templates = api.list_templates()
    listed_intake = api.list_intake_items(status="APPROVED")
    evaluation = api.evaluate_scenario(created_scenario.id)
    comparison = api.compare_scenarios(created_scenario.id, comparison_scenario.id)
    dependency = api.create_project_dependency(
        SimpleNamespace(
            predecessor_project_id=project_alpha.id,
            successor_project_id=project_beta.id,
            dependency_type="FS",
            summary="Warehouse cutover depends on line shutdown lessons learned.",
        )
    )

    assert listed_templates[0].is_active is True
    assert listed_intake[0].title == "Packaging Line Expansion"
    assert evaluation.scenario_name == "Q3 Balanced Plan"
    assert evaluation.status_label == "Within limits"
    assert comparison.added_project_names == ("Warehouse Retrofit",)
    assert dependency.summary == "Warehouse cutover depends on line shutdown lessons learned."
    assert api.list_heatmap()[0].pressure_label in {"Stable", "Watch", "Hot"}
    assert api.list_recent_actions(limit=5)[0].action_label == "Dependency created"

    api.remove_project_dependency(dependency.dependency_id)

    assert api.list_dependencies() == ()

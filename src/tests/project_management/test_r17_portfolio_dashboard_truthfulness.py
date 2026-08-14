from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

from src.core.modules.project_management.api.desktop.dashboard.builders.operational_table_builder import (
    build_operational_tables,
)
from src.core.modules.project_management.api.desktop.dashboard.builders.overview_builder import (
    build_contextual_overview,
)
from src.core.modules.project_management.application.dashboard.reporting.portfolio import (
    DashboardPortfolioMixin,
)


def _critical_row(index: int) -> SimpleNamespace:
    return SimpleNamespace(
        task_id=f"critical-{index}",
        task_name=f"Critical {index}",
        owner_name="Owner",
        finish_date=date(2026, 8, 31),
        total_float_days=0,
        late_by_days=index,
        status_label="Critical",
    )


def _milestone_row(index: int) -> SimpleNamespace:
    return SimpleNamespace(
        task_id=f"milestone-{index}",
        task_name=f"Milestone {index}",
        owner_name="Owner",
        target_date=date(2026, 9, 30),
        slip_days=index,
        status_label="Watch",
    )


def test_dashboard_operational_tables_distinguish_bounded_and_complete_sets() -> None:
    data = SimpleNamespace(
        kpi=SimpleNamespace(project_id="project-1"),
        critical_watchlist=[_critical_row(index) for index in range(12)],
        milestone_health=[_milestone_row(index) for index in range(12)],
        high_risks=[],
        resource_load=[],
        cost_sources=None,
    )

    tables = build_operational_tables(
        dashboard_data=data,
        pending_approvals=(),
        selected_period_key="all",
        portfolio_mode=False,
    )
    by_id = {table.id: table for table in tables}

    assert len(by_id["delayed_tasks"].rows) == 8
    assert by_id["delayed_tasks"].collection_semantics == "top_n"
    assert by_id["delayed_tasks"].supports_search is False
    assert by_id["delayed_tasks"].supports_pagination is False
    assert len(by_id["milestones"].rows) == 8
    assert by_id["milestones"].collection_semantics == "top_n"
    assert by_id["pending_approvals"].collection_semantics == "bounded"
    assert by_id["high_risks"].collection_semantics == "complete"
    assert by_id["high_risks"].supports_search is True
    assert by_id["high_risks"].supports_pagination is True


def test_dashboard_does_not_present_bounded_approval_rows_as_a_global_total() -> None:
    dashboard_data = SimpleNamespace(
        kpi=SimpleNamespace(
            tasks_total=4,
            tasks_completed=1,
            tasks_in_progress=2,
            task_blocked=0,
            critical_tasks=1,
            late_tasks=1,
            cost_variance=Decimal("0"),
        ),
        register_summary=None,
        resource_load=[],
    )

    overview = build_contextual_overview(
        project_name="Truthful Dashboard",
        dashboard_data=dashboard_data,
        selected_view_key="pmo",
        portfolio_mode=False,
    )

    assert "Approvals" not in {metric.label for metric in overview.metrics}


def test_dashboard_qml_disables_page_local_sort_and_bounded_controls() -> None:
    source = Path(
        "src/ui_qml/modules/project_management/qml/workspaces/dashboard/panels/"
        "DashboardOperationalPanel.qml"
    ).read_text(encoding="utf-8")

    assert 'sortingMode: "none"' in source
    assert "showSearch: Boolean(root.operationalTableModel.supportsSearch)" in source
    assert "visible: Boolean(root.operationalTableModel.supportsPagination)" in source


def test_portfolio_financial_aggregate_is_complete_and_decimal_exact(
    monkeypatch,
) -> None:
    projects = [
        SimpleNamespace(
            id=f"project-{index:03d}",
            name=f"Project {index:03d}",
            status=SimpleNamespace(value="ACTIVE"),
        )
        for index in range(51)
    ]

    class Reporting:
        @staticmethod
        def get_project_kpis(project_id: str) -> SimpleNamespace:
            return SimpleNamespace(
                project_id=project_id,
                name=project_id,
                start_date=None,
                end_date=None,
                tasks_total=0,
                tasks_completed=0,
                tasks_in_progress=0,
                task_blocked=0,
                tasks_not_started=0,
                critical_tasks=0,
                late_tasks=0,
                total_planned_cost=Decimal("0.02"),
                total_actual_cost=Decimal("0.01"),
                total_committed_cost=Decimal("0.005"),
                cost_variance=Decimal("-0.01"),
                committment_variance=Decimal("-0.015"),
                financial_detail_included=True,
            )

        @staticmethod
        def get_resource_load_summary(_project_id: str) -> list[object]:
            return []

    class Harness(DashboardPortfolioMixin):
        def __init__(self) -> None:
            self._projects = SimpleNamespace(list_projects=lambda: projects)
            self._reporting = Reporting()
            self._calendar = SimpleNamespace(working_days_between=lambda _start, _end: 0)
            self._user_session = object()

        @staticmethod
        def _build_upcoming_tasks(_project_id: str) -> list[object]:
            return []

    monkeypatch.setattr(
        "src.core.modules.project_management.application.dashboard.reporting.portfolio.require_permission",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        "src.core.modules.project_management.application.dashboard.reporting.portfolio.filter_project_rows",
        lambda rows, *_args, **_kwargs: list(rows),
    )

    result = Harness().get_portfolio_data()

    assert result.portfolio.projects_total == 51
    assert len(result.portfolio.project_rankings) == 51
    assert result.kpi.total_planned_cost == Decimal("1.02")
    assert result.kpi.total_actual_cost == Decimal("0.51")
    assert result.kpi.total_committed_cost == Decimal("0.255")
    assert result.kpi.cost_variance == Decimal("-0.51")
    assert isinstance(result.kpi.total_actual_cost, Decimal)

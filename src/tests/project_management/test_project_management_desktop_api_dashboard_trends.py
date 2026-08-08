from datetime import date, datetime, timedelta
from types import SimpleNamespace

from src.core.modules.project_management.api.desktop import (
    build_project_management_dashboard_desktop_api,
)
from src.core.modules.project_management.domain.risk.register import (
    RegisterEntrySeverity,
    RegisterEntryStatus,
    RegisterEntryType,
)


def test_project_management_dashboard_desktop_api_uses_real_period_labels_for_trend_axes() -> None:
    period_dates = (
        date.today() - timedelta(days=60),
        date.today() - timedelta(days=30),
        date.today(),
    )
    api = build_project_management_dashboard_desktop_api(
        project_service=SimpleNamespace(
            list_projects=lambda: [SimpleNamespace(id="proj-1", name="Plant Upgrade")]
        ),
        baseline_service=SimpleNamespace(list_baselines=lambda _project_id: []),
        dashboard_service=SimpleNamespace(
            get_dashboard_data=lambda project_id, baseline_id=None: SimpleNamespace(
                kpi=SimpleNamespace(
                    project_id=project_id,
                    name="Plant Upgrade",
                    tasks_total=6,
                    tasks_completed=2,
                    tasks_in_progress=3,
                    task_blocked=0,
                    critical_tasks=1,
                    late_tasks=1,
                    cost_variance=1200.0,
                    total_actual_cost=10000.0,
                    total_planned_cost=11200.0,
                ),
                alerts=[],
                milestone_health=[],
                critical_watchlist=[],
                resource_load=[],
                upcoming_tasks=[],
                burndown=[],
                evm=SimpleNamespace(
                    baseline_id="base-1",
                    as_of=period_dates[2],
                    CPI=0.96,
                    SPI=0.93,
                    PV=12000.0,
                    EV=11200.0,
                    AC=11850.0,
                    EAC=12600.0,
                    VAC=-600.0,
                    TCPI_to_BAC=1.04,
                    TCPI_to_EAC=1.01,
                    status_text="Watch. Recover. Monitor. Above target.",
                ),
                register_summary=None,
                cost_sources=None,
            )
        ),
        reporting_service=SimpleNamespace(
            get_evm_series=lambda project_id, baseline_id=None, as_of=None: [
                SimpleNamespace(
                    period_end=period_dates[0],
                    PV=9000.0,
                    EV=8800.0,
                    AC=9100.0,
                    BAC=15000.0,
                    CPI=0.97,
                    SPI=0.98,
                ),
                SimpleNamespace(
                    period_end=period_dates[1],
                    PV=10500.0,
                    EV=9800.0,
                    AC=10150.0,
                    BAC=15000.0,
                    CPI=0.97,
                    SPI=0.93,
                ),
                SimpleNamespace(
                    period_end=period_dates[2],
                    PV=12000.0,
                    EV=11200.0,
                    AC=11850.0,
                    BAC=15000.0,
                    CPI=0.95,
                    SPI=0.93,
                ),
            ]
        ),
    )

    snapshot = api.build_snapshot(project_id="proj-1", period_key="90d")

    assert [point.label for point in snapshot.charts[0].points] == [
        value.strftime("%d %b") for value in period_dates
    ]
    assert [point.supporting_text for point in snapshot.charts[0].points] == [
        value.isoformat() for value in period_dates
    ]
    assert snapshot.charts[1].points[0].label == period_dates[0].strftime("%d %b")


def test_project_management_dashboard_desktop_api_normalizes_naive_activity_timestamps() -> None:
    activity_at = datetime.now().replace(hour=9, minute=30, second=0, microsecond=0)
    recent_at = activity_at - timedelta(days=1, hours=1, minutes=15)
    requested_at = activity_at.replace(hour=7, minute=0)
    api = build_project_management_dashboard_desktop_api(
        project_service=SimpleNamespace(
            list_projects=lambda: [SimpleNamespace(id="proj-1", name="Plant Upgrade")]
        ),
        baseline_service=SimpleNamespace(list_baselines=lambda _project_id: []),
        dashboard_service=SimpleNamespace(
            get_dashboard_data=lambda project_id, baseline_id=None: SimpleNamespace(
                kpi=SimpleNamespace(
                    project_id=project_id,
                    name="Plant Upgrade",
                    tasks_total=4,
                    tasks_completed=1,
                    tasks_in_progress=2,
                    task_blocked=0,
                    critical_tasks=1,
                    late_tasks=1,
                    cost_variance=0.0,
                    total_actual_cost=1000.0,
                    total_planned_cost=1500.0,
                ),
                alerts=[],
                milestone_health=[],
                critical_watchlist=[],
                resource_load=[],
                upcoming_tasks=[],
                burndown=[],
                evm=None,
                register_summary=None,
                cost_sources=None,
            )
        ),
        collaboration_service=SimpleNamespace(
            list_workspace_snapshot=lambda limit=120: SimpleNamespace(
                notifications=[
                    SimpleNamespace(
                        entity_id="approval-1",
                        entity_type="approval_request",
                        headline="Approval requested",
                        notification_type="approval",
                        actor_username="planner",
                        created_at=activity_at,
                        project_id="proj-1",
                        project_name="Plant Upgrade",
                    )
                ],
                recent_activity=[
                    SimpleNamespace(
                        comment_id="comment-1",
                        task_id="task-1",
                        task_name="Cable Pull",
                        unread=False,
                        author_username="pm",
                        created_at=recent_at,
                        project_id="proj-1",
                        project_name="Plant Upgrade",
                    )
                ],
                inbox=[],
                active_presence=[],
            )
        ),
        approval_service=SimpleNamespace(
            list_pending=lambda project_id=None, limit=120: [
                SimpleNamespace(
                    id="req-1",
                    project_id="proj-1",
                    requested_by_username="planner",
                    requested_at=requested_at,
                    status=SimpleNamespace(value="pending"),
                    module_key="project_management",
                    request_type="baseline",
                    entity_type="project_baseline",
                    entity_label="Weekly Freeze",
                    context_label="Plant Upgrade",
                )
            ]
        ),
    )

    snapshot = api.build_snapshot(project_id="proj-1", period_key="30d")

    assert snapshot.activity_feed.items[0].title == "Approval requested"
    assert snapshot.activity_feed.items[0].meta_text.endswith(
        activity_at.strftime("%Y-%m-%d %H:%M")
    )
    approvals_table = next(
        table for table in snapshot.operational_tables if table.id == "pending_approvals"
    )
    assert approvals_table.rows[0].values["requestedAt"] == requested_at.strftime(
        "%Y-%m-%d %H:%M"
    )

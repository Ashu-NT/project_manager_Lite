from datetime import date, datetime
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
                    as_of=date(2026, 5, 31),
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
                    period_end=date(2026, 3, 31),
                    PV=9000.0,
                    EV=8800.0,
                    AC=9100.0,
                    BAC=15000.0,
                    CPI=0.97,
                    SPI=0.98,
                ),
                SimpleNamespace(
                    period_end=date(2026, 4, 30),
                    PV=10500.0,
                    EV=9800.0,
                    AC=10150.0,
                    BAC=15000.0,
                    CPI=0.97,
                    SPI=0.93,
                ),
                SimpleNamespace(
                    period_end=date(2026, 5, 31),
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
        "31 Mar",
        "30 Apr",
        "31 May",
    ]
    assert [point.supporting_text for point in snapshot.charts[0].points] == [
        "2026-03-31",
        "2026-04-30",
        "2026-05-31",
    ]
    assert snapshot.charts[1].points[0].label == "31 Mar"


def test_project_management_dashboard_desktop_api_normalizes_naive_activity_timestamps() -> None:
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
                        created_at=datetime(2026, 5, 20, 9, 30),
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
                        created_at=datetime(2026, 5, 19, 8, 15),
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
                    requested_at=datetime(2026, 5, 20, 7, 0),
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
    assert snapshot.activity_feed.items[0].meta_text.endswith("2026-05-20 09:30")
    approvals_table = next(
        table for table in snapshot.operational_tables if table.id == "pending_approvals"
    )
    assert approvals_table.rows[0].values["requestedAt"] == "2026-05-20 07:00"

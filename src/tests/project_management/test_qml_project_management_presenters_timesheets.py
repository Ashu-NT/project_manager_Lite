from datetime import date
from types import SimpleNamespace

from src.ui_qml.modules.project_management.context import ProjectManagementWorkspaceCatalog


class _FakeTimesheetsDesktopApi:
    def list_projects(self):
        return (
            SimpleNamespace(value="proj-1", label="Plant Upgrade"),
            SimpleNamespace(value="proj-2", label="Warehouse Retrofit"),
        )

    def list_assignments(self, *, project_id=None):
        rows = (
            SimpleNamespace(value="assign-1", label="Plant Upgrade | Cable Pull | Electrical Crew"),
            SimpleNamespace(value="assign-2", label="Warehouse Retrofit | Lighting Retrofit | Alex Taylor"),
        )
        if project_id == "proj-1":
            return rows[:1]
        if project_id == "proj-2":
            return rows[1:]
        return rows

    def list_queue_statuses(self):
        return (
            SimpleNamespace(value="all", label="All statuses"),
            SimpleNamespace(value="SUBMITTED", label="Submitted"),
            SimpleNamespace(value="APPROVED", label="Approved"),
        )

    def build_assignment_snapshot(self, assignment_id, *, period_start=None):
        assert assignment_id == "assign-1"
        return SimpleNamespace(
            assignment=SimpleNamespace(
                value="assign-1",
                label="Plant Upgrade | Cable Pull | Electrical Crew",
                project_id="proj-1",
            ),
            period_options=(SimpleNamespace(value="2026-05-01", label="May 2026"),),
            selected_period_start="2026-05-01",
            period_summary=SimpleNamespace(
                period_id="period-1",
                period_start_label="May 2026",
                period_end_label="2026-05-31",
                status="SUBMITTED",
                status_label="Submitted",
                resource_id="res-1",
                resource_name="Electrical Crew",
                total_hours_label="16.00h",
                entry_count=2,
                submitted_by_username="alex",
                submitted_at_label="2026-05-04 17:00",
                decided_by_username="-",
                decided_at_label="-",
                decision_note="",
            ),
            entries=(
                SimpleNamespace(
                    entry_id="entry-1",
                    entry_date_label="2026-05-03",
                    hours=8.0,
                    hours_label="8.00h",
                    note="Cable tray installation",
                    author_username="alex",
                ),
                SimpleNamespace(
                    entry_id="entry-2",
                    entry_date_label="2026-05-04",
                    hours=8.0,
                    hours_label="8.00h",
                    note="Termination prep",
                    author_username="alex",
                ),
            ),
            resource_period_total_hours_label="16.00h",
            scope_summary="Task period entries: 2 | Resource month total: 16.00h",
        )

    def list_review_queue_page(self, *, status="SUBMITTED", page=1, page_size=25):
        if status == "all":
            rows = (
                SimpleNamespace(
                    period_id="period-1",
                    resource_name="Electrical Crew",
                    period_start_label="May 2026",
                    status="SUBMITTED",
                    status_label="Submitted",
                    project_names=("Plant Upgrade",),
                    total_hours_label="16.00h",
                    entry_count=2,
                    submitted_by_username="alex",
                    submitted_at_label="2026-05-04 17:00",
                    resource_id="res-1",
                    period_start=date(2026, 5, 1),
                ),
            )
            return SimpleNamespace(items=rows, total=len(rows), page=page, page_size=page_size)
        rows = (
            SimpleNamespace(
                period_id="period-1",
                resource_name="Electrical Crew",
                period_start_label="May 2026",
                status="SUBMITTED",
                status_label="Submitted",
                project_names=("Plant Upgrade",),
                total_hours_label="16.00h",
                entry_count=2,
                submitted_by_username="alex",
                submitted_at_label="2026-05-04 17:00",
                resource_id="res-1",
                period_start=date(2026, 5, 1),
            ),
        )
        return SimpleNamespace(items=rows, total=len(rows), page=page, page_size=page_size)

    def get_review_detail(self, period_id):
        assert period_id == "period-1"
        return SimpleNamespace(
            summary=SimpleNamespace(
                period_id="period-1",
                resource_id="res-1",
                resource_name="Electrical Crew",
                period_start=date(2026, 5, 1),
                period_start_label="May 2026",
                status="SUBMITTED",
                status_label="Submitted",
                project_names=("Plant Upgrade",),
                total_hours_label="16.00h",
                entry_count=2,
                submitted_by_username="alex",
                submitted_at_label="2026-05-04 17:00",
                decided_by_username="-",
                decided_at_label="-",
                decision_note="No decision note recorded.",
            ),
            entries=(
                SimpleNamespace(task_name="Cable Pull"),
                SimpleNamespace(task_name="Cable Pull"),
            ),
        )


def test_project_management_workspace_catalog_exposes_typed_timesheets_controller() -> None:
    catalog = ProjectManagementWorkspaceCatalog(
        desktop_api_registry=SimpleNamespace(
            project_management_timesheets=_FakeTimesheetsDesktopApi()
        )
    )

    controller = catalog.timesheetsWorkspace

    assert controller.workspace["routeId"] == "project_management.timesheets"
    assert controller.overview["title"] == "Timesheets"
    assert controller.assignmentOptions[0]["label"] == "Plant Upgrade | Cable Pull | Electrical Crew"
    assert controller.entries["items"][0]["title"] == "2026-05-03"
    assert controller.selectedEntry["fields"][0]["value"] == "2026-05-03"
    assert controller.reviewQueue["items"][0]["title"] == "Electrical Crew | May 2026"

    controller.setQueueStatus("all")

    assert controller.selectedQueueStatus == "all"
    assert controller.reviewDetail["title"] == "Electrical Crew | May 2026"

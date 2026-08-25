from dataclasses import FrozenInstanceError
from pathlib import Path

from alembic import command
from alembic.config import Config
import pytest
import sqlalchemy as sa

from src.core.modules.project_management.contracts.reads.timesheets import (
    ReviewQueueItemType,
    TimesheetReviewQueueFact,
)
from src.core.platform.domain.time_management.time import TimesheetPeriodStatus


ROOT = Path(__file__).resolve().parents[2]
QML = ROOT / "ui_qml/modules/project_management/qml/workspaces/timesheets"
CONTROLLER = ROOT / "ui_qml/modules/project_management/controllers/timesheets"
PRESENTER = ROOT / "ui_qml/modules/project_management/presenters/timesheets"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_review_queue_fact_is_immutable_and_typed() -> None:
    fact = TimesheetReviewQueueFact(
        item_id="period-1",
        timesheet_period_id="period-1",
        version=4,
        resource_id="resource-1",
        resource_name="Reviewer",
        resource_code="RES-1",
        period_start=__import__("datetime").date(2026, 8, 1),
        period_end=__import__("datetime").date(2026, 8, 31),
        status=TimesheetPeriodStatus.SUBMITTED,
        submitted_at=None,
        submitted_by_username=None,
        decided_at=None,
        decided_by_username=None,
        decision_note=None,
        total_hours=0.0,
        project_count=0,
        task_count=0,
        entry_count=0,
        generic_entry_count=0,
        project_ids=(),
    )

    assert fact.item_type is ReviewQueueItemType.TIMESHEET_PERIOD
    with pytest.raises(FrozenInstanceError):
        fact.version = 5


def test_review_queue_qml_is_capability_driven_and_has_no_bulk_or_submit() -> None:
    state = _read(QML / "TimesheetsWorkspaceState.qml")
    page = _read(QML / "TimesheetsWorkspacePage.qml")
    list_page = _read(QML / "components/TimesheetsListPage.qml")
    dialog = _read(QML / "components/TimesheetReviewDecisionDialog.qml")

    assert "st.canApprove === true" in state
    assert "st.canReject === true" in state
    assert 'status === "SUBMITTED"' not in state
    assert "submitPeriod" not in page
    assert "bulk" not in page.lower()
    assert "multiSelect: false" in list_page
    assert 'sortingMode: "server"' in list_page
    assert '"expectedVersion"' in dialog
    assert "A return reason is required" in dialog


def test_review_controller_and_presenter_do_not_own_personal_time_state() -> None:
    controller = _read(CONTROLLER / "timesheets_workspace_controller.py")
    presenter = _read(PRESENTER / "timesheets_workspace_presenter.py")

    for obsolete in (
        "assignmentOptions",
        "entriesTableModel",
        "selectedEntry",
        "submitPeriod",
        "addTimeEntry",
        "updateTimeEntry",
        "deleteTimeEntry",
    ):
        assert obsolete not in controller
    assert "submit_period" not in presenter
    assert "add_time_entry" not in presenter


def test_r5f_migration_repairs_a_pre_baseline_edit_database(tmp_path) -> None:
    database = tmp_path / "r5f-repair.db"
    config = Config(str(ROOT / "infra/persistence/migrations/alembic.ini"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database.as_posix()}")
    command.upgrade(config, "c817a91e5f24")
    engine = sa.create_engine(config.get_main_option("sqlalchemy.url"), future=True)
    with engine.begin() as connection:
        connection.execute(sa.text("ALTER TABLE timesheet_periods DROP COLUMN version"))
    assert "version" not in {
        column["name"] for column in sa.inspect(engine).get_columns("timesheet_periods")
    }
    engine.dispose()

    command.upgrade(config, "head")
    engine = sa.create_engine(config.get_main_option("sqlalchemy.url"), future=True)
    columns = {
        column["name"]: column
        for column in sa.inspect(engine).get_columns("timesheet_periods")
    }
    assert columns["version"]["nullable"] is False
    engine.dispose()

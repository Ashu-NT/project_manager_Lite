from __future__ import annotations

from datetime import date
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGridLayout
from PySide6.QtWidgets import QDialog

from core.modules.project_management.domain.enums import TaskStatus
from core.platform.common.models import DependencyType
from core.modules.project_management.services.dashboard import PORTFOLIO_SCOPE_ID
from infra.modules.project_management.collaboration_store import TaskCollaborationStore
from tests.ui_runtime_helpers import make_settings_store
from ui.modules.project_management.dashboard.layout_builder import DashboardLayoutDialog
from ui.modules.project_management.dashboard.tab import DashboardTab
from ui.modules.project_management.report.dialog_gantt import GanttPreviewDialog
from ui.platform.shared.styles.theme import set_theme_mode
from ui.platform.shared.styles.ui_config import UIConfig as CFG
from ui.modules.project_management.task.collaboration_dialog import TaskCollaborationDialog
from ui.modules.project_management.task.tab import TaskTab


ROOT = Path(__file__).resolve().parents[1]


def test_pro_set_tracker_is_persisted():
    text = (ROOT / "docs" / "PRO_SET_IMPLEMENTATION.md").read_text(encoding="utf-8", errors="ignore")
    assert "Implement the full Pro Set 1 to 7" in text
    assert "- [x] 1. Productivity UX core" in text
    assert "- [x] 7. Material Design 3 modernization" in text


def test_task_tab_pro_controls_saved_views_and_undo_work_at_runtime(
    qapp,
    services,
    repo_workspace,
    monkeypatch,
):
    project = services["project_service"].create_project("Pro Set Tasks")
    services["task_service"].create_task(
        project.id,
        "High Priority Task",
        description="Critical path task",
        start_date=date(2026, 4, 1),
        duration_days=2,
        priority=90,
    )
    services["task_service"].create_task(
        project.id,
        "Routine Task",
        description="Normal task",
        start_date=date(2026, 4, 2),
        duration_days=2,
        priority=20,
    )

    tab = TaskTab(
        project_service=services["project_service"],
        task_service=services["task_service"],
        resource_service=services["resource_service"],
        project_resource_service=services["project_resource_service"],
        collaboration_store=services["task_collaboration_store"],
        settings_store=make_settings_store(repo_workspace, prefix="pro-set-task"),
        user_session=services["user_session"],
    )

    assert tab.btn_bulk_status.text() == "Apply Status"
    assert tab.btn_bulk_delete.text() == "Bulk Delete"
    assert tab.btn_comments.text() == "Comments"
    assert tab.lbl_mentions.text() == "Mentions: 0"
    assert tab.btn_assignment_add.text() == "Assign Resource"
    assert tab.btn_assignment_remove.text() == "Remove Assignment"
    assert tab.btn_assignment_set_alloc.text() == "Adjust Allocation"
    assert tab.btn_assignment_log_hours.text() == "Open Timesheet"
    assert tab.btn_dependency_add.text() == "Create Dependency"
    assert tab.btn_dependency_remove.text() == "Remove Dependency"
    assert tab.work_tabs.count() == 2
    assert tab.work_tabs.tabText(0) == "Assignments"
    assert tab.work_tabs.tabText(1) == "Dependencies"
    assert "advanced:" in tab.task_search_filter.placeholderText()
    assert tab.task_view_combo.count() >= 1

    monkeypatch.setattr(
        "ui.modules.project_management.task.filtering.QInputDialog.getText",
        lambda *_args, **_kwargs: ("High Focus", True),
    )
    tab.task_search_filter.setText("priority>=70")
    tab._save_current_task_view()
    saved_index = tab.task_view_combo.findData("High Focus")
    assert saved_index >= 0

    tab._clear_task_filters()
    tab.task_view_combo.setCurrentIndex(saved_index)
    tab._apply_selected_task_view()
    assert tab.task_search_filter.text() == "priority>=70"
    assert tab.model.rowCount() == 1

    tab._clear_task_filters()
    tab.table.selectAll()
    tab.bulk_status_combo.setCurrentIndex(tab.bulk_status_combo.findData(TaskStatus.DONE.value))
    tab.apply_bulk_status()

    status_by_name = {
        task.name: task.status for task in services["task_service"].list_tasks_for_project(project.id)
    }
    assert status_by_name == {
        "High Priority Task": TaskStatus.DONE,
        "Routine Task": TaskStatus.DONE,
    }
    assert tab._undo_stack.can_undo() is True

    tab.undo_last_task_action()
    status_by_name = {
        task.name: task.status for task in services["task_service"].list_tasks_for_project(project.id)
    }
    assert status_by_name == {
        "High Priority Task": TaskStatus.TODO,
        "Routine Task": TaskStatus.TODO,
    }

    tab.redo_last_task_action()
    status_by_name = {
        task.name: task.status for task in services["task_service"].list_tasks_for_project(project.id)
    }
    assert status_by_name == {
        "High Priority Task": TaskStatus.DONE,
        "Routine Task": TaskStatus.DONE,
    }

    tab._mentions_refresh_timer.stop()


def test_gantt_preview_dialog_supports_interactive_controls_runtime(qapp, services, monkeypatch):
    project = services["project_service"].create_project("Interactive Gantt")
    monkeypatch.setattr(GanttPreviewDialog, "_load_image", lambda self: None)

    dialog = GanttPreviewDialog(
        None,
        services["reporting_service"],
        project.id,
        project.name,
        task_service=services["task_service"],
        can_edit=True,
        can_open_interactive=True,
    )

    assert dialog.btn_open_interactive.text() == "Open Interactive"
    assert dialog.btn_open_interactive.isEnabled() is True
    assert dialog.btn_toggle_grid.text() == "Grid: On"
    assert dialog.btn_review_changes.text() == "Review Changes"
    assert dialog.btn_undo_last_apply.isEnabled() is False
    assert dialog.interactive_container.isHidden() is True

    dialog._toggle_interactive_panel()

    assert dialog.interactive_container.isHidden() is False
    assert dialog.btn_open_interactive.text() == "Hide Interactive"


def test_dashboard_layout_builder_and_persisted_state_work_at_runtime(
    qapp,
    services,
    repo_workspace,
    monkeypatch,
):
    project = services["project_service"].create_project("Dashboard Project")
    store = make_settings_store(repo_workspace, prefix="dashboard-layout")
    store.save_dashboard_layout(
        {
            "project": {
                "visible_panels": ["resource", "kpi"],
                "panel_order": ["resource", "kpi", "evm", "burndown"],
            },
            "portfolio": {
                "visible_panels": ["portfolio", "resource", "burndown"],
                "panel_order": ["portfolio", "resource", "burndown", "kpi"],
            },
        }
    )
    monkeypatch.setattr("ui.modules.project_management.dashboard.data_ops.run_refresh_dashboard_async", lambda *_args, **_kwargs: None)

    tab = DashboardTab(
        project_service=services["project_service"],
        dashboard_service=services["dashboard_service"],
        baseline_service=services["baseline_service"],
        settings_store=store,
        user_session=services["user_session"],
    )

    assert project.id == tab.project_combo.currentData()
    assert tab.btn_customize_dashboard.text() == "Customize Dashboard"
    assert tab.summary_widget.isHidden() is False
    assert tab.project_label_prefix.text() == "PROJECT OVERVIEW"
    assert tab.project_mode_badge.text() == "Project View"
    assert tab.dashboard_mode_badge.text() == "Live Panels"
    assert tab.kpi_group.isHidden() is False
    assert tab.resource_chart.isHidden() is False
    assert tab.evm_group.isHidden() is True
    assert tab.burndown_chart.isHidden() is True
    assert tab.portfolio_group.isHidden() is True
    assert tab._current_visible_panel_ids() == ["resource", "kpi"]
    assert tab._current_panel_order() == ["resource", "kpi", "evm", "burndown", "milestones", "watchlist"]
    assert tab._active_dashboard_panel_count() == 2

    applied_payload = {
        "project": {
            "visible_panels": ["evm", "kpi", "burndown"],
            "panel_order": ["evm", "kpi", "burndown", "resource"],
        },
        "portfolio": {
            "visible_panels": ["portfolio", "resource"],
            "panel_order": ["portfolio", "resource", "burndown", "kpi"],
        },
    }

    class _AcceptedLayoutDialog:
        def __init__(self, _parent, *, current_layout=None, portfolio_mode=False):
            self.current_layout = current_layout
            self.portfolio_mode = portfolio_mode
            self.layout_payload = applied_payload

        def exec(self):
            return QDialog.Accepted

    monkeypatch.setattr("ui.modules.project_management.dashboard.layout_state.DashboardLayoutDialog", _AcceptedLayoutDialog)
    tab._open_dashboard_layout_builder()

    assert store.load_dashboard_layout() == applied_payload
    assert tab._current_visible_panel_ids() == ["evm", "kpi", "burndown"]
    assert tab._active_dashboard_panel_count() == 3
    assert tab._current_panel_order() == ["evm", "kpi", "burndown", "resource", "milestones", "watchlist"]
    assert tab.evm_group.isHidden() is False
    assert tab.kpi_group.isHidden() is False
    assert tab.burndown_chart.isHidden() is False
    assert tab.resource_chart.isHidden() is True
    assert tab.portfolio_group.isHidden() is True

    portfolio_index = tab.project_combo.findData(PORTFOLIO_SCOPE_ID)
    tab.project_combo.setCurrentIndex(portfolio_index)

    assert tab._current_visible_panel_ids() == ["portfolio", "resource"]
    assert tab.portfolio_group.isHidden() is False
    assert tab.resource_chart.isHidden() is False
    assert tab.kpi_group.isHidden() is True
    assert tab.burndown_chart.isHidden() is True


def test_dashboard_layout_dialog_enforces_mode_specific_selection_runtime(qapp):
    set_theme_mode("light")
    dialog = DashboardLayoutDialog(
        None,
        current_layout={
            "project": {
                "visible_panels": ["kpi", "evm", "burndown"],
                "panel_order": ["evm", "kpi", "burndown", "resource"],
            },
            "portfolio": {
                "visible_panels": ["portfolio", "resource", "burndown"],
                "panel_order": ["portfolio", "resource", "burndown", "kpi"],
            },
        },
        portfolio_mode=True,
    )

    assert dialog.mode_badge.text() == "Portfolio View"
    assert CFG.COLOR_TEXT_PRIMARY in dialog.btn_apply_preset.styleSheet()
    assert CFG.COLOR_ACCENT in dialog.btn_save.styleSheet()
    assert dialog.btn_save.isEnabled() is True
    dialog._panel_checks["portfolio"].setChecked(False)
    dialog._panel_checks["resource"].setChecked(False)
    dialog._sync_selection_state()
    assert dialog.btn_save.isEnabled() is False
    dialog._panel_checks["resource"].setChecked(True)
    dialog._sync_selection_state()
    assert dialog.btn_save.isEnabled() is True


def test_dashboard_control_rail_collapses_runtime(qapp, services, repo_workspace, monkeypatch):
    services["project_service"].create_project("Dashboard Rail")
    monkeypatch.setattr("ui.modules.project_management.dashboard.data_ops.run_refresh_dashboard_async", lambda *_args, **_kwargs: None)

    tab = DashboardTab(
        project_service=services["project_service"],
        dashboard_service=services["dashboard_service"],
        baseline_service=services["baseline_service"],
        settings_store=make_settings_store(repo_workspace, prefix="dashboard-rail"),
        user_session=services["user_session"],
    )

    assert tab.dashboard_control_stack.currentIndex() == 0
    tab._set_dashboard_controls_collapsed(True)
    assert tab.dashboard_control_stack.currentIndex() == 1
    assert tab.dashboard_control_stack.width() == 128
    tab.btn_show_dashboard_controls.click()
    assert tab.dashboard_control_stack.currentIndex() == 0
    assert tab.kpi_group.layout().count() == 8


def test_dashboard_panels_reflow_responsively_runtime(qapp, services, repo_workspace, monkeypatch):
    services["project_service"].create_project("Responsive Dashboard")
    store = make_settings_store(repo_workspace, prefix="dashboard-responsive")
    store.save_dashboard_layout(
        {
            "project": {
                "visible_panels": ["evm", "kpi", "burndown"],
                "panel_order": ["evm", "kpi", "burndown", "resource"],
            },
            "portfolio": {
                "visible_panels": ["portfolio", "resource"],
                "panel_order": ["portfolio", "resource", "burndown", "kpi"],
            },
        }
    )
    monkeypatch.setattr("ui.modules.project_management.dashboard.data_ops.run_refresh_dashboard_async", lambda *_args, **_kwargs: None)

    tab = DashboardTab(
        project_service=services["project_service"],
        dashboard_service=services["dashboard_service"],
        baseline_service=services["baseline_service"],
        settings_store=store,
        user_session=services["user_session"],
    )
    tab.resize(1500, 900)
    tab.show()
    qapp.processEvents()

    layout = tab.panel_grid
    assert isinstance(layout, QGridLayout)
    assert tab.panel_canvas.maximumWidth() == 1480
    wide_evm = layout.getItemPosition(layout.indexOf(tab.evm_group))
    wide_kpi = layout.getItemPosition(layout.indexOf(tab.kpi_group))
    wide_burndown = layout.getItemPosition(layout.indexOf(tab.burndown_chart))

    assert wide_evm == (0, 0, 1, 1)
    assert wide_kpi == (0, 1, 1, 1)
    assert wide_burndown == (0, 2, 1, 1)

    tab.resize(860, 900)
    qapp.processEvents()

    narrow_evm = layout.getItemPosition(layout.indexOf(tab.evm_group))
    narrow_kpi = layout.getItemPosition(layout.indexOf(tab.kpi_group))
    narrow_burndown = layout.getItemPosition(layout.indexOf(tab.burndown_chart))

    assert narrow_evm == (0, 0, 1, 1)
    assert narrow_kpi == (1, 0, 1, 1)
    assert narrow_burndown == (2, 0, 1, 1)


def test_dashboard_kpi_cards_reflow_responsively_runtime(qapp, services, repo_workspace, monkeypatch):
    services["project_service"].create_project("Responsive KPI Dashboard")
    store = make_settings_store(repo_workspace, prefix="dashboard-kpi-responsive")
    store.save_dashboard_layout(
        {
            "project": {
                "visible_panels": ["kpi"],
                "panel_order": ["kpi", "resource", "evm", "burndown"],
            },
            "portfolio": {
                "visible_panels": ["portfolio", "resource"],
                "panel_order": ["portfolio", "resource", "burndown", "kpi"],
            },
        }
    )
    monkeypatch.setattr("ui.modules.project_management.dashboard.data_ops.run_refresh_dashboard_async", lambda *_args, **_kwargs: None)

    tab = DashboardTab(
        project_service=services["project_service"],
        dashboard_service=services["dashboard_service"],
        baseline_service=services["baseline_service"],
        settings_store=store,
        user_session=services["user_session"],
    )
    tab.resize(1500, 900)
    tab.show()
    qapp.processEvents()

    wide_first = tab.kpi_layout.getItemPosition(tab.kpi_layout.indexOf(tab.kpi_tasks))
    wide_fourth = tab.kpi_layout.getItemPosition(tab.kpi_layout.indexOf(tab.kpi_blocked))
    assert wide_first == (0, 0, 1, 1)
    assert wide_fourth == (0, 3, 1, 1)

    tab.resize(760, 900)
    qapp.processEvents()

    narrow_first = tab.kpi_layout.getItemPosition(tab.kpi_layout.indexOf(tab.kpi_tasks))
    narrow_third = tab.kpi_layout.getItemPosition(tab.kpi_layout.indexOf(tab.kpi_inflight))
    narrow_fourth = tab.kpi_layout.getItemPosition(tab.kpi_layout.indexOf(tab.kpi_blocked))
    assert narrow_first == (0, 0, 1, 1)
    assert narrow_third == (1, 0, 1, 1)
    assert narrow_fourth == (1, 1, 1, 1)


def test_dashboard_schedules_layout_sync_on_first_show_runtime(
    qapp,
    services,
    repo_workspace,
    monkeypatch,
):
    services["project_service"].create_project("Startup Dashboard")
    monkeypatch.setattr("ui.modules.project_management.dashboard.data_ops.run_refresh_dashboard_async", lambda *_args, **_kwargs: None)

    tab = DashboardTab(
        project_service=services["project_service"],
        dashboard_service=services["dashboard_service"],
        baseline_service=services["baseline_service"],
        settings_store=make_settings_store(repo_workspace, prefix="dashboard-first-show"),
        user_session=services["user_session"],
    )

    calls: list[int] = []

    def _count_sync() -> None:
        calls.append(1)

    monkeypatch.setattr(tab, "_sync_dashboard_panel_visibility", _count_sync)

    tab.show()

    assert tab._layout_sync_scheduled is True

    qapp.processEvents()

    assert tab._layout_sync_scheduled is False
    assert calls


def test_dashboard_chart_panels_stay_bounded_and_top_aligned_runtime(
    qapp,
    services,
    repo_workspace,
    monkeypatch,
):
    services["project_service"].create_project("Balanced Dashboard")
    store = make_settings_store(repo_workspace, prefix="dashboard-balanced")
    store.save_dashboard_layout(
        {
            "project": {
                "visible_panels": ["evm", "kpi", "burndown"],
                "panel_order": ["evm", "kpi", "burndown", "resource"],
            },
            "portfolio": {
                "visible_panels": ["portfolio", "resource"],
                "panel_order": ["portfolio", "resource", "burndown", "kpi"],
            },
        }
    )
    monkeypatch.setattr("ui.modules.project_management.dashboard.data_ops.run_refresh_dashboard_async", lambda *_args, **_kwargs: None)

    tab = DashboardTab(
        project_service=services["project_service"],
        dashboard_service=services["dashboard_service"],
        baseline_service=services["baseline_service"],
        settings_store=store,
        user_session=services["user_session"],
    )
    tab.resize(1500, 900)
    tab.show()
    qapp.processEvents()

    burndown_item = tab.panel_grid.itemAtPosition(0, 2)

    assert burndown_item is not None
    assert bool(burndown_item.alignment() & Qt.AlignTop)
    assert tab.burndown_chart.maximumHeight() == 292
    assert tab.resource_chart.maximumHeight() == 292
    assert tab.burndown_chart.sizeHint().height() == 252


def test_task_dependency_add_recalculates_dates_in_table_runtime(qapp, services, repo_workspace, monkeypatch):
    ps = services["project_service"]
    ts = services["task_service"]
    wc = services["work_calendar_engine"]
    settings_store = make_settings_store(repo_workspace, prefix="task-dependency")
    project = ps.create_project("Dependency UI Project")
    predecessor = ts.create_task(project.id, "Predecessor", start_date=date(2026, 4, 1), duration_days=2)
    successor = ts.create_task(project.id, "Successor", start_date=date(2026, 4, 1), duration_days=1)

    tab = TaskTab(
        project_service=ps,
        task_service=ts,
        resource_service=services["resource_service"],
        project_resource_service=services["project_resource_service"],
        collaboration_store=services["task_collaboration_store"],
        settings_store=settings_store,
        user_session=services["user_session"],
    )
    tab._select_task_by_id(successor.id)

    class _AcceptedDependencyDialog:
        predecessor_id = predecessor.id
        successor_id = successor.id
        dependency_type = DependencyType.FINISH_TO_START
        lag_days = 0

        def __init__(self, *_args, **_kwargs):
            pass

        def exec(self):
            return QDialog.Accepted

    monkeypatch.setattr("ui.modules.project_management.task.dependency_panel.DependencyAddDialog", _AcceptedDependencyDialog)
    tab.add_dependency_inline()

    refreshed = {task.id: task for task in ts.list_tasks_for_project(project.id)}
    expected_start = wc.next_working_day(refreshed[predecessor.id].end_date, include_today=False)
    assert refreshed[successor.id].start_date == expected_start

    for row in range(tab.model.rowCount()):
        task = tab.model.get_task(row)
        if task and task.id == successor.id:
            assert tab.model.data(tab.model.index(row, 2)) == expected_start.isoformat()
            assert tab.model.data(tab.model.index(row, 3)) == refreshed[successor.id].end_date.isoformat()
            break
    else:
        assert False, "Successor task not found in table model"

    tab._mentions_refresh_timer.stop()


def test_collaboration_dialog_posts_mentions_and_attachments_at_runtime(qapp, repo_workspace):
    store = TaskCollaborationStore(storage_path=repo_workspace / "comments.json")
    attachment = repo_workspace / "proof.txt"
    attachment.write_text("proof", encoding="utf-8")

    dialog = TaskCollaborationDialog(
        None,
        store=store,
        task_id="task-1",
        task_name="Task One",
        username="bob",
        mention_aliases=["alice"],
    )

    dialog._pending_attachments = [str(attachment)]
    dialog._refresh_attachment_label()
    assert "proof.txt" in dialog.attachments_label.text()

    dialog.comment_input.setPlainText("Please review this update @alice")
    dialog._post_comment()

    comments = store.list_comments("task-1")
    assert len(comments) == 1
    assert comments[0]["mentions"] == ["alice"]
    assert comments[0]["attachments"] == [str(attachment)]
    assert store.unread_mentions_count("alice") == 1
    assert dialog.activity_list.count() == 1
    assert "@alice" in dialog.activity_list.item(0).text()
    assert "proof.txt" in dialog.activity_list.item(0).text()

from __future__ import annotations

from datetime import date
from pathlib import Path

from PySide6.QtWidgets import QDialog

from core.domain.enums import TaskStatus
from infra.collaboration_store import TaskCollaborationStore
from tests.ui_runtime_helpers import make_settings_store
from ui.dashboard.tab import DashboardTab
from ui.report.dialog_gantt import GanttPreviewDialog
from ui.task.collaboration_dialog import TaskCollaborationDialog
from ui.task.tab import TaskTab


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
    assert "advanced:" in tab.task_search_filter.placeholderText()
    assert tab.task_view_combo.count() >= 1

    monkeypatch.setattr(
        "ui.task.filtering.QInputDialog.getText",
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
            "show_summary": True,
            "show_kpi": False,
            "show_evm": True,
            "show_burndown": True,
            "show_resource": True,
            "main_left_percent": 60,
            "chart_top_percent": 35,
            "left_order": ["summary", "evm", "kpi"],
            "chart_order": ["resource", "burndown"],
        }
    )
    monkeypatch.setattr("ui.dashboard.data_ops.run_refresh_dashboard_async", lambda *_args, **_kwargs: None)

    tab = DashboardTab(
        project_service=services["project_service"],
        dashboard_service=services["dashboard_service"],
        baseline_service=services["baseline_service"],
        settings_store=store,
        user_session=services["user_session"],
    )

    assert project.id == tab.project_combo.currentData()
    assert tab.btn_customize_dashboard.text() == "Customize Dashboard"
    assert tab.kpi_group.isHidden() is True
    assert tab._current_left_order()[:3] == ["summary", "evm", "kpi"]
    assert tab._current_chart_order()[:2] == ["resource", "burndown"]

    applied_payload = {
        "show_summary": True,
        "show_kpi": True,
        "show_evm": False,
        "show_burndown": False,
        "show_resource": True,
        "main_left_percent": 55,
        "chart_top_percent": 30,
        "left_order": ["kpi", "summary", "evm"],
        "chart_order": ["resource", "burndown"],
    }

    class _AcceptedLayoutDialog:
        def __init__(self, _parent, *, current_layout=None):
            self.current_layout = current_layout
            self.layout_payload = applied_payload

        def exec(self):
            return QDialog.Accepted

    monkeypatch.setattr("ui.dashboard.layout_state.DashboardLayoutDialog", _AcceptedLayoutDialog)
    tab._open_dashboard_layout_builder()

    assert store.load_dashboard_layout() == applied_payload
    assert tab._current_left_order()[:3] == ["kpi", "summary", "evm"]
    assert tab.evm_group.isHidden() is True
    assert tab.burndown_chart.isHidden() is True


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

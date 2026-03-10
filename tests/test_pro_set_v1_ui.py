from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_pro_set_tracker_is_persisted():
    text = (ROOT / "docs" / "PRO_SET_IMPLEMENTATION.md").read_text(encoding="utf-8", errors="ignore")
    assert "Implement the full Pro Set 1 to 7" in text
    assert "- [x] 1. Productivity UX core" in text
    assert "- [x] 7. Material Design 3 modernization" in text


def test_task_layout_has_bulk_and_collaboration_controls():
    text = (ROOT / "ui" / "task" / "layout.py").read_text(encoding="utf-8", errors="ignore")
    assert 'self.btn_bulk_status = QPushButton("Apply Status")' in text
    assert 'self.btn_bulk_delete = QPushButton("Bulk Delete")' in text
    assert 'self.btn_comments = QPushButton("Comments")' in text
    assert 'self.lbl_mentions = QLabel("Mentions: 0")' in text


def test_task_filtering_has_advanced_query_and_saved_views():
    text = (ROOT / "ui" / "task" / "filtering.py").read_text(encoding="utf-8", errors="ignore")
    assert "advanced: status:done priority>=70 progress<100" in text
    assert "self.task_view_combo = QComboBox()" in text
    assert "def _parse_advanced_task_query" in text
    assert "def _save_current_task_view" in text


def test_undo_stack_wired_into_task_tab():
    tab_text = (ROOT / "ui" / "task" / "tab.py").read_text(encoding="utf-8", errors="ignore")
    undo_text = (ROOT / "ui" / "shared" / "undo.py").read_text(encoding="utf-8", errors="ignore")
    bulk_text = (ROOT / "ui" / "task" / "bulk_actions.py").read_text(encoding="utf-8", errors="ignore")
    assert "self._undo_stack = UndoStack(max_depth=100)" in tab_text
    assert "class UndoStack" in undo_text
    assert "stack.push_and_execute(command)" in bulk_text


def test_gantt_dialog_uses_interactive_mixin():
    dialog_text = (ROOT / "ui" / "report" / "dialog_gantt.py").read_text(encoding="utf-8", errors="ignore")
    interactive_text = (ROOT / "ui" / "report" / "gantt_interactive.py").read_text(
        encoding="utf-8", errors="ignore"
    )
    interactive_actions_text = (ROOT / "ui" / "report" / "gantt_interactive_actions.py").read_text(
        encoding="utf-8", errors="ignore"
    )
    interactive_bar_text = (ROOT / "ui" / "report" / "gantt_interactive_bar.py").read_text(
        encoding="utf-8", errors="ignore"
    )
    assert "class GanttPreviewDialog(GanttInteractiveMixin, QDialog):" in dialog_text
    assert 'self.btn_open_interactive = QPushButton("Open Interactive")' in dialog_text
    assert "class GanttInteractiveMixin" in interactive_text
    assert "class _InteractiveGanttBar" in interactive_bar_text
    assert 'self.btn_toggle_grid = QPushButton("Grid: On")' in interactive_text
    assert "drag the right edge to change duration" in interactive_text
    assert 'self.btn_review_changes = QPushButton("Review Changes")' in interactive_text
    assert 'self.btn_undo_last_apply = QPushButton("Undo Last Apply")' in interactive_text
    assert "def _apply_single_edit_with_retry" in interactive_actions_text


def test_dashboard_builder_is_persisted():
    tab_text = (ROOT / "ui" / "dashboard" / "tab.py").read_text(encoding="utf-8", errors="ignore")
    state_text = (ROOT / "ui" / "dashboard" / "layout_state.py").read_text(
        encoding="utf-8", errors="ignore"
    )
    builder_text = (ROOT / "ui" / "dashboard" / "layout_builder.py").read_text(
        encoding="utf-8", errors="ignore"
    )
    assert 'self.btn_customize_dashboard = QPushButton("Customize Dashboard")' in tab_text
    assert "class DashboardLayoutStateMixin" in state_text
    assert "QDialog.Accepted" in state_text
    assert '"left_order"' in state_text
    assert '"chart_order"' in state_text
    assert "class DashboardLayoutDialog(QDialog):" in builder_text
    assert "QAbstractItemView.InternalMove" in builder_text


def test_collaboration_baseline_store_and_dialog_exist():
    store_text = (ROOT / "infra" / "collaboration_store.py").read_text(encoding="utf-8", errors="ignore")
    dialog_text = (ROOT / "ui" / "task" / "collaboration_dialog.py").read_text(
        encoding="utf-8", errors="ignore"
    )
    assert "class TaskCollaborationStore" in store_text
    assert "def unread_mentions_count" in store_text
    assert "def unread_mentions_count_for_users" in store_text
    assert "class TaskCollaborationDialog(QDialog):" in dialog_text
    assert "mention_aliases" in dialog_text
    assert "@username" in dialog_text

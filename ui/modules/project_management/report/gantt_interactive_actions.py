from __future__ import annotations

from datetime import datetime, timedelta

from PySide6.QtWidgets import QMessageBox

from core.platform.common.exceptions import ConcurrencyError
from ui.platform.shared.styles.ui_config import UIConfig as CFG


class GanttInteractiveActionsMixin:
    def _pending_task_name_map(self) -> dict[str, str]:
        bars = self._reporting_service.get_gantt_data(self._project_id)
        return {str(bar.task_id): str(bar.name) for bar in bars}

    def _sync_pending_label(self) -> None:
        if not self._interactive_pending_edits:
            self.lbl_pending.setText("No pending interactive edits.")
            self.btn_apply_changes.setEnabled(False)
            self.btn_reset_changes.setEnabled(False)
            self.btn_review_changes.setEnabled(False)
            return
        shift_count = sum(
            1
            for edit in self._interactive_pending_edits.values()
            if int(edit.get("shift", 0)) != 0
        )
        duration_count = sum(
            1
            for edit in self._interactive_pending_edits.values()
            if int(edit.get("duration_delta", 0)) != 0
        )
        self.lbl_pending.setText(
            f"Pending edits: {len(self._interactive_pending_edits)} task(s) | "
            f"shift: {shift_count}, duration: {duration_count}"
        )
        self.btn_apply_changes.setEnabled(self._can_edit)
        self.btn_reset_changes.setEnabled(True)
        self.btn_review_changes.setEnabled(True)

    def _format_edit_fragment(self, edit: dict[str, int]) -> str:
        shift_days = int(edit.get("shift", 0))
        duration_delta = int(edit.get("duration_delta", 0))
        shift_label = (
            f"start {'+' if shift_days >= 0 else ''}{shift_days}d"
            if shift_days
            else "start unchanged"
        )
        duration_label = (
            f"duration {'+' if duration_delta >= 0 else ''}{duration_delta}d"
            if duration_delta
            else "duration unchanged"
        )
        return f"{shift_label}, {duration_label}"

    def _pending_change_lines(self, *, limit: int = 10) -> list[str]:
        task_names = self._pending_task_name_map()
        rows = []
        for task_id, edit in self._interactive_pending_edits.items():
            name = task_names.get(task_id, task_id)
            rows.append((name.lower(), f"- {name}: {self._format_edit_fragment(edit)}"))
        rows.sort(key=lambda item: item[0])
        lines = [line for _, line in rows[:limit]]
        extra = len(rows) - len(lines)
        if extra > 0:
            lines.append(f"... and {extra} more task(s)")
        return lines

    def _review_pending_changes(self) -> None:
        if not self._interactive_pending_edits:
            QMessageBox.information(self, "Interactive Gantt", "There are no pending edits to review.")
            return
        lines = self._pending_change_lines(limit=14)
        body = "Pending interactive updates:\n\n" + "\n".join(lines)
        QMessageBox.information(self, "Review Changes", body)

    def _confirm_apply_pending_changes(self) -> bool:
        lines = self._pending_change_lines(limit=10)
        question = (
            f"Apply {len(self._interactive_pending_edits)} interactive edit(s)?\n\n"
            + "\n".join(lines)
        )
        decision = QMessageBox.question(
            self,
            "Apply Interactive Changes",
            question,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        return decision == QMessageBox.Yes

    @staticmethod
    def _resolve_task_duration(task) -> int:
        duration = task.duration_days
        if duration is not None:
            return max(1, int(duration))
        if task.end_date and task.start_date:
            return max(1, int((task.end_date - task.start_date).days + 1))
        return 1

    def _set_apply_status(self, message: str, *, is_warning: bool = False) -> None:
        color = CFG.COLOR_WARNING if is_warning else CFG.COLOR_TEXT_SECONDARY
        self.lbl_apply_status.setStyleSheet(f"color: {color}; font-size: 11px;")
        self.lbl_apply_status.setText(message)

    def _sync_undo_button(self) -> None:
        self.btn_undo_last_apply.setEnabled(bool(self._interactive_last_apply_snapshot) and self._can_edit)

    def _reset_drag_changes(self) -> None:
        self._interactive_pending_edits = {}
        self._build_interactive_timeline(keep_pending=False)

    def _apply_single_edit_with_retry(
        self,
        *,
        task_id: str,
        shift_days: int,
        duration_delta: int,
        attempts: int = 3,
    ) -> dict[str, object]:
        if self._task_service is None:
            raise RuntimeError("Task service is unavailable.")
        if attempts < 1:
            attempts = 1

        last_error: Exception | None = None
        for _attempt in range(attempts):
            task = self._task_service.get_task(task_id)
            if task is None or task.start_date is None:
                raise RuntimeError(task_id)

            base_duration = self._resolve_task_duration(task)
            new_duration = max(1, int(base_duration) + duration_delta)
            old_start = task.start_date
            old_duration = int(base_duration)
            try:
                self._task_service.update_task(
                    task_id=task.id,
                    start_date=old_start + timedelta(days=shift_days),
                    duration_days=new_duration,
                )
                return {
                    "task_id": task.id,
                    "task_name": task.name or task.id,
                    "start_date": old_start,
                    "duration_days": old_duration,
                }
            except ConcurrencyError as exc:
                last_error = exc
                continue
        raise last_error or ConcurrencyError("Task was updated by another user.", code="STALE_WRITE")

    def _restore_snapshot_with_retry(self, row: dict[str, object], attempts: int = 3) -> None:
        if self._task_service is None:
            raise RuntimeError("Task service is unavailable.")
        if attempts < 1:
            attempts = 1

        task_id = str(row.get("task_id") or "")
        start_date = row.get("start_date")
        duration_days = int(row.get("duration_days") or 1)
        if not task_id or start_date is None:
            raise RuntimeError("Missing snapshot payload.")

        last_error: Exception | None = None
        for _attempt in range(attempts):
            try:
                self._task_service.update_task(
                    task_id=task_id,
                    start_date=start_date,
                    duration_days=max(1, duration_days),
                )
                return
            except ConcurrencyError as exc:
                last_error = exc
                continue
        raise last_error or ConcurrencyError("Task was updated by another user.", code="STALE_WRITE")

    def _apply_drag_changes(self) -> None:
        if not self._interactive_pending_edits:
            return
        if self._task_service is None:
            QMessageBox.warning(self, "Interactive Gantt", "Task service is unavailable.")
            return
        if not self._confirm_apply_pending_changes():
            return

        failures: list[str] = []
        applied = 0
        applied_snapshot: list[dict[str, object]] = []
        for task_id, edit in list(self._interactive_pending_edits.items()):
            shift_days = int(edit.get("shift", 0))
            duration_delta = int(edit.get("duration_delta", 0))
            if shift_days == 0 and duration_delta == 0:
                continue
            try:
                snapshot_row = self._apply_single_edit_with_retry(
                    task_id=task_id,
                    shift_days=shift_days,
                    duration_delta=duration_delta,
                )
                applied_snapshot.append(snapshot_row)
                applied += 1
            except Exception:
                failures.append(str(task_id))

        self._interactive_pending_edits.clear()
        if applied_snapshot:
            self._interactive_last_apply_snapshot = applied_snapshot
        self._load_image()
        self._sync_undo_button()

        timestamp = datetime.now().strftime("%H:%M:%S")
        if failures:
            preview = ", ".join(failures[:5]) + ("..." if len(failures) > 5 else "")
            self._set_apply_status(
                f"{timestamp} - Applied {applied} update(s), {len(failures)} failed: {preview}",
                is_warning=True,
            )
            QMessageBox.warning(
                self,
                "Interactive Gantt",
                f"Applied {applied} task update(s). Failed for {len(failures)} task(s): {preview}",
            )
            return
        self._set_apply_status(f"{timestamp} - Applied {applied} interactive update(s).")
        QMessageBox.information(self, "Interactive Gantt", f"Applied {applied} interactive update(s).")

    def _undo_last_apply(self) -> None:
        if not self._interactive_last_apply_snapshot:
            return
        decision = QMessageBox.question(
            self,
            "Undo Last Apply",
            f"Undo the last applied interactive batch ({len(self._interactive_last_apply_snapshot)} task(s))?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if decision != QMessageBox.Yes:
            return

        failures: list[str] = []
        restored = 0
        remaining_snapshot: list[dict[str, object]] = []
        for row in list(self._interactive_last_apply_snapshot):
            task_name = str(row.get("task_name") or row.get("task_id") or "<unknown>")
            try:
                self._restore_snapshot_with_retry(row)
                restored += 1
            except Exception:
                failures.append(task_name)
                remaining_snapshot.append(row)

        self._interactive_last_apply_snapshot = remaining_snapshot
        self._load_image()
        self._sync_undo_button()
        timestamp = datetime.now().strftime("%H:%M:%S")
        if failures:
            preview = ", ".join(failures[:5]) + ("..." if len(failures) > 5 else "")
            self._set_apply_status(
                f"{timestamp} - Undo restored {restored}, {len(failures)} failed: {preview}",
                is_warning=True,
            )
            QMessageBox.warning(
                self,
                "Interactive Gantt",
                f"Undo restored {restored} task(s). Failed for {len(failures)} task(s): {preview}",
            )
            return
        self._set_apply_status(f"{timestamp} - Undo restored {restored} task(s).")
        QMessageBox.information(self, "Interactive Gantt", f"Undo restored {restored} task(s).")


__all__ = ["GanttInteractiveActionsMixin"]

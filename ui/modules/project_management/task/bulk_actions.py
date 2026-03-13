from __future__ import annotations

from PySide6.QtWidgets import QInputDialog, QMessageBox

from core.modules.project_management.domain.enums import TaskStatus
from ui.platform.shared.undo import UndoCommand


class TaskBulkActionsMixin:
    def apply_bulk_status(self) -> None:
        tasks = list(getattr(self, "_get_selected_tasks", lambda: [])())
        if not tasks:
            QMessageBox.information(self, "Bulk status", "Select one or more tasks first.")
            return
        raw_status = str(getattr(self.bulk_status_combo, "currentData", lambda: "")() or "").strip()
        try:
            target_status = TaskStatus(raw_status)
        except ValueError:
            QMessageBox.warning(self, "Bulk status", "Choose a valid target status.")
            return

        changes: list[tuple[str, TaskStatus, TaskStatus]] = []
        for task in tasks:
            current_status = getattr(task, "status", TaskStatus.TODO)
            if current_status == target_status:
                continue
            changes.append((task.id, current_status, target_status))
        if not changes:
            QMessageBox.information(self, "Bulk status", "Selected tasks already have this status.")
            return

        reopened_count = sum(
            1 for _, old_status, _ in changes if old_status == TaskStatus.DONE and target_status != TaskStatus.DONE
        )
        reopen_percent: float | None = None
        if reopened_count:
            decision = QMessageBox.question(
                self,
                "Bulk status",
                f"{reopened_count} completed task(s) will be reopened. Continue?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if decision != QMessageBox.Yes:
                return
            if target_status == TaskStatus.IN_PROGRESS:
                percent, ok = QInputDialog.getDouble(
                    self,
                    "Bulk status",
                    "Set completion % for reopened tasks:",
                    50.0,
                    1.0,
                    99.0,
                    1,
                )
                if not ok:
                    return
                reopen_percent = float(percent)

        def _apply(target_idx: int) -> None:
            for task_id, old_status, new_status in changes:
                status = (old_status, new_status)[target_idx]
                if (
                    target_idx == 1
                    and reopen_percent is not None
                    and old_status == TaskStatus.DONE
                    and new_status == TaskStatus.IN_PROGRESS
                ):
                    self._task_service.update_progress(
                        task_id=task_id,
                        status=TaskStatus.IN_PROGRESS,
                        percent_complete=reopen_percent,
                    )
                else:
                    self._task_service.set_status(task_id, status)

        label = f"Bulk status -> {target_status.value} ({len(changes)} tasks)"
        command = UndoCommand(
            label=label,
            redo=lambda: _apply(1),
            undo=lambda: _apply(0),
        )
        stack = getattr(self, "_undo_stack", None)
        if stack is not None and hasattr(stack, "push_and_execute"):
            try:
                stack.push_and_execute(command)
                self._sync_undo_redo_state()
            except Exception as exc:
                QMessageBox.warning(self, "Bulk status", str(exc))
                return
        else:
            try:
                command.redo()
            except Exception as exc:
                QMessageBox.warning(self, "Bulk status", str(exc))
                return
        self.reload_tasks()

    def bulk_delete_tasks(self) -> None:
        tasks = list(getattr(self, "_get_selected_tasks", lambda: [])())
        if not tasks:
            QMessageBox.information(self, "Bulk delete", "Select one or more tasks first.")
            return
        if len(tasks) == 1:
            self.delete_task()
            return
        confirm = QMessageBox.question(
            self,
            "Bulk delete tasks",
            (
                f"Delete {len(tasks)} selected tasks and their dependencies/assignments?\n\n"
                "This action cannot be undone."
            ),
        )
        if confirm != QMessageBox.Yes:
            return
        deleted = 0
        failed: list[str] = []
        for task in tasks:
            try:
                self._task_service.delete_task(task.id)
                deleted += 1
            except Exception:
                failed.append(task.name)
        self.reload_tasks()
        if failed:
            preview = ", ".join(failed[:4]) + ("..." if len(failed) > 4 else "")
            QMessageBox.warning(
                self,
                "Bulk delete tasks",
                f"Deleted {deleted} task(s). Failed: {len(failed)} ({preview})",
            )
            return
        QMessageBox.information(self, "Bulk delete tasks", f"Deleted {deleted} task(s).")

    def undo_last_task_action(self) -> None:
        stack = getattr(self, "_undo_stack", None)
        if stack is None:
            return
        try:
            label = stack.undo()
        except Exception as exc:
            QMessageBox.warning(self, "Undo", str(exc))
            return
        if label:
            self.reload_tasks()
        self._sync_undo_redo_state()

    def redo_last_task_action(self) -> None:
        stack = getattr(self, "_undo_stack", None)
        if stack is None:
            return
        try:
            label = stack.redo()
        except Exception as exc:
            QMessageBox.warning(self, "Redo", str(exc))
            return
        if label:
            self.reload_tasks()
        self._sync_undo_redo_state()


__all__ = ["TaskBulkActionsMixin"]

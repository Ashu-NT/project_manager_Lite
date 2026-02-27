from __future__ import annotations

from ui.dashboard.workqueue_dialogs import (
    DashboardAlertsDialog,
    DashboardConflictsDialog,
    DashboardUpcomingDialog,
)


class DashboardWorkqueueActionsMixin:
    _alerts_dialog: DashboardAlertsDialog | None
    _conflicts_dialog: DashboardConflictsDialog | None
    _upcoming_dialog: DashboardUpcomingDialog | None
    _current_alert_rows: list[tuple[str, str, str]]
    _current_alert_summary: str
    _current_upcoming_rows: list[dict[str, object]]

    def _prepare_conflicts_dialog(self) -> None:
        if self._conflicts_dialog is not None:
            return
        panel = self._build_conflicts_panel()
        self._conflicts_dialog = DashboardConflictsDialog(panel, self)
        self.btn_preview_conflicts.clicked.connect(self._preview_conflicts)
        self.btn_auto_level.clicked.connect(self._auto_level_conflicts)
        self.btn_manual_shift.clicked.connect(self._manual_shift_selected_conflict)
        self.conflicts_table.itemSelectionChanged.connect(self._sync_leveling_buttons)

    def _open_alerts_dialog(self) -> None:
        if self._alerts_dialog is None:
            self._alerts_dialog = DashboardAlertsDialog(self)
        self._alerts_dialog.set_alert_rows(
            self._current_alert_rows,
            self._current_alert_summary,
        )
        self._alerts_dialog.show()
        self._alerts_dialog.raise_()
        self._alerts_dialog.activateWindow()

    def _open_upcoming_dialog(self) -> None:
        if not self._current_upcoming_rows and getattr(self, "_current_data", None) is not None:
            self._update_upcoming(self._current_data)
        if self._upcoming_dialog is None:
            self._upcoming_dialog = DashboardUpcomingDialog(self)
        self._upcoming_dialog.set_upcoming_rows(self._current_upcoming_rows)
        self._upcoming_dialog.show()
        self._upcoming_dialog.raise_()
        self._upcoming_dialog.activateWindow()

    def _open_conflicts_dialog(self) -> None:
        self._prepare_conflicts_dialog()
        self._sync_leveling_buttons()
        self._conflicts_dialog.show()
        self._conflicts_dialog.raise_()
        self._conflicts_dialog.activateWindow()


__all__ = ["DashboardWorkqueueActionsMixin"]

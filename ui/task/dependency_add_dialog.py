from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHeaderView,
    QLabel,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from core.models import DependencyType, Task
from core.services.task import TaskService
from core.services.task.dependency_diagnostics import DependencyImpactRow
from ui.styles.style_utils import style_table
from ui.styles.ui_config import UIConfig as CFG
from ui.task.dependency_shared import REL_CURRENT_DEPENDS, REL_OTHER_DEPENDS


class DependencyAddDialog(QDialog):
    def __init__(
        self,
        parent=None,
        tasks: list[Task] | None = None,
        current_task: Task | None = None,
        task_service: TaskService | None = None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Add Dependency")
        self._tasks = sorted(tasks or [], key=lambda t: t.name.lower())
        self._current = current_task or (self._tasks[0] if self._tasks else None)
        self._task_service = task_service

        self.lbl_info = QLabel()
        self.lbl_info.setWordWrap(True)
        self.lbl_info.setStyleSheet(CFG.INFO_TEXT_STYLE)

        self.lbl_diag = QLabel()
        self.lbl_diag.setWordWrap(True)
        self.lbl_diag.setStyleSheet(
            f"background-color: {CFG.COLOR_BG_SURFACE_ALT}; "
            f"border: 1px solid {CFG.COLOR_BORDER}; "
            f"border-radius: 8px; padding: 10px; "
            f"color: {CFG.COLOR_TEXT_PRIMARY}; font-size: 10pt;"
        )

        self.cmb_relation = QComboBox()
        self.cmb_relation.addItem("Current task depends on other task", REL_CURRENT_DEPENDS)
        self.cmb_relation.addItem("Other task depends on current task", REL_OTHER_DEPENDS)

        self.cmb_other = QComboBox()
        for task in self._tasks:
            if self._current and task.id == self._current.id:
                continue
            self.cmb_other.addItem(task.name, task.id)

        self._types: list[DependencyType] = [
            DependencyType.FINISH_TO_START,
            DependencyType.START_TO_START,
            DependencyType.FINISH_TO_FINISH,
            DependencyType.START_TO_FINISH,
        ]
        self.cmb_type = QComboBox()
        for dep_type in self._types:
            self.cmb_type.addItem(dep_type.value, dep_type)

        self.spin_lag = QSpinBox()
        self.spin_lag.setMinimum(CFG.LAG_MIN)
        self.spin_lag.setMaximum(CFG.LAG_MAX)

        self.lbl_impact = QLabel("Predicted Schedule Impact")
        self.lbl_impact.setStyleSheet(
            f"font-weight: 700; color: {CFG.COLOR_TEXT_PRIMARY}; font-size: 10pt;"
        )

        self.impact_table = QTableWidget(0, 3)
        self.impact_table.setHorizontalHeaderLabels(["Impacted Task", "Start Shift", "Finish Shift"])
        self.impact_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.impact_table.setSelectionMode(QTableWidget.NoSelection)
        style_table(self.impact_table)

        header = self.impact_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)

        form = QFormLayout()
        form.setLabelAlignment(CFG.ALIGN_RIGHT | CFG.ALIGN_CENTER)
        form.setFormAlignment(CFG.ALIGN_TOP)
        form.setHorizontalSpacing(CFG.SPACING_MD)
        form.setVerticalSpacing(CFG.SPACING_SM)
        form.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        form.addRow("Current task", QLabel(self._current.name if self._current else "-"))
        form.addRow("Relationship", self.cmb_relation)
        form.addRow("Other task", self.cmb_other)
        form.addRow("Type", self.cmb_type)
        form.addRow("Lag (days)", self.spin_lag)

        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.setSpacing(CFG.SPACING_MD)
        layout.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)
        layout.addWidget(self.lbl_info)
        layout.addLayout(form)
        layout.addWidget(self.lbl_diag)
        layout.addWidget(self.lbl_impact)
        layout.addWidget(self.impact_table, 1)
        layout.addWidget(self.buttons)

        self.setMinimumSize(760, 460)
        self.resize(860, 520)

        self.cmb_relation.currentIndexChanged.connect(self._refresh_diagnostics)
        self.cmb_other.currentIndexChanged.connect(self._refresh_diagnostics)
        self.cmb_type.currentIndexChanged.connect(self._refresh_diagnostics)
        self.spin_lag.valueChanged.connect(self._refresh_diagnostics)

        if self.cmb_other.count() == 0:
            self.lbl_info.setText("At least two tasks are required to create a dependency.")
            self.buttons.button(QDialogButtonBox.Ok).setEnabled(False)
        else:
            self.lbl_info.setText(
                "Use predecessor/successor direction to model task sequencing clearly."
            )
            self._refresh_diagnostics()

    @property
    def predecessor_id(self) -> str:
        other = self.cmb_other.currentData()
        if self.cmb_relation.currentData() == REL_CURRENT_DEPENDS:
            return other
        return self._current.id

    @property
    def successor_id(self) -> str:
        other = self.cmb_other.currentData()
        if self.cmb_relation.currentData() == REL_CURRENT_DEPENDS:
            return self._current.id
        return other

    @property
    def dependency_type(self) -> DependencyType:
        return self._types[self.cmb_type.currentIndex()]

    @property
    def lag_days(self) -> int:
        return self.spin_lag.value()

    def _refresh_diagnostics(self) -> None:
        ok_btn = self.buttons.button(QDialogButtonBox.Ok)
        if self.cmb_other.count() == 0 or not self._current:
            self.lbl_diag.setText("")
            self._render_impact_rows([])
            ok_btn.setEnabled(False)
            return

        if self._task_service is None:
            self.lbl_diag.setText("Validation preview unavailable.")
            self._render_impact_rows([])
            ok_btn.setEnabled(True)
            return

        diag = self._task_service.get_dependency_diagnostics(
            predecessor_id=self.predecessor_id,
            successor_id=self.successor_id,
            dependency_type=self.dependency_type,
            lag_days=self.lag_days,
            include_impact=True,
        )
        risk = str(getattr(diag, "risk_level", "unknown")).upper()
        status = ("Ready to apply" if diag.is_valid else "Validation issue") + f" | Risk: {risk}"
        status_color = CFG.COLOR_SUCCESS if diag.is_valid else CFG.COLOR_DANGER
        lines = [f"<b style='color:{status_color};'>{status}</b>", f"<b>{diag.summary}</b>"]
        if diag.detail:
            lines.append(diag.detail)
        if diag.suggestions:
            lines.extend(f"- {text}" for text in diag.suggestions[:2])

        self.lbl_diag.setText("\n".join(lines))
        self._render_impact_rows(diag.impact_rows)
        self.lbl_impact.setText(f"Predicted Schedule Impact ({len(diag.impact_rows)} task(s))")
        ok_btn.setEnabled(diag.is_valid)

    def _render_impact_rows(self, rows: list[DependencyImpactRow]) -> None:
        shown = rows[:12]
        self.impact_table.setRowCount(len(shown))
        for r, row in enumerate(shown):
            values = (
                row.task_name,
                self._format_shift(row.start_shift_days),
                self._format_shift(row.finish_shift_days),
            )
            for c, value in enumerate(values):
                item = QTableWidgetItem(value)
                if c in (1, 2):
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    if value.startswith("+"):
                        item.setForeground(QColor(CFG.COLOR_DANGER))
                    elif value.startswith("-"):
                        item.setForeground(QColor(CFG.COLOR_SUCCESS))
                if c == 0 and row.trace_path:
                    item.setToolTip(f"Dependency chain: {row.trace_path}")
                self.impact_table.setItem(r, c, item)

    @staticmethod
    def _format_shift(days: int | None) -> str:
        if days is None:
            return "-"
        return f"{days:+d}d"

__all__ = ["DependencyAddDialog"]

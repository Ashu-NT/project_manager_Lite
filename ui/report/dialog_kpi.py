from __future__ import annotations

from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from core.services.reporting import ReportingService
from ui.report.dialog_helpers import metric_card, section_group, setup_dialog_size
from ui.styles.ui_config import UIConfig as CFG


class KPIReportDialog(QDialog):
    def __init__(self, parent, reporting_service: ReportingService, project_id: str):
        super().__init__(parent)
        self._reporting_service: ReportingService = reporting_service
        self._project_id: str = project_id
        self.setWindowTitle("Project KPIs")
        self._setup_ui()

    def _setup_ui(self):
        kpi = self._reporting_service.get_project_kpis(self._project_id)
        layout = QVBoxLayout(self)
        layout.setSpacing(CFG.SPACING_MD)
        layout.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)
        setup_dialog_size(self, 860, 540, 980, 680)

        title = QLabel(f"Project KPIs - {kpi.name}")
        title.setStyleSheet(CFG.TITLE_LARGE_STYLE)
        layout.addWidget(title)

        subtitle = QLabel(
            "Snapshot of schedule, task execution, and cost performance for this project."
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet(CFG.INFO_TEXT_STYLE)
        layout.addWidget(subtitle)

        completion_pct = (100.0 * kpi.tasks_completed / kpi.tasks_total) if kpi.tasks_total else 0.0
        variance_color = CFG.COLOR_DANGER if kpi.cost_variance > 0 else CFG.COLOR_SUCCESS

        cards_row = QHBoxLayout()
        cards_row.setSpacing(CFG.SPACING_SM)
        cards_row.addWidget(
            metric_card(
                "Task Completion",
                f"{completion_pct:.1f}%",
                f"{kpi.tasks_completed} done / {kpi.tasks_total} total",
                CFG.COLOR_ACCENT,
            )
        )
        cards_row.addWidget(
            metric_card(
                "Critical Tasks",
                str(kpi.critical_tasks),
                "Tasks with zero total float",
                CFG.COLOR_WARNING,
            )
        )
        cards_row.addWidget(
            metric_card(
                "Late Tasks",
                str(kpi.late_tasks),
                "Tasks currently behind schedule",
                CFG.COLOR_DANGER,
            )
        )
        cards_row.addWidget(
            metric_card(
                "Cost Variance",
                f"{kpi.cost_variance:.2f}",
                "Actual - Planned",
                variance_color,
            )
        )
        layout.addLayout(cards_row)

        details_row = QHBoxLayout()
        details_row.setSpacing(CFG.SPACING_SM)
        details_row.addWidget(
            section_group(
                "Schedule",
                [
                    ("Start date:", kpi.start_date.isoformat() if kpi.start_date else "-"),
                    ("End date:", kpi.end_date.isoformat() if kpi.end_date else "-"),
                    (
                        "Duration (working days):",
                        str(kpi.duration_working_days) if kpi.duration_working_days is not None else "-",
                    ),
                ],
            )
        )
        details_row.addWidget(
            section_group(
                "Task Breakdown",
                [
                    ("Total tasks:", str(kpi.tasks_total)),
                    ("Completed:", str(kpi.tasks_completed)),
                    ("In progress:", str(kpi.tasks_in_progress)),
                    ("Blocked:", str(kpi.task_blocked)),
                    ("Not started:", str(kpi.tasks_not_started)),
                ],
            )
        )
        details_row.addWidget(
            section_group(
                "Cost Overview",
                [
                    ("Planned:", f"{kpi.total_planned_cost:.2f}"),
                    ("Committed:", f"{kpi.total_committed_cost:.2f}"),
                    ("Actual:", f"{kpi.total_actual_cost:.2f}"),
                    ("Variance:", f"{kpi.cost_variance:.2f}"),
                ],
            )
        )
        layout.addLayout(details_row)

        hint = QLabel(
            "Use Excel/PDF exports from the Reports tab when you need printable reporting packages."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet(CFG.INFO_TEXT_STYLE)
        layout.addWidget(hint)

        btn_close = QPushButton(CFG.CLOSE_BUTTON_LABEL)
        btn_close.setMinimumHeight(CFG.BUTTON_HEIGHT)
        btn_close.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
        btn_close.clicked.connect(self.accept)
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(btn_close)
        layout.addLayout(btn_row)

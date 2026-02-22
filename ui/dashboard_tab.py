# ui/dashboard_tab.py
from __future__ import annotations
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton,
    QGroupBox, QListWidget, QListWidgetItem, QTableWidget, QTableWidgetItem,
    QHeaderView,QGridLayout,QMessageBox,QInputDialog
)
from ui.styles.style_utils import style_table
from ui.styles.formatting import fmt_int, fmt_float, fmt_percent
from core.services.project_service import ProjectService
from core.services.dashboard_service import DashboardService, DashboardData
from core.services.baseline_service import BaselineService

# Matplotlib embedding
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from ui.styles.formatting import fmt_ratio, fmt_money
from ui.styles.ui_config import UIConfig as CFG
from core.events.domain_events import domain_events

class DashboardTab(QWidget):
    """
    Modern SaaS-style dashboard:
    - Project summary & KPI tiles
    - Burndown chart
    - Resource load chart
    - Alerts panel
    - Upcoming tasks table
    """
    def __init__(
        self,
        project_service: ProjectService,
        dashboard_service: DashboardService,
        baseline_service: BaselineService,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._project_service = project_service
        self._dashboard_service = dashboard_service
        self._baseline_service = baseline_service

        self._current_data: Optional[DashboardData] = None

        self._setup_ui()
        self.reload_projects()
        domain_events.costs_changed.connect(self._on_domain_changed)
        domain_events.tasks_changed.connect(self._on_domain_changed)
        domain_events.project_changed.connect(self._on_domain_changed)

    # --------------------------------------------------------------
    # UI setup
    # --------------------------------------------------------------

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(CFG.SPACING_XS)
        layout.setContentsMargins(
            CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD
        )

        # Project selection
        top = QHBoxLayout()
        top.addSpacing(CFG.SPACING_MD)
        
        top.addWidget(QLabel("Project:"))
        self.project_combo = QComboBox()
        self.project_combo.setSizePolicy(CFG.INPUT_POLICY)
        self.project_combo.setFixedHeight(CFG.INPUT_HEIGHT)
        self.project_combo.setEditable(CFG.COMBO_EDITABLE)
        self.project_combo.setMaxVisibleItems(CFG.COMBO_MAX_VISIBLE)
        
        self.btn_reload_projects = QPushButton(CFG.RELOAD_BUTTON_LABEL)
        self.btn_refresh_dashboard = QPushButton(CFG.REFRESH_DASHBOARD_LABEL)
        
        self.baseline_combo = QComboBox()
        self.baseline_combo.setSizePolicy(CFG.INPUT_POLICY)
        self.baseline_combo.setFixedHeight(CFG.INPUT_HEIGHT)
        self.baseline_combo.setEditable(CFG.COMBO_EDITABLE)
        self.baseline_combo.setMaxVisibleItems(CFG.COMBO_MAX_VISIBLE)

        self.btn_create_baseline = QPushButton(CFG.CREATE_BASELINE_LABEL)
        self.btn_delete_baseline = QPushButton(CFG.DELETE_BASELINE_LABEL)
        
        for btn in(
            self.btn_reload_projects,
            self.btn_refresh_dashboard,
            self.btn_create_baseline,
            self.btn_delete_baseline,
        ):
            btn.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
            btn.setFixedHeight(CFG.BUTTON_HEIGHT)

        top.addWidget(self.project_combo)
        top.addWidget(self.btn_reload_projects)
        top.addWidget(self.btn_refresh_dashboard)
        top.addStretch()
        top.addWidget(QLabel("Baseline:"))
        top.addWidget(self.baseline_combo)
        top.addWidget(self.btn_create_baseline)
        top.addWidget(self.btn_delete_baseline)
        layout.addLayout(top)

        # Summary + KPI tiles
        # Project summary: boxed title + compact meta chips (start / end / duration)
        self.summary_widget = QWidget()
        self.summary_widget.setStyleSheet(CFG.PROJECT_SUMMARY_BOX_STYLE)
        s_layout = QHBoxLayout(self.summary_widget)
        s_layout.setContentsMargins(CFG.SPACING_XS, CFG.SPACING_XS, CFG.SPACING_XS, CFG.SPACING_XS)
        s_layout.setSpacing(CFG.SPACING_SM)

        # Compact group: prefix + title (kept tightly together)
        self.prefix_title_widget = QWidget()
        pt_layout = QHBoxLayout(self.prefix_title_widget)
        pt_layout.setContentsMargins(0, 0, 0, 0)
        pt_layout.setSpacing(CFG.SPACING_XS)
        # Keep the prefix+title compact and not expanding so the meta chips remain adjacent
        self.prefix_title_widget.setSizePolicy(CFG.FIXED_BOTH)

        self.project_label_prefix = QLabel(CFG.DASHBOARD_PROJECT_LABEL)
        self.project_label_prefix.setStyleSheet(CFG.DASHBOARD_PROJECT_LABEL_STYLE)
        self.project_label_prefix.setTextInteractionFlags(Qt.TextSelectableByMouse)
        # reduce height only
        self.project_label_prefix.setFixedHeight(CFG.DASHBOARD_PROJECT_ITEM_HEIGHT)

        self.project_title_lbl = QLabel("")
        self.project_title_lbl.setStyleSheet(CFG.DASHBOARD_PROJECT_TITLE_STYLE)
        self.project_title_lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
        # Constrain title width so it does not push meta chips to the far right
        self.project_title_lbl.setMinimumWidth(160)
        # reduce height only
        self.project_title_lbl.setFixedHeight(CFG.DASHBOARD_PROJECT_ITEM_HEIGHT)

        pt_layout.addWidget(self.project_label_prefix)
        pt_layout.addWidget(self.project_title_lbl)
        # Make the title a reasonable max width so it does not force chips away
        self.project_title_lbl.setMaximumWidth(300)

        meta_widget = QWidget()
        meta_layout = QHBoxLayout(meta_widget)
        meta_layout.setContentsMargins(0, 0, 0, 0)
        meta_layout.setSpacing(CFG.SPACING_XS)

        self.project_meta_start = QLabel("")
        self.project_meta_start.setStyleSheet(CFG.DASHBOARD_PROJECT_META_STYLE)
        # reduce height only
        self.project_meta_start.setFixedHeight(CFG.DASHBOARD_PROJECT_ITEM_HEIGHT)
        self.project_meta_end = QLabel("")
        self.project_meta_end.setStyleSheet(CFG.DASHBOARD_PROJECT_META_STYLE)
        self.project_meta_end.setFixedHeight(CFG.DASHBOARD_PROJECT_ITEM_HEIGHT)
        self.project_meta_duration = QLabel("")
        self.project_meta_duration.setStyleSheet(CFG.DASHBOARD_PROJECT_META_STYLE)
        self.project_meta_duration.setFixedHeight(CFG.DASHBOARD_PROJECT_ITEM_HEIGHT)

        meta_layout.addWidget(self.project_meta_start)
        meta_layout.addWidget(self.project_meta_end)
        meta_layout.addWidget(self.project_meta_duration)

        # Add the compact prefix+title and then the meta chips (kept close with small spacing)
        s_layout.addWidget(self.prefix_title_widget)
        s_layout.addSpacing(CFG.SPACING_XS)
        s_layout.addWidget(meta_widget)
        meta_widget.setSizePolicy(CFG.FIXED_BOTH)

        layout.addWidget(self.summary_widget)

        kpi_group = QGroupBox()
        kpi_layout = QHBoxLayout(kpi_group)
        kpi_layout.setSpacing(CFG.SPACING_XS)

        self.kpi_tasks = KpiCard("Tasks", "0 / 0", "Completed / Total")
        self.kpi_critical = KpiCard("Critical tasks", "0", "", "#f5a623")
        self.kpi_late = KpiCard("Late tasks", "0", "", "#d0021b")
        self.kpi_cost = KpiCard("Cost variance", "0.00", "Actual - Planned", "#4a90e2")
        self.kpi_progress = KpiCard("% complete", "0%", "", "#7ed321")

        kpi_layout.addWidget(self.kpi_tasks)
        kpi_layout.addWidget(self.kpi_critical)
        kpi_layout.addWidget(self.kpi_late)
        kpi_layout.addWidget(self.kpi_cost)
        kpi_layout.addWidget(self.kpi_progress)
        layout.addWidget(kpi_group)
        
        #EVM panel (Earned Value)
        self.evm_group = self._build_evm_panel()
        layout.addWidget(self.evm_group)
        
        # Charts row
        charts_row = QHBoxLayout()
        self.burndown_chart = ChartWidget("Burndown (remaining tasks)")
        self.resource_chart = ChartWidget("Resource load (allocation %)")

        charts_row.addWidget(self.burndown_chart)
        charts_row.addWidget(self.resource_chart)
        layout.addLayout(charts_row)

        # Alerts + upcoming tasks
        bottom_row = QHBoxLayout()

        # Alerts panel
        alerts_group = QGroupBox("Alerts")
        alerts_group.setFont(CFG.GROUPBOX_TITLE_FONT)
        alerts_layout = QVBoxLayout(alerts_group)
        self.alerts_list = QListWidget()
        alerts_layout.addWidget(self.alerts_list)
        bottom_row.addWidget(alerts_group, 1)

        # Upcoming tasks table
        upcoming_group = QGroupBox("Upcoming tasks (next 14 days)")
        upcoming_group.setFont(CFG.GROUPBOX_TITLE_FONT)
        up_layout = QVBoxLayout(upcoming_group)
        up_layout.addSpacing(CFG.SPACING_XS)
        
        self.upcoming_table = QTableWidget(0, len(CFG.UPCOMING_TASKS_HEADERS))
        self.upcoming_table.setHorizontalHeaderLabels(CFG.UPCOMING_TASKS_HEADERS)
        self.upcoming_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        style_table(self.upcoming_table)
        up_layout.addWidget(self.upcoming_table)
        bottom_row.addWidget(upcoming_group, 2)

        layout.addLayout(bottom_row)
        layout.addStretch()

        # Signals
        self.btn_reload_projects.clicked.connect(self.reload_projects)
        self.btn_refresh_dashboard.clicked.connect(self.refresh_dashboard)
        self.btn_create_baseline.clicked.connect(self._generate_baseline) 
        self.btn_delete_baseline.clicked.connect(self._delete_selected_baseline)
        
        self.project_combo.currentIndexChanged.connect(self._on_project_changed)
        self.baseline_combo.currentIndexChanged.connect(self.refresh_dashboard)

    # --------------------------------------------------------------
    # Data loading
    # --------------------------------------------------------------
    def _generate_baseline(self):
        proj_id, _ = self._current_project_id_and_name()
        if not proj_id:
            return

        name, ok = QInputDialog.getText(self, "Create Baseline", "Baseline name:", text="Baseline")
        if not ok:
            return

        try:
            self._baseline_service.create_baseline(proj_id, name.strip() or "Baseline")
            self._load_baselines_for_project(proj_id)

            # auto-select the newest (or stay on Latest)
            self.baseline_combo.setCurrentIndex(0)

            self.refresh_dashboard()
        except Exception as e:
            QMessageBox.critical(self, "Baseline error", f"Could not create baseline:\n{e}")
    
    def _on_domain_changed(self, project_id: str):
        current_id, _ = self._current_project_id_and_name()
        if current_id == project_id:
            self.reload_projects()
    
    def _on_project_changed(self, index: int = 0):
        proj_id, _ = self._current_project_id_and_name()
        if proj_id:
            self._load_baselines_for_project(proj_id)
            self.baseline_combo.setCurrentIndex(0)  # "Latest baseline"
        self.refresh_dashboard()
    
    def reload_projects(self):
        previous_id, _ = self._current_project_id_and_name()
        self.project_combo.blockSignals(True)
        self.project_combo.clear()
        projects = self._project_service.list_projects()
        for p in projects:
            self.project_combo.addItem(p.name, userData=p.id)
        selected_id = None
        if projects:
            if previous_id and any(p.id == previous_id for p in projects):
                selected_id = previous_id
            else:
                selected_id = projects[0].id
            idx = self.project_combo.findData(selected_id)
            if idx >= 0:
                self.project_combo.setCurrentIndex(idx)
        self.project_combo.blockSignals(False)

        if not projects:
            # no projects: clear baseline dropdown too
            self.baseline_combo.clear()
            self.baseline_combo.addItem("Latest baseline", userData=None)
            self._clear_dashboard()
            return

        if selected_id:
            self._load_baselines_for_project(selected_id)
            self.baseline_combo.setCurrentIndex(0)
        self.refresh_dashboard()

    def _current_project_id_and_name(self):
        idx = self.project_combo.currentIndex()
        if idx < 0:
            return None, None
        return self.project_combo.itemData(idx), self.project_combo.currentText()

    def refresh_dashboard(self):
        proj_id, proj_name = self._current_project_id_and_name()
        
        if not proj_id:
            self._clear_dashboard()
            return
        try:
            baseline_id = self._selected_baseline_id() if hasattr(self, "baseline_combo") else None
            data = self._dashboard_service.get_dashboard_data(proj_id, baseline_id=baseline_id)
            if not hasattr(self,"evm_hint"):
                self.evm_group = self._build_evm_panel()
        except Exception as e:
            self._clear_dashboard()
            #self.summary_widget(f"Error loading dashboard: {e}")
            return

        self._current_data = data
        self._update_summary(proj_name, data)
        self._update_kpis(data)
        self._update_burndown_chart(data)
        self._update_resource_chart(data)
        self._update_alerts(data)
        self._update_upcoming(data)
        
        # EVM
        if data.evm is None:
            self.evm_hint.setText("Create a baseline to enable EVM metrics.")
            if hasattr(self, "evm_cost_summary"):
                self.evm_cost_summary.setText("")
                self.evm_schedule_summary.setText("")
                self.evm_forecast_summary.setText("")
                self.evm_TCPI_summary.setText("")
            self.lbl_cpi.setText("-")
            self.lbl_spi.setText("-")
            self.lbl_eac.setText("-")
            self.lbl_vac.setText("-")
            self.lbl_pv.setText("-")
            self.lbl_ev.setText("-")
            self.lbl_ac.setText("-")
            self.lbl_tcpi.setText("-")
            return

        evm = data.evm
        selected_id = self._selected_baseline_id()
        
        if selected_id:
            # Find label already in combo (clean for user)
            baseline_label = self.baseline_combo.currentText()
        else:
            baseline_label = "Latest baseline"

        self.evm_hint.setText(f"As of {evm.as_of.isoformat()} (baseline: {baseline_label})")

        self.lbl_cpi.setText(fmt_ratio(evm.CPI))
        self.lbl_spi.setText(fmt_ratio(evm.SPI))
        self.lbl_eac.setText(fmt_money(evm.EAC))
        self.lbl_vac.setText(fmt_money(evm.VAC))
        self.lbl_pv.setText(fmt_money(evm.PV))
        self.lbl_ev.setText(fmt_money(evm.EV))
        self.lbl_ac.setText(fmt_money(evm.AC))
        self.lbl_tcpi.setText(fmt_ratio(evm.TCPI_to_BAC))
        self.lbl_tcpi_eac.setText(fmt_ratio(evm.TCPI_to_EAC))
        
        parts = evm.status_text.split(". ")
        
        p0 = parts[0] if len(parts) > 0 else ""
        p1 = parts[1] if len(parts) > 1 else ""
        p2 = parts[2] if len(parts) > 2 else (" ".join(parts[1:]) if len(parts) > 1 else "")
        p3 = parts[3] if len(parts) > 3 else (" ".join(parts[2:]) if len(parts) > 2 else "")
        self.evm_cost_summary.setText(self._format_evm_part(p0))
        self.evm_schedule_summary.setText(self._format_evm_part(p1))
        self.evm_forecast_summary.setText(self._format_evm_part(p2))
        self.evm_TCPI_summary.setText(self._format_evm_part(p3))
        
    def _clear_dashboard(self):
            self.alerts_list.clear()
            self.upcoming_table.setRowCount(0)

            # Clear charts
            self.burndown_chart.ax.clear()
            self.resource_chart.ax.clear()
            self.burndown_chart.redraw()
            self.resource_chart.redraw()

            # Reset KPI values (update existing widgets, don't recreate)
            try:
                self.kpi_tasks.findChildren(QLabel)[1].setText("0 / 0")
                self.kpi_tasks.findChildren(QLabel)[2].setText("Completed / Total")
                self.kpi_critical.findChildren(QLabel)[1].setText("0")
                self.kpi_late.findChildren(QLabel)[1].setText("0")
                self.kpi_cost.findChildren(QLabel)[1].setText("0.00")
                self.kpi_cost.findChildren(QLabel)[2].setText("Actual - Planned")
                self.kpi_progress.findChildren(QLabel)[1].setText("0%")
            except Exception:
                pass

            # Reset project summary
            if hasattr(self, "project_title_lbl"):
                self.project_title_lbl.setText("")
                self.project_meta_start.setText("")
                self.project_meta_end.setText("")
                self.project_meta_duration.setText("")

            # Reset EVM widgets if present
            if hasattr(self, "evm_hint"):
                self.evm_hint.setText("Create a baseline to enable EVM metrics.")
                if hasattr(self, "evm_cost_summary"):
                    self.evm_cost_summary.setText("")
                    self.evm_schedule_summary.setText("")
                    self.evm_forecast_summary.setText("")
                    self.evm_TCPI_summary.setText("")
                self.lbl_cpi.setText("-")
                self.lbl_spi.setText("-")
                self.lbl_eac.setText("-")
                self.lbl_vac.setText("-")
                self.lbl_pv.setText("-")
                self.lbl_ev.setText("-")
                self.lbl_ac.setText("-")

    def _build_evm_panel(self):
        box = QGroupBox("Earned Value (EVM)")
        box.setFont(CFG.GROUPBOX_TITLE_FONT)
        grid = QGridLayout(box)

        self.evm_hint = QLabel("Create a baseline to enable EVM metrics.")
        self.evm_hint.setWordWrap(True)

        self.lbl_cpi = QLabel("-")
        self.lbl_spi = QLabel("-")
        self.lbl_eac = QLabel("-")
        self.lbl_vac = QLabel("-")
        self.lbl_pv  = QLabel("-")
        self.lbl_ev  = QLabel("-")
        self.lbl_ac  = QLabel("-")
        self.lbl_tcpi = QLabel("-")
        self.lbl_tcpi_eac = QLabel("-")    

        # Single-line EVM summary bar (Cost • Schedule • Forecast)
        self.evm_cost_summary = QLabel("")
        self.evm_schedule_summary = QLabel("")
        self.evm_forecast_summary = QLabel("")
        self.evm_TCPI_summary = QLabel("")
        for lbl in (self.evm_cost_summary, self.evm_schedule_summary, self.evm_forecast_summary, self.evm_TCPI_summary):
            lbl.setStyleSheet("font-size: 10pt; color: #333333;")
            lbl.setWordWrap(False)
            lbl.setTextFormat(Qt.RichText)
            lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)

        self.evm_summary_bar = QWidget()
        hbar = QHBoxLayout(self.evm_summary_bar)
        hbar.setContentsMargins(0, 0, 0, 0)
        hbar.setSpacing(CFG.SPACING_MD)

        sep1 = QLabel("•"); sep1.setStyleSheet("color: #cccccc;")
        sep2 = QLabel("•"); sep2.setStyleSheet("color: #cccccc;")
        sep3= QLabel("•"); sep3.setStyleSheet("color: #cccccc;")

        hbar.addWidget(self.evm_cost_summary)
        hbar.addWidget(sep1)
        hbar.addWidget(self.evm_schedule_summary)
        hbar.addWidget(sep2)
        hbar.addWidget(self.evm_forecast_summary)
        hbar.addWidget(sep3)
        hbar.addWidget(self.evm_TCPI_summary)
        hbar.addStretch()

        # Row 0–1: hint/status spanning all 8 columns
        grid.addWidget(self.evm_hint,   0, 0, 1, 8)
        grid.addWidget(self.evm_summary_bar, 1, 0, 1, 8)

        # Row 2: CPI / PV / SPI / EV
        self.cpi_lbl = QLabel("CPI")
        self.pv_lbl = QLabel("PV")
        self.spi_lbl = QLabel("SPI")
        self.ev_lbl = QLabel("EV")
        self.eac_lbl = QLabel("EAC")
        self.ac_lbl  = QLabel("AC")
        self.tcpi_bac  = QLabel("TCPI(BAC)")
        self.vac_lbl = QLabel("VAC")
        self.tcpi_eac = QLabel("TCPI(EAC)") 
        
        grid.addWidget(self.cpi_lbl, 2, 0); grid.addWidget(self.lbl_cpi, 2, 1)
        grid.addWidget(self.pv_lbl,  2, 2); grid.addWidget(self.lbl_pv,  2, 3)
        grid.addWidget(self.spi_lbl , 2, 4); grid.addWidget(self.lbl_spi, 2, 5)
        grid.addWidget(self.ev_lbl,  2, 6); grid.addWidget(self.lbl_ev,  2, 7)

        # Row 3: EAC / AC / VAC / TCPI
        grid.addWidget(self.eac_lbl, 3, 0); grid.addWidget(self.lbl_eac, 3, 1)
        grid.addWidget(self.ac_lbl,  3, 2); grid.addWidget(self.lbl_ac,  3, 3)
        grid.addWidget(self.vac_lbl, 3, 4); grid.addWidget(self.lbl_vac, 3, 5)
        grid.addWidget(self.tcpi_bac ,3, 6); grid.addWidget(self.lbl_tcpi,3, 7)
        grid.addWidget(self.tcpi_eac,3, 8); grid.addWidget(self.lbl_tcpi_eac,3, 9)

        
        # Apply per-metric colors for EVM labels (configurable via CFG.EVM_METRIC_COLORS)
        evm_map = getattr(CFG, 'EVM_METRIC_COLORS', {})
        evm_label_map = {
            'CPI': self.lbl_cpi,
            'SPI': self.lbl_spi,
            'EAC': self.lbl_eac,
            'VAC': self.lbl_vac,
            'PV': self.lbl_pv,
            'EV': self.lbl_ev,
            'AC': self.lbl_ac,
            'TCPI': self.lbl_tcpi,
            'TCPI_EAC': self.lbl_tcpi_eac,
        }
        for key, label in evm_label_map.items():
            color = evm_map.get(key, CFG.EVM_DEFAULT_COLOR)
            label.setStyleSheet(CFG.DASHBOARD_METRIC_BOLD_TEMPLATE.format(color=color))
        
        for lbl in [self.cpi_lbl, self.spi_lbl, self.eac_lbl, 
                    self.vac_lbl, self.pv_lbl, self.ev_lbl, 
                    self.ac_lbl,self.tcpi_bac,self.tcpi_eac]:
            lbl.setStyleSheet(CFG.DASHBOARD_KPI_TITLE_STYLE)    
        
        sss = CFG.DASHBOARD_HIGHLIGHT_COLOR
        
        box.setStyleSheet("""
            QGroupBox {
                background-color: #ffffff;
                border-radius: 10px;
                border: 1px solid #e0e0e0;
                margin-top: 8px;
            }
            QGroupBox:title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px 0 3px;
                color: #444444;
                font-weight: bold;
            }
        """)

        return box

    def _format_evm_part(self, text: str) -> str:
        """Format a single EVM summary part into HTML: bold label and muted value.
        Example input: "Cost: Over budget by 12%" -> formatted HTML string.
        """
        if not text:
            return "-"
        if ":" in text:
            key, val = text.split(":", 1)
            return f"<span style='font-weight:600;color:#444'>{key}:</span> <span style='color:#666'>{val.strip()}</span>"
        return text
    
    def _load_baselines_for_project(self, project_id: str):
        # Avoid triggering refresh repeatedly while populating combo
        self.baseline_combo.blockSignals(True)
        self.baseline_combo.clear()

        baselines = self._baseline_service.list_baselines(project_id)

        # First option: “Latest”
        self.baseline_combo.addItem("Latest baseline", userData=None)

        for b in baselines:
            label = f"{b.name}  ({b.created_at.strftime('%Y-%m-%d %H:%M')})"
            self.baseline_combo.addItem(label, userData=b.id)

        self.baseline_combo.blockSignals(False)

    def _selected_baseline_id(self) -> str | None:
        idx = self.baseline_combo.currentIndex()
        if idx < 0:
            return None
        return self.baseline_combo.itemData(idx)
    
    def _delete_selected_baseline(self):
        proj_id, _ = self._current_project_id_and_name()
        if not proj_id:
            return

        baseline_id = self._selected_baseline_id()
        if baseline_id is None:
            QMessageBox.information(self, "Delete baseline", "Select a specific baseline (not 'Latest baseline').")
            return

        label = self.baseline_combo.currentText()
        resp = QMessageBox.question(
            self,
            "Delete baseline",
            f"Delete selected baseline?\n\n{label}\n\nThis cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if resp != QMessageBox.Yes:
            return

        try:
            self._baseline_service.delete_baseline(baseline_id)
            self._load_baselines_for_project(proj_id)
            self.baseline_combo.setCurrentIndex(0)
            self.refresh_dashboard()
        except Exception as e:
            QMessageBox.critical(self, "Delete baseline", f"Could not delete baseline:\n{e}")
    
    # --------------------------------------------------------------
    # Update sections
    # --------------------------------------------------------------

    def _update_summary(self, project_name: str, data: DashboardData):
        k = data.kpi
        start = k.start_date.isoformat() if k.start_date else "-"
        end = k.end_date.isoformat() if k.end_date else "-"
        # Title (prefer explicit project_name but fall back to KPI.name in case combo label is empty)
        title = project_name or (getattr(k, 'name', None) or '')
        self.project_title_lbl.setText(title)
        self.project_title_lbl.setVisible(True)
        self.project_title_lbl.setWordWrap(False)

        # Meta chips (use UIConfig prefixes)
        self.project_meta_start.setText(f"{CFG.DASHBOARD_META_START_PREFIX} {start}")
        self.project_meta_start.setVisible(True)
        self.project_meta_end.setText(f"{CFG.DASHBOARD_META_END_PREFIX} {end}")
        self.project_meta_end.setVisible(True)
        self.project_meta_duration.setText(f"{CFG.DASHBOARD_META_DURATION_PREFIX} {k.duration_working_days} working days")
        self.project_meta_duration.setVisible(True)

    def _update_kpis(self, data: DashboardData):
        k = data.kpi

        # Because KpiCard doesn't expose labels, easiest is to recreate text via stylesheet:
        # Instead, we just update their texts via children:
        tasks_title = self.kpi_tasks.findChildren(QLabel)[0]
        tasks_value = self.kpi_tasks.findChildren(QLabel)[1]
        tasks_sub = self.kpi_tasks.findChildren(QLabel)[2]
        tasks_value.setText(f"{fmt_int(k.tasks_completed)} / {fmt_int(k.tasks_total)}")
        tasks_sub.setText("Completed / Total")

        crit_title = self.kpi_critical.findChildren(QLabel)[0]
        crit_value = self.kpi_critical.findChildren(QLabel)[1]
        crit_value.setText(fmt_int(k.critical_tasks))

        late_value = self.kpi_late.findChildren(QLabel)[1]
        late_value.setText(fmt_int(k.late_tasks))

        cost_value = self.kpi_cost.findChildren(QLabel)[1]
        cost_sub = self.kpi_cost.findChildren(QLabel)[2]
        cost_value.setText(f"{fmt_float(k.cost_variance,2)}")
        cost_sub.setText("Actual - Planned")

        # % complete: naive (completed / total)
        pct = 0.0
        if k.tasks_total > 0:
            pct = 100.0 * k.tasks_completed / k.tasks_total
        prog_value = self.kpi_progress.findChildren(QLabel)[1]
        prog_value.setText(f"{fmt_percent(pct,2)}")

    def _update_burndown_chart(self, data: DashboardData):
        self.burndown_chart.ax.clear()
        pts = data.burndown
        if not pts:
            self.burndown_chart.ax.set_title("No burndown data")
            self.burndown_chart.redraw()
            return

        dates = [p.day for p in pts]
        rem = [p.remaining_tasks for p in pts]

        self.burndown_chart.ax.plot(dates, rem, marker="o")
        
        self.burndown_chart.ax.set_title("Burndown (remaining tasks)")
        self.burndown_chart.ax.set_xlabel("Date",fontsize=10)
        self.burndown_chart.ax.set_ylabel("Remaining tasks",fontsize=10)
        self.burndown_chart.ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        self.burndown_chart.ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(mdates.AutoDateLocator()))
        self.burndown_chart.fig.autofmt_xdate(rotation=30)
        self.burndown_chart.ax.grid(True, linestyle=":", linewidth=0.5)

        self.burndown_chart.fig.tight_layout()
        self.burndown_chart.redraw()

    def _update_resource_chart(self, data: DashboardData):
        self.resource_chart.ax.clear()
        rows = data.resource_load
        if not rows:
            self.resource_chart.ax.set_title("No resource load data")
            self.resource_chart.redraw()
            return

        names = [r.resource_name for r in rows]
        allocs = [r.total_allocation_percent for r in rows]

        x = range(len(names))
        bars = self.resource_chart.ax.bar(x, allocs)
        for i, r in enumerate(rows):
            if r.total_allocation_percent > 100.0:
                bars[i].set_color("#d0021b")

        self.resource_chart.ax.set_xticks(list(x))
        self.resource_chart.ax.set_xticklabels(names, rotation=45, ha="right", fontsize=8)
        self.resource_chart.ax.set_ylabel("Allocation %",fontsize=10)
        self.resource_chart.ax.set_title("Resource load")
        self.resource_chart.ax.axhline(100.0, color="red", linestyle="--", linewidth=0.5)
        self.resource_chart.ax.grid(True, axis="y", linestyle=":", linewidth=0.5)

        self.resource_chart.fig.tight_layout()
        self.resource_chart.redraw()

    def _update_alerts(self, data: DashboardData):
        self.alerts_list.clear()
        if not data.alerts:
            self.alerts_list.addItem("No alerts. Everything looks good.")
            return

        for msg in data.alerts:
            item = QListWidgetItem("⚠ " + msg)
            item.setForeground(QColor("#d0021b"))
            self.alerts_list.addItem(item)

    def _update_upcoming(self, data: DashboardData):
        self.upcoming_table.setRowCount(0)
        ups = data.upcoming_tasks
        if not ups:
            return

        self.upcoming_table.setRowCount(len(ups))
        for row, u in enumerate(ups):
            def set_cell(col, text, color_bg=None):
                item = QTableWidgetItem(text)
                if color_bg:
                    item.setBackground(color_bg)
                self.upcoming_table.setItem(row, col, item)

            set_cell(0, u.name)
            set_cell(1, u.start_date.isoformat() if u.start_date else "-")
            set_cell(2, u.end_date.isoformat() if u.end_date else "-")
            set_cell(3, f"{u.percent_complete:.0f}%")
            set_cell(4, u.main_resource or "-")

            if u.is_late:
                for col in range(5):
                    it = self.upcoming_table.item(row, col)
                    it.setBackground(QColor("#ffe5e5"))

class KpiCard(QWidget):
    def __init__(self, title: str, value: str, subtitle: str = "", color: str = "#4a90e2", parent: QWidget | None = None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(CFG.SPACING_SM, CFG.SPACING_XS, CFG.SPACING_SM,  CFG.SPACING_XS)

        lbl_title = QLabel(title)
        lbl_title.setStyleSheet(CFG.DASHBOARD_KPI_TITLE_STYLE)

        lbl_value = QLabel(value)
        lbl_value.setStyleSheet(CFG.DASHBOARD_KPI_VALUE_TEMPLATE.format(color=color))

        layout.addWidget(lbl_title)
        layout.addWidget(lbl_value)

        if subtitle:
            lbl_sub = QLabel(subtitle)
            lbl_sub.setStyleSheet(CFG.DASHBOARD_KPI_SUB_STYLE)
            layout.addWidget(lbl_sub)

        layout.addStretch()

        self.setStyleSheet("""
            QWidget {
                background-color: #ffffff;
                border-radius: 10px;
                border: 1px solid #e0e0e0;
            }
        """)

class ChartWidget(QWidget):
    def __init__(self, title: str, parent: QWidget | None = None):
        super().__init__(parent)
        self._fig, self._ax = plt.subplots()
        self._canvas = FigureCanvas(self._fig)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(CFG.SPACING_SM, CFG.SPACING_XS, CFG.SPACING_SM,  CFG.SPACING_XS)

        lbl_title = QLabel(title)
        lbl_title.setStyleSheet(CFG.CHART_TITLE_STYLE)

        layout.addWidget(lbl_title)
        layout.addWidget(self._canvas)
        
        self._canvas.setSizePolicy(
            CFG.GROW, 
            CFG.GROW
        )

        self.setStyleSheet("""
            QWidget {
                background-color: #ffffff;
                border-radius: 10px;
                border: 1px solid #e0e0e0;
            }
        """)

    @property
    def ax(self):
        return self._ax

    @property
    def fig(self):
        return self._fig

    def redraw(self):
        self._canvas.draw()



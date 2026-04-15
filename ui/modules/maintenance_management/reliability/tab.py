from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.application.runtime.platform_runtime import PlatformRuntimeApplicationService
from core.modules.maintenance_management import (
    MaintenanceAssetService,
    MaintenanceFailureCodeService,
    MaintenanceLocationService,
    MaintenanceReliabilityService,
    MaintenanceReportingService,
    MaintenanceSystemService,
)
from core.platform.auth import UserSessionContext
from core.platform.common.exceptions import BusinessRuleError
from core.platform.notifications.domain_events import DomainChangeEvent, domain_events
from core.platform.org import SiteService
from ui.modules.maintenance_management.shared import (
    MaintenanceWorkbenchNavigator,
    MaintenanceWorkbenchSection,
    build_maintenance_header,
    display_metric,
    format_timestamp,
    make_accent_badge,
    make_filter_toggle_button,
    make_meta_badge,
    reset_combo_options,
    selected_combo_value,
    set_filter_panel_visible,
)
from ui.modules.project_management.dashboard.styles import dashboard_action_button_style
from ui.modules.project_management.dashboard.widgets import KpiCard
from ui.platform.admin.shared_surface import build_admin_surface_card, build_admin_table
from ui.platform.shared.guards import apply_permission_hint, has_permission, make_guarded_slot
from ui.platform.shared.styles.ui_config import UIConfig as CFG


class MaintenanceReliabilityTab(QWidget):
    def __init__(
        self,
        *,
        reliability_service: MaintenanceReliabilityService,
        reporting_service: MaintenanceReportingService,
        failure_code_service: MaintenanceFailureCodeService,
        site_service: SiteService,
        asset_service: MaintenanceAssetService,
        location_service: MaintenanceLocationService,
        system_service: MaintenanceSystemService,
        platform_runtime_application_service: PlatformRuntimeApplicationService | None = None,
        user_session: UserSessionContext | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._reliability_service = reliability_service
        self._reporting_service = reporting_service
        self._failure_code_service = failure_code_service
        self._site_service = site_service
        self._asset_service = asset_service
        self._location_service = location_service
        self._system_service = system_service
        self._platform_runtime_application_service = platform_runtime_application_service
        self._user_session = user_session
        self._can_export = has_permission(user_session, "report.export")
        self._setup_ui()
        self.reload_data()
        domain_events.domain_changed.connect(self._on_domain_change)
        domain_events.modules_changed.connect(self._on_modules_changed)
        domain_events.organizations_changed.connect(self._on_organization_changed)

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(CFG.SPACING_MD)
        root.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)

        self.context_badge = make_accent_badge("Context: -")
        self.export_badge = make_meta_badge("Export Disabled")
        self.focus_badge = make_meta_badge("Reliability Engineer Queue")
        build_maintenance_header(
            root=root,
            object_name="maintenanceReliabilityHeaderCard",
            eyebrow_text="RELIABILITY WORKBENCH",
            title_text="Reliability",
            subtitle_text="Review recurring failures, root-cause clusters, and generated maintenance report packs from one workbench.",
            badges=(self.context_badge, self.export_badge, self.focus_badge),
        )

        self.btn_refresh = QPushButton(CFG.REFRESH_BUTTON_LABEL)
        self.btn_backlog_excel = QPushButton("Backlog Excel")
        self.btn_pm_excel = QPushButton("PM Excel")
        self.btn_recurring_excel = QPushButton("Recurring Excel")
        self.btn_exception_excel = QPushButton("Exceptions Excel")
        self.btn_downtime_pdf = QPushButton("Downtime PDF")
        self.btn_execution_pdf = QPushButton("Execution PDF")
        self.btn_filters = make_filter_toggle_button(self)
        for button, variant in (
            (self.btn_refresh, "secondary"),
            (self.btn_backlog_excel, "secondary"),
            (self.btn_pm_excel, "secondary"),
            (self.btn_recurring_excel, "secondary"),
            (self.btn_exception_excel, "secondary"),
            (self.btn_downtime_pdf, "secondary"),
            (self.btn_execution_pdf, "primary"),
            (self.btn_filters, "secondary"),
        ):
            button.setFixedHeight(CFG.BUTTON_HEIGHT)
            button.setStyleSheet(dashboard_action_button_style(variant))

        exports, exports_layout = build_admin_surface_card(
            object_name="maintenanceReliabilityExportSurface",
            alt=False,
        )
        self.export_surface = exports
        export_summary = QLabel(
            "Generate workbook and PDF packs for backlog, PM compliance, recurring failures, exception review, downtime, and execution."
        )
        export_summary.setStyleSheet(CFG.INFO_TEXT_STYLE)
        export_summary.setWordWrap(True)
        exports_layout.addWidget(export_summary)
        export_grid = QGridLayout()
        export_grid.setContentsMargins(0, 0, 0, 0)
        export_grid.setHorizontalSpacing(CFG.SPACING_SM)
        export_grid.setVerticalSpacing(CFG.SPACING_SM)
        for index, button in enumerate(
            (
                self.btn_backlog_excel,
                self.btn_pm_excel,
                self.btn_recurring_excel,
                self.btn_exception_excel,
                self.btn_downtime_pdf,
                self.btn_execution_pdf,
            )
        ):
            export_grid.addWidget(button, index // 3, index % 3)
        exports_layout.addLayout(export_grid)
        root.addWidget(exports)

        controls, controls_layout = build_admin_surface_card(
            object_name="maintenanceReliabilityControlSurface",
            alt=True,
        )
        self.control_surface = controls
        toolbar_row = QHBoxLayout()
        toolbar_row.setSpacing(CFG.SPACING_SM)
        self.filter_summary = QLabel("Filters: All sites | All assets | All systems | All locations | All failure symptoms")
        self.filter_summary.setStyleSheet(CFG.NOTE_STYLE_SHEET)
        self.filter_summary.setWordWrap(True)
        toolbar_row.addWidget(self.filter_summary, 1)
        toolbar_row.addWidget(self.btn_filters)
        toolbar_row.addWidget(self.btn_refresh)
        controls_layout.addLayout(toolbar_row)

        self.filter_panel = QWidget()
        filter_row = QGridLayout(self.filter_panel)
        filter_row.setContentsMargins(0, 0, 0, 0)
        filter_row.setHorizontalSpacing(CFG.SPACING_MD)
        filter_row.setVerticalSpacing(CFG.SPACING_SM)
        self.site_combo = QComboBox()
        self.asset_combo = QComboBox()
        self.system_combo = QComboBox()
        self.location_combo = QComboBox()
        self.failure_code_combo = QComboBox()
        self.days_combo = QComboBox()
        self.limit_combo = QComboBox()
        self.threshold_combo = QComboBox()
        for days in (30, 60, 90, 180, 365):
            self.days_combo.addItem(f"{days} days", days)
        self.days_combo.setCurrentIndex(2)
        for limit in (5, 10, 20, 50):
            self.limit_combo.addItem(f"Top {limit}", limit)
        self.limit_combo.setCurrentIndex(2)
        for threshold in (2, 3, 4, 5):
            self.threshold_combo.addItem(f"{threshold}+ repeats", threshold)
        filter_row.addWidget(QLabel("Site"), 0, 0)
        filter_row.addWidget(self.site_combo, 0, 1)
        filter_row.addWidget(QLabel("Asset"), 0, 2)
        filter_row.addWidget(self.asset_combo, 0, 3)
        filter_row.addWidget(QLabel("Failure"), 0, 4)
        filter_row.addWidget(self.failure_code_combo, 0, 5)
        filter_row.addWidget(QLabel("System"), 1, 0)
        filter_row.addWidget(self.system_combo, 1, 1)
        filter_row.addWidget(QLabel("Location"), 1, 2)
        filter_row.addWidget(self.location_combo, 1, 3)
        filter_row.addWidget(QLabel("Window"), 1, 4)
        filter_row.addWidget(self.days_combo, 1, 5)
        filter_row.addWidget(QLabel("Limit"), 2, 0)
        filter_row.addWidget(self.limit_combo, 2, 1)
        filter_row.addWidget(QLabel("Recurring Threshold"), 2, 2)
        filter_row.addWidget(self.threshold_combo, 2, 3)
        controls_layout.addWidget(self.filter_panel)
        set_filter_panel_visible(button=self.btn_filters, panel=self.filter_panel, visible=False)
        root.addWidget(controls)

        summary_row = QHBoxLayout()
        summary_row.setSpacing(CFG.SPACING_MD)
        self.suggestion_card = KpiCard("Suggestions", "-", "Failure-guided suggestions", CFG.COLOR_ACCENT)
        self.root_cause_card = KpiCard("Root causes", "-", "Observed combinations", CFG.COLOR_WARNING)
        self.recurring_card = KpiCard("Recurring patterns", "-", "Repeat reliability signals", CFG.COLOR_SUCCESS)
        for card in (self.suggestion_card, self.root_cause_card, self.recurring_card):
            summary_row.addWidget(card, 1)
        root.addLayout(summary_row)

        self.workbench = MaintenanceWorkbenchNavigator(object_name="maintenanceReliabilityWorkbench", parent=self)
        self.suggestions_panel = self._build_suggestions_panel()
        self.root_cause_panel = self._build_root_cause_panel()
        self.recurring_panel = self._build_recurring_panel()
        self.workbench.set_sections(
            [
                MaintenanceWorkbenchSection(
                    key="suggestions",
                    label="Suggestions",
                    widget=self.suggestions_panel,
                ),
                MaintenanceWorkbenchSection(
                    key="root_causes",
                    label="Root Causes",
                    widget=self.root_cause_panel,
                ),
                MaintenanceWorkbenchSection(
                    key="recurring_failures",
                    label="Recurring Failures",
                    widget=self.recurring_panel,
                ),
            ],
            initial_key="suggestions",
        )
        root.addWidget(self.workbench, 1)

        self.site_combo.currentIndexChanged.connect(self._on_site_changed)
        self.asset_combo.currentIndexChanged.connect(
            make_guarded_slot(self, title="Maintenance Reliability", callback=self.reload_analysis)
        )
        self.system_combo.currentIndexChanged.connect(
            make_guarded_slot(self, title="Maintenance Reliability", callback=self.reload_analysis)
        )
        self.location_combo.currentIndexChanged.connect(
            make_guarded_slot(self, title="Maintenance Reliability", callback=self.reload_analysis)
        )
        self.failure_code_combo.currentIndexChanged.connect(
            make_guarded_slot(self, title="Maintenance Reliability", callback=self.reload_analysis)
        )
        self.days_combo.currentIndexChanged.connect(
            make_guarded_slot(self, title="Maintenance Reliability", callback=self.reload_analysis)
        )
        self.limit_combo.currentIndexChanged.connect(
            make_guarded_slot(self, title="Maintenance Reliability", callback=self.reload_analysis)
        )
        self.threshold_combo.currentIndexChanged.connect(
            make_guarded_slot(self, title="Maintenance Reliability", callback=self.reload_analysis)
        )
        self.btn_refresh.clicked.connect(
            make_guarded_slot(self, title="Maintenance Reliability", callback=self.reload_data)
        )
        self.btn_backlog_excel.clicked.connect(
            make_guarded_slot(self, title="Maintenance Reliability", callback=self.export_backlog_excel)
        )
        self.btn_pm_excel.clicked.connect(
            make_guarded_slot(self, title="Maintenance Reliability", callback=self.export_pm_excel)
        )
        self.btn_recurring_excel.clicked.connect(
            make_guarded_slot(self, title="Maintenance Reliability", callback=self.export_recurring_excel)
        )
        self.btn_exception_excel.clicked.connect(
            make_guarded_slot(self, title="Maintenance Reliability", callback=self.export_exception_excel)
        )
        self.btn_downtime_pdf.clicked.connect(
            make_guarded_slot(self, title="Maintenance Reliability", callback=self.export_downtime_pdf)
        )
        self.btn_execution_pdf.clicked.connect(
            make_guarded_slot(self, title="Maintenance Reliability", callback=self.export_execution_pdf)
        )
        self.btn_filters.clicked.connect(self._toggle_filters)
        for button in (
            self.btn_backlog_excel,
            self.btn_pm_excel,
            self.btn_recurring_excel,
            self.btn_exception_excel,
            self.btn_downtime_pdf,
            self.btn_execution_pdf,
        ):
            apply_permission_hint(button, allowed=self._can_export, missing_permission="report.export")

    def _build_suggestions_panel(self) -> QWidget:
        panel, layout = build_admin_surface_card(
            object_name="maintenanceReliabilitySuggestionSurface",
            alt=False,
        )
        title = QLabel("Root Cause Suggestions")
        title.setStyleSheet(CFG.SECTION_BOLD_MARGIN_STYLE)
        subtitle = QLabel("Suggested causes for the selected failure symptom and scope.")
        subtitle.setStyleSheet(CFG.INFO_TEXT_STYLE)
        subtitle.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        self.suggestions_table = build_admin_table(
            headers=("Scope", "Root Cause", "Count", "Downtime", "Latest"),
            resize_modes=(
                self._resize_to_contents(),
                self._stretch(),
                self._resize_to_contents(),
                self._resize_to_contents(),
                self._resize_to_contents(),
            ),
        )
        layout.addWidget(self.suggestions_table)
        return panel

    def _build_root_cause_panel(self) -> QWidget:
        panel, layout = build_admin_surface_card(
            object_name="maintenanceReliabilityInsightSurface",
            alt=False,
        )
        title = QLabel("Observed Root Causes")
        title.setStyleSheet(CFG.SECTION_BOLD_MARGIN_STYLE)
        subtitle = QLabel("Most common failure and root-cause combinations in the selected window.")
        subtitle.setStyleSheet(CFG.INFO_TEXT_STYLE)
        subtitle.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        self.root_cause_table = build_admin_table(
            headers=("Failure", "Root Cause", "Count", "Downtime", "Open"),
            resize_modes=(
                self._stretch(),
                self._stretch(),
                self._resize_to_contents(),
                self._resize_to_contents(),
                self._resize_to_contents(),
            ),
        )
        layout.addWidget(self.root_cause_table)
        return panel

    def _build_recurring_panel(self) -> QWidget:
        panel, layout = build_admin_surface_card(
            object_name="maintenanceReliabilityRecurringSurface",
            alt=False,
        )
        title = QLabel("Recurring Failure Queue")
        title.setStyleSheet(CFG.SECTION_BOLD_MARGIN_STYLE)
        subtitle = QLabel("Patterns that planners and reliability engineers should review next.")
        subtitle.setStyleSheet(CFG.INFO_TEXT_STYLE)
        subtitle.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        self.recurring_table = build_admin_table(
            headers=("Anchor", "Failure", "Lead Cause", "Count", "Open", "MTBF"),
            resize_modes=(
                self._stretch(),
                self._stretch(),
                self._stretch(),
                self._resize_to_contents(),
                self._resize_to_contents(),
                self._resize_to_contents(),
            ),
        )
        layout.addWidget(self.recurring_table)
        return panel

    def reload_data(self) -> None:
        selected_site_id = selected_combo_value(self.site_combo)
        selected_asset_id = selected_combo_value(self.asset_combo)
        selected_system_id = selected_combo_value(self.system_combo)
        selected_location_id = selected_combo_value(self.location_combo)
        selected_failure_code = selected_combo_value(self.failure_code_combo)
        try:
            site_options = [
                (f"{site.site_code} - {site.name}", site.id)
                for site in self._site_service.list_sites(active_only=None)
            ]
            asset_options = [
                (f"{asset.asset_code} - {asset.name}", asset.id)
                for asset in self._asset_service.list_assets(active_only=True, site_id=selected_site_id)
            ]
            system_options = [
                (f"{system.system_code} - {system.name}", system.id)
                for system in self._system_service.list_systems(active_only=True, site_id=selected_site_id)
            ]
            location_options = [
                (f"{location.location_code} - {location.name}", location.id)
                for location in self._location_service.list_locations(active_only=True, site_id=selected_site_id)
            ]
            failure_options = [
                (f"{row.failure_code} - {row.name}", row.failure_code)
                for row in self._failure_code_service.list_failure_codes(active_only=True, code_type="SYMPTOM")
            ]
        except BusinessRuleError as exc:
            QMessageBox.warning(self, "Maintenance Reliability", str(exc))
            return
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Maintenance Reliability", f"Failed to load reliability filters: {exc}")
            return

        reset_combo_options(
            self.site_combo,
            placeholder="All sites",
            options=site_options,
            selected_value=selected_site_id,
        )
        reset_combo_options(
            self.asset_combo,
            placeholder="All assets",
            options=asset_options,
            selected_value=selected_asset_id,
        )
        reset_combo_options(
            self.system_combo,
            placeholder="All systems",
            options=system_options,
            selected_value=selected_system_id,
        )
        reset_combo_options(
            self.location_combo,
            placeholder="All locations",
            options=location_options,
            selected_value=selected_location_id,
        )
        reset_combo_options(
            self.failure_code_combo,
            placeholder="All failure symptoms",
            options=failure_options,
            selected_value=selected_failure_code,
        )
        self.reload_analysis()

    def reload_analysis(self) -> None:
        try:
            suggestions = []
            failure_code = selected_combo_value(self.failure_code_combo)
            if failure_code:
                suggestions = self._reliability_service.suggest_root_causes(
                    failure_code=failure_code,
                    asset_id=selected_combo_value(self.asset_combo),
                    system_id=selected_combo_value(self.system_combo),
                    days=self._selected_days(),
                    limit=self._selected_limit(),
                )
            insights = self._reliability_service.list_root_cause_analysis(
                site_id=selected_combo_value(self.site_combo),
                asset_id=selected_combo_value(self.asset_combo),
                system_id=selected_combo_value(self.system_combo),
                location_id=selected_combo_value(self.location_combo),
                days=self._selected_days(),
                limit=self._selected_limit(),
            )
            recurring = self._reliability_service.list_recurring_failure_patterns(
                site_id=selected_combo_value(self.site_combo),
                asset_id=selected_combo_value(self.asset_combo),
                system_id=selected_combo_value(self.system_combo),
                location_id=selected_combo_value(self.location_combo),
                days=self._selected_days(),
                min_occurrences=self._selected_threshold(),
                limit=self._selected_limit(),
            )
        except BusinessRuleError as exc:
            QMessageBox.warning(self, "Maintenance Reliability", str(exc))
            return
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Maintenance Reliability", f"Failed to load reliability analytics: {exc}")
            return

        self.context_badge.setText(f"Context: {self._context_label()}")
        self.export_badge.setText("Export Enabled" if self._can_export else "Export Disabled")
        self.filter_summary.setText(
            "Filters: "
            f"{self.site_combo.currentText()} | {self.asset_combo.currentText()} | "
            f"{self.system_combo.currentText()} | {self.location_combo.currentText()} | "
            f"{self.failure_code_combo.currentText()} | {self.days_combo.currentText()} | "
            f"{self.limit_combo.currentText()} | {self.threshold_combo.currentText()}"
        )
        self.suggestion_card.set_value(str(len(suggestions)))
        self.root_cause_card.set_value(str(len(insights)))
        self.recurring_card.set_value(str(len(recurring)))
        self._populate_suggestions_table(suggestions)
        self._populate_root_cause_table(insights)
        self._populate_recurring_table(recurring)

    def export_backlog_excel(self, output_path: str | Path | None = None):
        return self._export(
            callback=self._reporting_service.generate_backlog_excel,
            title="Export maintenance backlog Excel",
            suggested_name="maintenance-backlog.xlsx",
            file_filter="Excel files (*.xlsx);;All files (*.*)",
            output_path=output_path,
        )

    def export_pm_excel(self, output_path: str | Path | None = None):
        return self._export(
            callback=self._reporting_service.generate_pm_compliance_excel,
            title="Export maintenance PM compliance Excel",
            suggested_name="maintenance-pm-compliance.xlsx",
            file_filter="Excel files (*.xlsx);;All files (*.*)",
            output_path=output_path,
        )

    def export_downtime_pdf(self, output_path: str | Path | None = None):
        return self._export(
            callback=self._reporting_service.generate_downtime_pdf,
            title="Export maintenance downtime PDF",
            suggested_name="maintenance-downtime.pdf",
            file_filter="PDF files (*.pdf);;All files (*.*)",
            output_path=output_path,
        )

    def export_execution_pdf(self, output_path: str | Path | None = None):
        return self._export(
            callback=self._reporting_service.generate_execution_overview_pdf,
            title="Export maintenance execution PDF",
            suggested_name="maintenance-execution-overview.pdf",
            file_filter="PDF files (*.pdf);;All files (*.*)",
            output_path=output_path,
        )

    def export_recurring_excel(self, output_path: str | Path | None = None):
        return self._export(
            callback=self._reporting_service.generate_recurring_failures_excel,
            title="Export recurring failures Excel",
            suggested_name="maintenance-recurring-failures.xlsx",
            file_filter="Excel files (*.xlsx);;All files (*.*)",
            output_path=output_path,
        )

    def export_exception_excel(self, output_path: str | Path | None = None):
        return self._export(
            callback=self._reporting_service.generate_exception_review_excel,
            title="Export maintenance exception review Excel",
            suggested_name="maintenance-exception-review.xlsx",
            file_filter="Excel files (*.xlsx);;All files (*.*)",
            output_path=output_path,
        )

    def _export(self, *, callback, title: str, suggested_name: str, file_filter: str, output_path: str | Path | None):
        path = Path(output_path) if output_path is not None else self._choose_export_path(
            title=title,
            suggested_name=suggested_name,
            file_filter=file_filter,
        )
        if path is None:
            return None
        try:
            artifact = callback(
                path,
                site_id=selected_combo_value(self.site_combo),
                asset_id=selected_combo_value(self.asset_combo),
                system_id=selected_combo_value(self.system_combo),
                location_id=selected_combo_value(self.location_combo),
                days=self._selected_days(),
                limit=self._selected_limit(),
                recurring_threshold=self._selected_threshold(),
            )
        except BusinessRuleError as exc:
            QMessageBox.warning(self, "Maintenance Reliability", str(exc))
            return None
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Maintenance Reliability", f"Failed to export report pack: {exc}")
            return None
        QMessageBox.information(self, "Maintenance Reliability", f"Report exported to:\n{artifact.file_path}")
        return artifact.file_path

    def _choose_export_path(self, *, title: str, suggested_name: str, file_filter: str) -> Path | None:
        file_path, _ = QFileDialog.getSaveFileName(self, title, suggested_name, file_filter)
        if not file_path:
            return None
        return Path(file_path)

    def _populate_suggestions_table(self, rows) -> None:
        self.suggestions_table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            values = (
                row.match_scope.title(),
                row.root_cause_name,
                str(row.occurrence_count),
                str(row.total_downtime_minutes),
                format_timestamp(row.latest_occurrence_at),
            )
            for column, value in enumerate(values):
                self.suggestions_table.setItem(row_index, column, QTableWidgetItem(value))

    def _populate_root_cause_table(self, rows) -> None:
        self.root_cause_table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            values = (
                row.failure_name,
                row.root_cause_name,
                str(row.work_order_count),
                str(row.total_downtime_minutes),
                str(row.open_work_orders),
            )
            for column, value in enumerate(values):
                self.root_cause_table.setItem(row_index, column, QTableWidgetItem(value))

    def _populate_recurring_table(self, rows) -> None:
        self.recurring_table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            values = (
                f"{row.anchor_code} - {row.anchor_name}",
                row.failure_name,
                row.leading_root_cause_name or "-",
                str(row.occurrence_count),
                str(row.open_work_orders),
                display_metric(row.mean_interval_hours or "n/a"),
            )
            for column, value in enumerate(values):
                self.recurring_table.setItem(row_index, column, QTableWidgetItem(value))

    def _on_site_changed(self) -> None:
        self.reload_data()

    def _toggle_filters(self) -> None:
        set_filter_panel_visible(
            button=self.btn_filters,
            panel=self.filter_panel,
            visible=not self.filter_panel.isVisible(),
        )

    def _on_domain_change(self, event: DomainChangeEvent) -> None:
        if getattr(event, "scope_code", "") == "maintenance_management":
            self.reload_data()

    def _on_modules_changed(self, _module_code: str) -> None:
        self.reload_data()

    def _on_organization_changed(self, _organization_id: str) -> None:
        self.reload_data()

    def _selected_days(self) -> int:
        value = self.days_combo.currentData()
        try:
            return int(value)
        except (TypeError, ValueError):
            return 90

    def _selected_limit(self) -> int:
        value = self.limit_combo.currentData()
        try:
            return int(value)
        except (TypeError, ValueError):
            return 20

    def _selected_threshold(self) -> int:
        value = self.threshold_combo.currentData()
        try:
            return int(value)
        except (TypeError, ValueError):
            return 2

    def _context_label(self) -> str:
        service = self._platform_runtime_application_service
        if service is None or not hasattr(service, "current_context_label"):
            return "-"
        return str(service.current_context_label())

    @staticmethod
    def _resize_to_contents():
        from PySide6.QtWidgets import QHeaderView

        return QHeaderView.ResizeToContents

    @staticmethod
    def _stretch():
        from PySide6.QtWidgets import QHeaderView

        return QHeaderView.Stretch


__all__ = ["MaintenanceReliabilityTab"]

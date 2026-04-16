from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
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
    MaintenanceLocationService,
    MaintenanceReliabilityService,
    MaintenanceSystemService,
)
from src.core.platform.auth import UserSessionContext
from core.platform.common.exceptions import BusinessRuleError
from core.platform.notifications.domain_events import DomainChangeEvent, domain_events
from core.platform.org import SiteService
from ui.modules.maintenance_management.shared import (
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
from ui.platform.shared.guards import make_guarded_slot
from ui.platform.shared.styles.ui_config import UIConfig as CFG


class MaintenanceDashboardTab(QWidget):
    def __init__(
        self,
        *,
        reliability_service: MaintenanceReliabilityService,
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
        self._site_service = site_service
        self._asset_service = asset_service
        self._location_service = location_service
        self._system_service = system_service
        self._platform_runtime_application_service = platform_runtime_application_service
        self._user_session = user_session
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
        self.window_badge = make_meta_badge("90 day window")
        self.recurring_badge = make_meta_badge("0 recurring patterns")
        build_maintenance_header(
            root=root,
            object_name="maintenanceDashboardHeaderCard",
            eyebrow_text="MAINTENANCE OVERVIEW",
            title_text="Maintenance Dashboard",
            subtitle_text="See backlog pressure, downtime signals, root causes, and recurring failures from the first maintenance analytics seam.",
            badges=(self.context_badge, self.window_badge, self.recurring_badge),
        )

        controls, controls_layout = build_admin_surface_card(
            object_name="maintenanceDashboardControlSurface",
            alt=True,
        )
        toolbar_row = QHBoxLayout()
        toolbar_row.setSpacing(CFG.SPACING_SM)
        self.filter_summary = QLabel("Filters: All sites | All assets | All systems | All locations")
        self.filter_summary.setStyleSheet(CFG.NOTE_STYLE_SHEET)
        self.filter_summary.setWordWrap(True)
        toolbar_row.addWidget(self.filter_summary, 1)
        self.btn_filters = make_filter_toggle_button(self)
        self.btn_refresh = QPushButton(CFG.REFRESH_BUTTON_LABEL)
        self.btn_refresh.setFixedHeight(CFG.BUTTON_HEIGHT)
        self.btn_refresh.setStyleSheet(dashboard_action_button_style("secondary"))
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
        self.days_combo = QComboBox()
        for days in (30, 60, 90, 180, 365):
            self.days_combo.addItem(f"{days} days", days)
        self.days_combo.setCurrentIndex(2)
        filter_row.addWidget(QLabel("Site"), 0, 0)
        filter_row.addWidget(self.site_combo, 0, 1)
        filter_row.addWidget(QLabel("Asset"), 0, 2)
        filter_row.addWidget(self.asset_combo, 0, 3)
        filter_row.addWidget(QLabel("System"), 1, 0)
        filter_row.addWidget(self.system_combo, 1, 1)
        filter_row.addWidget(QLabel("Location"), 1, 2)
        filter_row.addWidget(self.location_combo, 1, 3)
        filter_row.addWidget(QLabel("Window"), 0, 4)
        filter_row.addWidget(self.days_combo, 0, 5)
        controls_layout.addWidget(self.filter_panel)
        set_filter_panel_visible(button=self.btn_filters, panel=self.filter_panel, visible=False)
        root.addWidget(controls)

        summary_grid = QGridLayout()
        summary_grid.setHorizontalSpacing(CFG.SPACING_MD)
        summary_grid.setVerticalSpacing(CFG.SPACING_MD)
        self.summary_cards = [
            KpiCard("Open work orders", "-", "", CFG.COLOR_ACCENT),
            KpiCard("In progress", "-", "", CFG.COLOR_SUCCESS),
            KpiCard("Overdue", "-", "", CFG.COLOR_WARNING),
            KpiCard("Completed", "-", "", CFG.COLOR_SUCCESS),
            KpiCard("Open downtime", "-", "", CFG.COLOR_DANGER),
            KpiCard("Downtime minutes", "-", "", CFG.COLOR_ACCENT),
            KpiCard("MTTR hours", "-", "", CFG.COLOR_WARNING),
            KpiCard("MTBF hours", "-", "", CFG.COLOR_SUCCESS),
        ]
        for index, card in enumerate(self.summary_cards):
            summary_grid.addWidget(card, index // 4, index % 4)
        root.addLayout(summary_grid)

        content_row = QHBoxLayout()
        content_row.setSpacing(CFG.SPACING_MD)
        content_row.addWidget(self._build_metric_table_panel(), 1)
        content_row.addWidget(self._build_root_cause_panel(), 2)
        root.addLayout(content_row, 1)
        root.addWidget(self._build_recurring_panel(), 1)

        self.site_combo.currentIndexChanged.connect(self._on_site_changed)
        self.asset_combo.currentIndexChanged.connect(
            make_guarded_slot(self, title="Maintenance Dashboard", callback=self.reload_dashboard)
        )
        self.system_combo.currentIndexChanged.connect(
            make_guarded_slot(self, title="Maintenance Dashboard", callback=self.reload_dashboard)
        )
        self.location_combo.currentIndexChanged.connect(
            make_guarded_slot(self, title="Maintenance Dashboard", callback=self.reload_dashboard)
        )
        self.days_combo.currentIndexChanged.connect(
            make_guarded_slot(self, title="Maintenance Dashboard", callback=self.reload_dashboard)
        )
        self.btn_refresh.clicked.connect(
            make_guarded_slot(self, title="Maintenance Dashboard", callback=self.reload_data)
        )
        self.btn_filters.clicked.connect(self._toggle_filters)

    def _build_metric_table_panel(self) -> QWidget:
        panel, layout = build_admin_surface_card(
            object_name="maintenanceDashboardBacklogSurface",
            alt=False,
        )
        title = QLabel("Backlog Profile")
        title.setStyleSheet(CFG.SECTION_BOLD_MARGIN_STYLE)
        subtitle = QLabel("Status and priority splits for the selected maintenance scope.")
        subtitle.setStyleSheet(CFG.INFO_TEXT_STYLE)
        subtitle.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        self.backlog_table = build_admin_table(
            headers=("Metric", "Value"),
            resize_modes=(self._resize_to_contents(), self._stretch()),
        )
        layout.addWidget(self.backlog_table)
        return panel

    def _build_root_cause_panel(self) -> QWidget:
        panel, layout = build_admin_surface_card(
            object_name="maintenanceDashboardRootCauseSurface",
            alt=False,
        )
        title = QLabel("Top Root Causes")
        title.setStyleSheet(CFG.SECTION_BOLD_MARGIN_STYLE)
        subtitle = QLabel("Frequent failure and cause combinations across recent work.")
        subtitle.setStyleSheet(CFG.INFO_TEXT_STYLE)
        subtitle.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        self.root_cause_table = build_admin_table(
            headers=("Failure", "Root Cause", "Count", "Downtime", "Latest"),
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
            object_name="maintenanceDashboardRecurringSurface",
            alt=False,
        )
        title = QLabel("Recurring Failures")
        title.setStyleSheet(CFG.SECTION_BOLD_MARGIN_STYLE)
        subtitle = QLabel("Assets, systems, or locations showing repeated failure patterns.")
        subtitle.setStyleSheet(CFG.INFO_TEXT_STYLE)
        subtitle.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        self.recurring_table = build_admin_table(
            headers=("Anchor", "Failure", "Lead Cause", "Count", "Downtime", "Interval"),
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
        except BusinessRuleError as exc:
            QMessageBox.warning(self, "Maintenance Dashboard", str(exc))
            return
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Maintenance Dashboard", f"Failed to load maintenance filters: {exc}")
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
        self.reload_dashboard()

    def reload_dashboard(self) -> None:
        try:
            dashboard = self._reliability_service.build_reliability_dashboard(
                site_id=selected_combo_value(self.site_combo),
                asset_id=selected_combo_value(self.asset_combo),
                system_id=selected_combo_value(self.system_combo),
                location_id=selected_combo_value(self.location_combo),
                days=self._selected_days(),
                limit=10,
            )
        except BusinessRuleError as exc:
            QMessageBox.warning(self, "Maintenance Dashboard", str(exc))
            return
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Maintenance Dashboard", f"Failed to load dashboard: {exc}")
            return

        for index, metric in enumerate(dashboard.summary[: len(self.summary_cards)]):
            card = self.summary_cards[index]
            card.set_title(metric.label)
            card.set_value(display_metric(metric.value))
        self.context_badge.setText(f"Context: {self._context_label()}")
        self.window_badge.setText(f"{self._selected_days()} day window")
        self.recurring_badge.setText(f"{len(dashboard.recurring_failures)} recurring patterns")
        self.filter_summary.setText(
            "Filters: "
            f"{self.site_combo.currentText()} | {self.asset_combo.currentText()} | "
            f"{self.system_combo.currentText()} | {self.location_combo.currentText()} | "
            f"{self.days_combo.currentText()}"
        )
        self._populate_backlog_table(dashboard)
        self._populate_root_cause_table(dashboard)
        self._populate_recurring_table(dashboard)

    def _populate_backlog_table(self, dashboard) -> None:
        rows = list(dashboard.backlog_by_status) + list(dashboard.backlog_by_priority)
        self.backlog_table.setRowCount(len(rows))
        for row_index, metric in enumerate(rows):
            self.backlog_table.setItem(row_index, 0, QTableWidgetItem(metric.label))
            self.backlog_table.setItem(row_index, 1, QTableWidgetItem(display_metric(metric.value)))

    def _populate_root_cause_table(self, dashboard) -> None:
        self.root_cause_table.setRowCount(len(dashboard.top_root_causes))
        for row_index, row in enumerate(dashboard.top_root_causes):
            values = (
                row.failure_name,
                row.root_cause_name,
                str(row.work_order_count),
                str(row.total_downtime_minutes),
                format_timestamp(row.latest_occurrence_at),
            )
            for column, value in enumerate(values):
                self.root_cause_table.setItem(row_index, column, QTableWidgetItem(value))

    def _populate_recurring_table(self, dashboard) -> None:
        self.recurring_table.setRowCount(len(dashboard.recurring_failures))
        for row_index, row in enumerate(dashboard.recurring_failures):
            values = (
                f"{row.anchor_code} - {row.anchor_name}",
                row.failure_name,
                row.leading_root_cause_name or "-",
                str(row.occurrence_count),
                str(row.total_downtime_minutes),
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


__all__ = ["MaintenanceDashboardTab"]

from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from src.ui.platform.workspaces.admin.support.surface import build_support_header, style_support_button, update_support_header_badges
from src.ui.shared.widgets.guards import make_guarded_slot
from src.ui.shared.formatting.ui_config import UIConfig as CFG


class SupportUiLayoutMixin:
    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)
        root.setSpacing(CFG.SPACING_MD)

        build_support_header(self, root)

        update_group = QGroupBox("Release Channel")
        update_group.setFont(CFG.GROUPBOX_TITLE_FONT)
        update_form = QFormLayout(update_group)
        update_form.setSpacing(CFG.SPACING_SM)

        self.channel_combo = QComboBox()
        self.channel_combo.setFixedHeight(CFG.INPUT_HEIGHT)
        self.channel_combo.addItem("Stable", userData="stable")
        self.channel_combo.addItem("Beta", userData="beta")

        self.auto_check = QCheckBox("Check for updates automatically at startup")
        self.manifest_url = QLineEdit()
        self.manifest_url.setPlaceholderText("Manifest URL or local file path")
        self.manifest_url.setMinimumHeight(CFG.INPUT_HEIGHT)

        update_form.addRow("Channel:", self.channel_combo)
        update_form.addRow("Manifest source:", self.manifest_url)
        update_form.addRow("", self.auto_check)

        update_buttons = QHBoxLayout()
        self.btn_save_update_settings = QPushButton("Save Update Settings")
        self.btn_check_updates = QPushButton("Check for Updates")
        style_support_button(self.btn_save_update_settings, "secondary")
        style_support_button(self.btn_check_updates, "primary")
        for btn in (self.btn_save_update_settings, self.btn_check_updates):
            update_buttons.addWidget(btn)
        update_buttons.addStretch()
        update_form.addRow(update_buttons)
        root.addWidget(update_group)

        diag_group = QGroupBox("Diagnostics")
        diag_group.setFont(CFG.GROUPBOX_TITLE_FONT)
        diag_layout = QVBoxLayout(diag_group)
        diag_layout.setSpacing(CFG.SPACING_SM)

        diag_hint = QLabel(
            "Build a diagnostics zip with metadata, logs, structured telemetry, and optional DB snapshot."
        )
        diag_hint.setStyleSheet(CFG.INFO_TEXT_STYLE)
        diag_hint.setWordWrap(True)
        diag_layout.addWidget(diag_hint)

        incident_row = QHBoxLayout()
        self.incident_id_input = QLineEdit()
        self.incident_id_input.setMinimumHeight(CFG.INPUT_HEIGHT)
        self.incident_id_input.setPlaceholderText("Incident trace ID")
        self.btn_new_incident = QPushButton("New Incident")
        self.btn_copy_incident = QPushButton("Copy ID")
        style_support_button(self.btn_new_incident, "secondary")
        style_support_button(self.btn_copy_incident, "secondary")
        incident_row.addWidget(QLabel("Incident ID:"))
        incident_row.addWidget(self.incident_id_input, 1)
        incident_row.addWidget(self.btn_new_incident)
        incident_row.addWidget(self.btn_copy_incident)
        diag_layout.addLayout(incident_row)

        diag_buttons = QHBoxLayout()
        self.btn_export_diagnostics = QPushButton("Export Diagnostics Bundle")
        self.btn_report_incident = QPushButton("Report Incident")
        self.btn_open_logs = QPushButton("Open Logs Folder")
        self.btn_open_data = QPushButton("Open Data Folder")
        for btn, variant in (
            (self.btn_export_diagnostics, "primary"),
            (self.btn_report_incident, "secondary"),
            (self.btn_open_logs, "secondary"),
            (self.btn_open_data, "secondary"),
        ):
            style_support_button(btn, variant)
            diag_buttons.addWidget(btn)
        diag_buttons.addStretch()
        diag_layout.addLayout(diag_buttons)
        root.addWidget(diag_group)

        self.result_box = QTextEdit()
        self.result_box.setReadOnly(True)
        self.result_box.setMinimumHeight(220)
        self.result_box.setPlaceholderText("Support activity and update check results appear here.")
        root.addWidget(self.result_box, 1)

        self.btn_save_update_settings.clicked.connect(
            make_guarded_slot(self, title="Support", callback=self._save_update_settings)
        )
        self.btn_check_updates.clicked.connect(
            make_guarded_slot(self, title="Support", callback=self._check_updates)
        )
        self.btn_new_incident.clicked.connect(
            make_guarded_slot(self, title="Support", callback=self._new_incident_id)
        )
        self.btn_copy_incident.clicked.connect(
            make_guarded_slot(self, title="Support", callback=self._copy_incident_id)
        )
        self.btn_export_diagnostics.clicked.connect(
            make_guarded_slot(self, title="Support", callback=self._export_diagnostics)
        )
        self.btn_report_incident.clicked.connect(
            make_guarded_slot(self, title="Support", callback=self._report_incident)
        )
        self.btn_open_logs.clicked.connect(
            make_guarded_slot(self, title="Support", callback=self._open_logs_folder)
        )
        self.btn_open_data.clicked.connect(
            make_guarded_slot(self, title="Support", callback=self._open_data_folder)
        )

    def _update_support_header_badges(self) -> None:
        update_support_header_badges(self)


__all__ = ["SupportUiLayoutMixin"]

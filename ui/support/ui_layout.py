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

from ui.shared.guards import make_guarded_slot
from ui.styles.ui_config import UIConfig as CFG


class SupportUiLayoutMixin:
    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)
        root.setSpacing(CFG.SPACING_MD)

        title = QLabel("Support & Updates")
        title.setStyleSheet(CFG.TITLE_LARGE_STYLE)
        subtitle = QLabel(
            "Admin tooling for release checks, diagnostics export, and operational incident tracing."
        )
        subtitle.setStyleSheet(CFG.INFO_TEXT_STYLE)
        subtitle.setWordWrap(True)
        root.addWidget(title)
        root.addWidget(subtitle)

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
        for btn in (self.btn_save_update_settings, self.btn_check_updates):
            btn.setFixedHeight(CFG.BUTTON_HEIGHT)
            btn.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
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
        for btn in (self.btn_new_incident, self.btn_copy_incident):
            btn.setFixedHeight(CFG.BUTTON_HEIGHT)
            btn.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
        incident_row.addWidget(QLabel("Incident ID:"))
        incident_row.addWidget(self.incident_id_input, 1)
        incident_row.addWidget(self.btn_new_incident)
        incident_row.addWidget(self.btn_copy_incident)
        diag_layout.addLayout(incident_row)

        diag_buttons = QHBoxLayout()
        self.btn_export_diagnostics = QPushButton("Export Diagnostics Bundle")
        self.btn_open_logs = QPushButton("Open Logs Folder")
        self.btn_open_data = QPushButton("Open Data Folder")
        for btn in (self.btn_export_diagnostics, self.btn_open_logs, self.btn_open_data):
            btn.setFixedHeight(CFG.BUTTON_HEIGHT)
            btn.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
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
        self.btn_open_logs.clicked.connect(
            make_guarded_slot(self, title="Support", callback=self._open_logs_folder)
        )
        self.btn_open_data.clicked.connect(
            make_guarded_slot(self, title="Support", callback=self._open_data_folder)
        )


__all__ = ["SupportUiLayoutMixin"]

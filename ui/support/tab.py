from __future__ import annotations

from PySide6.QtWidgets import QWidget

from core.services.auth import UserSessionContext
from infra.operational_support import get_operational_support
from ui.settings import MainWindowSettingsStore
from ui.support.diagnostics_flow import SupportDiagnosticsFlowMixin
from ui.support.telemetry import SupportTelemetryMixin
from ui.support.ui_layout import SupportUiLayoutMixin
from ui.support.update_flow import SupportUpdateFlowMixin


class SupportTab(
    SupportUiLayoutMixin,
    SupportTelemetryMixin,
    SupportUpdateFlowMixin,
    SupportDiagnosticsFlowMixin,
    QWidget,
):
    """Support tab coordinator: compose UI, update flow, diagnostics flow, telemetry."""

    def __init__(
        self,
        *,
        settings_store: MainWindowSettingsStore,
        user_session: UserSessionContext | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._settings_store = settings_store
        self._user_session = user_session
        self._ops_support = get_operational_support()
        self._setup_ui()
        self.incident_id_input.setText(self._ops_support.new_incident_id())
        self._load_settings()


__all__ = ["SupportTab"]

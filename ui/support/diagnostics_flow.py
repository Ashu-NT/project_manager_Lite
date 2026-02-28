from __future__ import annotations

from ui.support.diagnostics_export import SupportDiagnosticsExportMixin
from ui.support.incident_report import DEFAULT_SUPPORT_EMAIL, SupportIncidentReportMixin


class SupportDiagnosticsFlowMixin(
    SupportIncidentReportMixin,
    SupportDiagnosticsExportMixin,
):
    """Facade mixin combining diagnostics export and incident report workflows."""


__all__ = ["DEFAULT_SUPPORT_EMAIL", "SupportDiagnosticsFlowMixin"]

from __future__ import annotations

import os
from datetime import datetime

from PySide6.QtWidgets import QApplication, QMessageBox

from infra.diagnostics import DiagnosticsBundleResult, build_diagnostics_bundle
from infra.operational_support import bind_trace_id
from infra.path import user_data_dir
from ui.shared.async_job import JobUiConfig, start_async_job
from ui.support.incident_mail import (
    clipboard_email_template,
    compose_incident_email,
    open_incident_mailto,
)

DEFAULT_SUPPORT_EMAIL = "tech_ash_673@info.tech"


class SupportIncidentReportMixin:
    @staticmethod
    def _support_email() -> str:
        override = (os.getenv("PM_SUPPORT_EMAIL") or "").strip()
        return override or DEFAULT_SUPPORT_EMAIL

    def _report_incident(self) -> None:
        incident_id = self._current_incident_id()
        generated_at = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_dir = user_data_dir() / "incidents"
        out_dir.mkdir(parents=True, exist_ok=True)
        output_path = out_dir / f"pm_incident_{incident_id}_{generated_at}.zip"
        support_email = self._support_email()

        self._emit_support_event(
            event_type="support.incident.report_started",
            message="Started incident report packaging.",
            trace_id=incident_id,
            data={"output_path": str(output_path), "support_email": support_email},
        )

        def _work(token, progress):
            with bind_trace_id(incident_id):
                token.raise_if_cancelled()
                progress(None, "Collecting diagnostics for incident report...")
                result = build_diagnostics_bundle(
                    output_path=output_path,
                    settings_snapshot=self._settings_snapshot(),
                    include_db_copy=True,
                    incident_id=incident_id,
                )
                token.raise_if_cancelled()
                return result

        start_async_job(
            parent=self,
            ui=JobUiConfig(
                title="Report Incident",
                label="Preparing incident package...",
                allow_retry=True,
            ),
            work=_work,
            on_success=lambda result: self._handle_incident_report_result(
                result,
                incident_id=incident_id,
                support_email=support_email,
            ),
            on_error=lambda msg: self._handle_async_error(
                title="Report Incident",
                context="Incident report",
                event_type="support.incident.report_failed",
                message=msg,
            ),
            on_cancel=lambda: self._on_incident_report_canceled(incident_id),
            set_busy=self._set_diag_busy,
        )

    def _on_incident_report_canceled(self, incident_id: str) -> None:
        self._append_result("Incident report canceled.")
        self._emit_support_event(
            event_type="support.incident.report_canceled",
            message="Incident report canceled by user.",
            trace_id=incident_id,
        )

    def _handle_incident_report_result(
        self,
        result: DiagnosticsBundleResult,
        *,
        incident_id: str,
        support_email: str,
    ) -> None:
        clipboard = QApplication.clipboard()
        if clipboard is not None:
            clipboard.setText(incident_id)

        subject_text, body_text = compose_incident_email(
            incident_id=incident_id,
            bundle_path=result.output_path,
        )
        opened_mail_client = open_incident_mailto(
            support_email=support_email,
            subject_text=subject_text,
            body_text=body_text,
        )

        self._emit_support_event(
            event_type="support.incident.report_ready",
            message="Incident report package is ready.",
            trace_id=incident_id,
            data={
                "output_path": str(result.output_path),
                "support_email": support_email,
                "files_added": result.files_added,
            },
        )
        self._append_result(
            f"Incident report ready: incident={incident_id} | bundle={result.output_path} | copied ID to clipboard."
        )
        if opened_mail_client:
            QMessageBox.information(
                self,
                "Report Incident",
                (
                    f"Incident package created.\n\n"
                    f"Incident ID (copied): {incident_id}\n"
                    f"Bundle: {result.output_path}\n"
                    f"Support Email: {support_email}\n\n"
                    "Your default mail client was opened with a prefilled incident report."
                ),
            )
            return

        if clipboard is not None:
            clipboard.setText(
                clipboard_email_template(
                    support_email=support_email,
                    subject_text=subject_text,
                    body_text=body_text,
                )
            )
        self._emit_support_event(
            event_type="support.incident.mail_client_unavailable",
            message="Mail client is unavailable for incident report.",
            trace_id=incident_id,
            data={"support_email": support_email, "bundle": str(result.output_path)},
        )
        QMessageBox.information(
            self,
            "Report Incident",
            (
                f"Incident package created.\n\n"
                f"Incident ID: {incident_id}\n"
                f"Bundle: {result.output_path}\n"
                f"Support Email: {support_email}\n\n"
                "No default mail app was found.\n"
                "A ready-to-send email template was copied to your clipboard.\n"
                "Open your email client, paste the template, and attach the bundle."
            ),
        )


__all__ = ["DEFAULT_SUPPORT_EMAIL", "SupportIncidentReportMixin"]

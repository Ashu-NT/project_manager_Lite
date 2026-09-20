from __future__ import annotations

from src.ui_qml.modules.project_management.utils.file_paths import (
    local_path_from_qml_file_url,
)


class FinancialsReportingMutationMixin:
    def _export_financials(self, report_format: str, output_path: str) -> None:
        normalized_path = local_path_from_qml_file_url(output_path)
        if not normalized_path:
            self._set_error_message("Choose an output file for the financial report.")
            return
        self._run_finance_mutation(
            lambda: self._financials_workspace_presenter.export_financial_report(
                project_id=self._selected_project_id,
                output_path=normalized_path,
                report_format=(report_format or "").strip().lower(),
                baseline_id=self._selected_baseline_id or None,
            ),
            f"Financial report exported to {normalized_path}.",
            on_success=lambda: None,
        )

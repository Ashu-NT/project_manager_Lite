from __future__ import annotations

from pathlib import Path

import pytest

from src.core.modules.project_management.api.desktop.financials.api import (
    ProjectManagementFinancialsDesktopApi,
)


def test_financial_report_export_passes_canonical_services_and_basis(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    reporting_service = object()
    finance_service = object()
    captured: dict[str, object] = {}

    def export_excel(service, project_id, output_path, **kwargs):
        captured.update(
            service=service,
            project_id=project_id,
            output_path=output_path,
            **kwargs,
        )
        return Path(output_path)

    monkeypatch.setattr(
        "src.core.modules.project_management.api.desktop.financials.api.generate_excel_report",
        export_excel,
    )
    api = ProjectManagementFinancialsDesktopApi(
        reporting_service=reporting_service,
        finance_service=finance_service,
    )
    output_path = tmp_path / "finance.xlsx"

    result = api.export_financial_report(
        "project-1",
        str(output_path),
        report_format="xlsx",
        baseline_id="baseline-2",
    )

    assert result == str(output_path)
    assert captured == {
        "service": reporting_service,
        "project_id": "project-1",
        "output_path": str(output_path),
        "finance_service": finance_service,
        "baseline_id": "baseline-2",
    }


def test_financial_report_rejects_unknown_format() -> None:
    api = ProjectManagementFinancialsDesktopApi(
        reporting_service=object(),
        finance_service=object(),
    )

    with pytest.raises(ValueError, match="xlsx.*pdf"):
        api.export_financial_report(
            "project-1",
            "finance.csv",
            report_format="csv",
        )

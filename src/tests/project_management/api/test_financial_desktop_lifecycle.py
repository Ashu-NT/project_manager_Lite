from __future__ import annotations

from pathlib import Path

import pytest

from src.core.modules.project_management.api.desktop.financials.api import (
    ProjectManagementFinancialsDesktopApi,
)
from src.core.platform.common.exceptions import ValidationError


def test_financial_report_export_passes_canonical_services_and_basis(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    report_sources = object()
    finance_snapshot_query = object()
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
        report_sources=report_sources,  # type: ignore[arg-type]
        finance_snapshot_query=finance_snapshot_query,
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
        "service": report_sources,
        "project_id": "project-1",
        "output_path": str(output_path),
        "finance_snapshot_query": finance_snapshot_query,
        "baseline_id": "baseline-2",
    }


def test_financial_report_rejects_unknown_format() -> None:
    api = ProjectManagementFinancialsDesktopApi(
        report_sources=object(),  # type: ignore[arg-type]
        finance_snapshot_query=object(),
    )

    with pytest.raises(ValidationError, match="xlsx.*pdf") as invalid:
        api.export_financial_report(
            "project-1",
            "finance.csv",
            report_format="csv",
        )
    assert invalid.value.code == "FINANCIAL_REPORT_FORMAT_INVALID"

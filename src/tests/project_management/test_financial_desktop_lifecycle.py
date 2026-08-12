from __future__ import annotations

from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.core.modules.project_management.api.desktop.financials.api import (
    ProjectManagementFinancialsDesktopApi,
)


def _enum(value: str) -> SimpleNamespace:
    return SimpleNamespace(value=value)


def _forecast(identifier: str, *, status: str = "approved") -> SimpleNamespace:
    return SimpleNamespace(
        id=identifier,
        name=f"Forecast {identifier}",
        status=_enum(status),
        revision=2,
        row_version=3,
        currency_code="USD",
        as_of_date=date(2026, 8, 1),
        generation_mode=_enum("automatic"),
        approved_at=None,
        notes="",
    )


def test_forecast_line_read_revalidates_project_ownership() -> None:
    class ForecastService:
        line_reads: list[str] = []

        def list_forecasts(self, project_id: str) -> list[SimpleNamespace]:
            assert project_id == "project-1"
            return [_forecast("forecast-1")]

        def list_lines(self, forecast_id: str) -> list[object]:
            self.line_reads.append(forecast_id)
            return []

    service = ForecastService()
    api = ProjectManagementFinancialsDesktopApi(forecast_version_service=service)

    assert api.list_forecast_lines("project-1", "foreign-forecast") == ()
    assert service.line_reads == []


def test_change_impact_read_revalidates_project_ownership() -> None:
    class ChangeService:
        impact_reads: list[str] = []

        def list_changes(self, project_id: str) -> list[SimpleNamespace]:
            assert project_id == "project-1"
            return [SimpleNamespace(id="change-1")]

        def list_impacts(self, change_id: str) -> list[object]:
            self.impact_reads.append(change_id)
            return []

    service = ChangeService()
    api = ProjectManagementFinancialsDesktopApi(financial_change_service=service)

    assert api.list_financial_change_impacts("project-1", "foreign-change") == ()
    assert service.impact_reads == []


def test_baseline_variance_does_not_hide_authorization_failures() -> None:
    class BaselineService:
        def list_baselines(self, project_id: str) -> list[object]:
            raise PermissionError(f"denied:{project_id}")

    api = ProjectManagementFinancialsDesktopApi(baseline_service=BaselineService())

    with pytest.raises(PermissionError, match="denied:project-1"):
        api.get_baseline_variance("project-1")


def test_baseline_variance_uses_only_governed_versions() -> None:
    draft = SimpleNamespace(
        id="draft", name="Draft", status=_enum("draft"), version=3,
        created_at=date(2026, 8, 2), approved_at=None,
    )
    approved = SimpleNamespace(
        id="approved", name="Control", status=_enum("approved"), version=2,
        created_at=date(2026, 8, 1), approved_at=date(2026, 8, 2),
    )

    class BaselineService:
        def list_baselines(self, project_id: str) -> list[object]:
            return [draft, approved]

        def list_variance_records(self, baseline_id: str) -> list[object]:
            assert baseline_id == "approved"
            return []

    api = ProjectManagementFinancialsDesktopApi(baseline_service=BaselineService())
    result = api.get_baseline_variance("project-1", "draft")

    assert result.selected_baseline_id == "approved"
    assert [item.id for item in result.baselines] == ["approved"]


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

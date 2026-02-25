"""Backward-compatible wrappers for reporting exports.

Deprecated:
    Import from ``core.reporting.api`` directly for new code.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from warnings import warn

from core.reporting.api import (
    generate_evm_png as _generate_evm_png,
    generate_excel_report as _generate_excel_report,
    generate_gantt_png as _generate_gantt_png,
    generate_pdf_report as _generate_pdf_report,
)
from core.services.finance import FinanceService
from core.services.reporting import ReportingService


def _warn_deprecated(function_name: str) -> None:
    warn(
        (
            f"`core.reporting.exporters.{function_name}` is deprecated. "
            "Use `core.reporting.api` instead."
        ),
        DeprecationWarning,
        stacklevel=2,
    )


def generate_gantt_png(
    reporting_service: ReportingService,
    project_id: str,
    output_path: str | Path,
) -> Path:
    _warn_deprecated("generate_gantt_png")
    return _generate_gantt_png(reporting_service, project_id, output_path)


def generate_evm_png(
    reporting_service: ReportingService,
    project_id: str,
    output_path: str | Path,
    baseline_id: str | None = None,
    as_of: date | None = None,
) -> Path:
    _warn_deprecated("generate_evm_png")
    return _generate_evm_png(
        reporting_service,
        project_id,
        output_path,
        baseline_id=baseline_id,
        as_of=as_of,
    )


def generate_excel_report(
    reporting_service: ReportingService,
    project_id: str,
    output_path: str | Path,
    finance_service: FinanceService | None = None,
    baseline_id: str | None = None,
    as_of: date | None = None,
) -> Path:
    _warn_deprecated("generate_excel_report")
    return _generate_excel_report(
        reporting_service,
        project_id,
        output_path,
        finance_service=finance_service,
        baseline_id=baseline_id,
        as_of=as_of,
    )


def generate_pdf_report(
    reporting_service: ReportingService,
    project_id: str,
    output_path: str | Path,
    temp_dir: str | Path = "tmp_reports",
    finance_service: FinanceService | None = None,
    baseline_id: str | None = None,
    as_of: date | None = None,
) -> Path:
    _warn_deprecated("generate_pdf_report")
    return _generate_pdf_report(
        reporting_service,
        project_id,
        output_path,
        temp_dir=temp_dir,
        finance_service=finance_service,
        baseline_id=baseline_id,
        as_of=as_of,
    )


__all__ = [
    "generate_gantt_png",
    "generate_evm_png",
    "generate_excel_report",
    "generate_pdf_report",
]

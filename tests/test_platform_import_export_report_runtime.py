from __future__ import annotations

import ast
from pathlib import Path

import pytest

from core.platform.exporting import ExportDefinitionRegistry, ExportRuntime
from core.platform.importing import (
    ImportDefinitionRegistry,
    ImportFieldSpec,
    ImportPreview,
    ImportPreviewRow,
    ImportSummary,
)
from core.platform.report_runtime import ReportDefinitionRegistry, ReportRuntime


ROOT = Path(__file__).resolve().parents[1]


class _DummyImportDefinition:
    operation_key = "tasks"
    module_code = "project_management"
    permission_code = "import.manage"

    def field_specs(self) -> tuple[ImportFieldSpec, ...]:
        return (ImportFieldSpec(key="name", label="Name", required=True),)

    def preview(self, rows) -> ImportPreview:
        return ImportPreview(
            entity_type="tasks",
            available_columns=[],
            mapped_columns={},
            rows=[
                ImportPreviewRow(
                    line_no=rows[0].line_no,
                    status="READY",
                    action="CREATE",
                    message="Ready",
                    row=dict(rows[0].values),
                )
            ],
            created_count=len(rows),
        )

    def execute(self, rows) -> ImportSummary:
        return ImportSummary(entity_type="tasks", created_count=len(rows))


class _DummyExportDefinition:
    operation_key = "artifact"
    module_code = "project_management"
    permission_code = "report.export"

    def export(self, request: object):
        return request


class _DummyReportDefinition:
    report_key = "summary"
    module_code = "project_management"
    permission_code = "report.export"
    supported_formats = ("pdf",)

    def render(self, request: object) -> object:
        return {"request": request}


def _python_files(root: Path):
    for path in root.rglob("*.py"):
        yield path


def test_import_definition_registry_rejects_duplicates() -> None:
    registry = ImportDefinitionRegistry()
    registry.register(_DummyImportDefinition())

    with pytest.raises(ValueError, match="already registered"):
        registry.register(_DummyImportDefinition())


def test_export_runtime_normalizes_export_artifacts(tmp_path: Path) -> None:
    registry = ExportDefinitionRegistry()
    registry.register(_DummyExportDefinition())
    runtime = ExportRuntime(registry)

    artifact = runtime.export("artifact", tmp_path / "report.pdf")

    assert artifact.file_path == tmp_path / "report.pdf"
    assert artifact.file_name == "report.pdf"


def test_report_runtime_dispatches_registered_definitions() -> None:
    registry = ReportDefinitionRegistry()
    registry.register(_DummyReportDefinition())
    runtime = ReportRuntime(registry)

    result = runtime.render("summary", {"project_id": "p1"})

    assert result == {"request": {"project_id": "p1"}}


def test_import_summary_tracks_structured_and_legacy_row_errors() -> None:
    summary = ImportSummary(entity_type="tasks")

    row_error = summary.add_row_error(line_no=3, message="Missing required column 'name'.")

    assert summary.error_count == 1
    assert summary.error_rows == ["line 3: Missing required column 'name'."]
    assert summary.row_errors == [row_error]


def test_platform_runtime_packages_do_not_import_module_code() -> None:
    packages = (
        ROOT / "core" / "platform" / "importing",
        ROOT / "core" / "platform" / "exporting",
        ROOT / "core" / "platform" / "report_runtime",
    )
    violations: list[tuple[str, str]] = []

    for package_root in packages:
        for path in _python_files(package_root):
            source = path.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        name = alias.name
                        if name.startswith("core.modules.") or name.startswith("infra.modules.") or name.startswith("ui.modules."):
                            violations.append((str(path.relative_to(ROOT)), name))
                elif isinstance(node, ast.ImportFrom):
                    mod = node.module or ""
                    if mod.startswith("core.modules.") or mod.startswith("infra.modules.") or mod.startswith("ui.modules."):
                        violations.append((str(path.relative_to(ROOT)), mod))

    assert not violations, f"Platform runtime packages import module code: {violations}"

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from src.core.platform.exporting import ExportArtifactDraft, ExportDefinitionRegistry, ExportRuntime
from src.core.platform.report_runtime import ReportDefinitionRegistry, ReportRuntime


class _TrackingExportDefinition:
    def __init__(self, operation_key: str, module_code: str = "project_management") -> None:
        self.operation_key = operation_key
        self.module_code = module_code
        self.permission_code = "report.export"

    def export(self, request: object):
        return ExportArtifactDraft(
            file_path=Path(request),
            file_name=Path(request).name,
            media_type="text/csv",
        )


class _TrackingReportDefinition:
    def __init__(self, report_key: str, module_code: str = "project_management") -> None:
        self.report_key = report_key
        self.module_code = module_code
        self.permission_code = "report.export"
        self.supported_formats = ("pdf",)

    def render(self, request: object):
        return ExportArtifactDraft(
            file_path=Path(request),
            file_name=Path(request).name,
            media_type="application/pdf",
        )


def _unique_key(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:8]}"


def test_runtime_execution_service_tracks_cancellation_and_retry_metadata(services):
    runtime = services["runtime_execution_service"]

    execution = runtime.start_execution(
        operation_type="report",
        operation_key=_unique_key("maintenance_backlog"),
        module_code="maintenance_management",
        input_path="maintenance.xlsx",
        output_path="maintenance-report.xlsx",
    )
    runtime.request_cancellation(execution.id)
    requested = runtime.get_execution(execution.id)
    assert requested is not None
    assert requested.status == "CANCELLATION_REQUESTED"
    assert requested.cancellation_requested_at is not None
    assert requested.cancellation_requested_by_username == "admin"
    cancelled = runtime.cancel_execution(requested, error_message="Cancelled from queue")
    retry = runtime.start_retry(cancelled.id, output_path="maintenance-report-retry.xlsx")

    assert cancelled.status == "CANCELLED"
    assert cancelled.completed_at is not None
    assert cancelled.error_message == "Cancelled from queue"
    assert retry.retry_of_execution_id == cancelled.id
    assert retry.attempt_number == 2
    assert retry.output_path == "maintenance-report-retry.xlsx"


def test_export_runtime_records_artifact_metadata_in_execution_history(services, tmp_path):
    operation_key = _unique_key("runtime_export")
    registry = ExportDefinitionRegistry()
    registry.register(_TrackingExportDefinition(operation_key))
    runtime = ExportRuntime(
        registry,
        user_session=services["user_session"],
        module_catalog_service=services["module_catalog_service"],
        runtime_execution_service=services["runtime_execution_service"],
    )

    artifact_path = tmp_path / "runtime-export.csv"
    artifact = runtime.export(operation_key, artifact_path)
    executions = services["runtime_execution_service"].list_recent(
        limit=10,
        module_code="project_management",
        status="COMPLETED",
    )
    execution = next(row for row in executions if row.operation_key == operation_key)

    assert artifact.file_name == "runtime-export.csv"
    assert execution.output_path == str(artifact_path)
    assert execution.output_file_name == "runtime-export.csv"
    assert execution.output_media_type == "text/csv"
    assert execution.output_metadata == {}


def test_report_runtime_records_artifact_metadata_and_list_filters(services, tmp_path):
    report_key = _unique_key("runtime_report")
    registry = ReportDefinitionRegistry()
    registry.register(_TrackingReportDefinition(report_key))
    runtime = ReportRuntime(
        registry,
        user_session=services["user_session"],
        module_catalog_service=services["module_catalog_service"],
        runtime_execution_service=services["runtime_execution_service"],
    )

    output_path = tmp_path / "runtime-report.pdf"
    rendered = runtime.render(report_key, output_path)

    completed = services["runtime_execution_service"].list_recent(
        limit=10,
        module_code="project_management",
        status="COMPLETED",
    )
    running = services["runtime_execution_service"].list_recent(
        limit=10,
        module_code="project_management",
        status="RUNNING",
    )
    execution = next(row for row in completed if row.operation_key == report_key)

    assert rendered.file_name == "runtime-report.pdf"
    assert execution.output_path == str(output_path)
    assert execution.output_file_name == "runtime-report.pdf"
    assert execution.output_media_type == "application/pdf"
    assert running == []

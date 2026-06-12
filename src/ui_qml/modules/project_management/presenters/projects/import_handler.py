from __future__ import annotations

from src.core.modules.project_management.infrastructure.importers.scheduling.mpp.mpp_parser import (
    MSProjectXmlParser,
)
from src.core.modules.project_management.infrastructure.importers.scheduling.primavera.p6_parser import (
    P6Parser,
)
from src.core.modules.project_management.infrastructure.importers.services.validation import (
    ImportValidationService,
    ImportValidationSeverity,
)
from src.core.modules.project_management.infrastructure.importers.utils.csv_parser import (
    CsvImportParser,
)
from src.ui_qml.modules.project_management.utils.file_paths import local_path_from_qml_file_url

_PARSERS = {
    "csv": CsvImportParser,
    "ms_project_xml": MSProjectXmlParser,
    "p6_xer": P6Parser,
}


def preview_import(
    import_sessions: dict[str, object],
    *,
    file_path: str,
    source_format: str,
) -> dict[str, object]:
    normalized_path = local_path_from_qml_file_url(file_path)
    normalized_format = (source_format or "csv").strip().lower()
    parser_cls = _PARSERS.get(normalized_format)
    if parser_cls is None:
        raise ValueError(
            f"Unsupported import format: '{source_format}'. "
            "Supported formats: csv, ms_project_xml, p6_xer."
        )
    try:
        with open(normalized_path, "rb") as fh:
            source_bytes = fh.read()
    except OSError as exc:
        raise ValueError(f"Cannot read file: {exc}") from exc

    rows = parser_cls().parse(source_bytes)
    svc = ImportValidationService()
    issues = svc.validate(rows)
    preview = svc.build_preview(rows, issues)
    import_sessions[preview.session_id] = preview
    return serialize_import_preview(preview)


def execute_import(
    import_sessions: dict[str, object],
    *,
    session_id: str,
) -> dict[str, object]:
    normalized_id = (session_id or "").strip()
    preview = import_sessions.get(normalized_id)
    if preview is None:
        raise ValueError("Import session not found or expired. Please re-upload the file.")
    if not preview.can_commit:
        raise ValueError(
            f"Cannot import: {preview.error_rows} row(s) have errors. "
            "Fix the source file and re-upload."
        )
    del import_sessions[normalized_id]
    return {
        "ok": True,
        "importedCount": preview.valid_rows,
        "message": f"Import accepted. {preview.valid_rows} task(s) staged for this project.",
    }


def serialize_import_preview(preview) -> dict[str, object]:
    error_row_numbers = {
        issue.row_number
        for issue in preview.issues
        if issue.severity == ImportValidationSeverity.ERROR
    }
    rows_view = []
    for row in preview.rows[:50]:
        rows_view.append({
            "rowNumber": row.row_number,
            "name": str(
                row.mapped_data.get("name") or row.mapped_data.get("task_name") or ""
            ),
            "startDate": str(row.mapped_data.get("start_date") or ""),
            "endDate": str(
                row.mapped_data.get("end_date") or row.mapped_data.get("finish_date") or ""
            ),
            "hasErrors": row.has_errors or row.row_number in error_row_numbers,
        })
    return {
        "sessionId": preview.session_id,
        "totalRows": preview.total_rows,
        "validRows": preview.valid_rows,
        "errorRows": preview.error_rows,
        "warningRows": preview.warning_rows,
        "canCommit": preview.can_commit,
        "rows": rows_view,
        "issueCount": len(preview.issues),
    }

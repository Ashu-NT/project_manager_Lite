"""Map neutral import staging results to the QML import flow."""

from src.core.modules.project_management.application.projects.dto.responses.import_preview import (
    ImportPreviewModel,
    ImportValidationSeverity,
    ProjectImportStagingResult,
)


def build_import_preview(preview: ImportPreviewModel) -> dict[str, object]:
    error_row_numbers = {
        issue.row_number
        for issue in preview.issues
        if issue.severity == ImportValidationSeverity.ERROR
    }
    rows_view = []
    for row in preview.rows[:50]:
        rows_view.append(
            {
                "rowNumber": row.row_number,
                "name": str(
                    row.mapped_data.get("name")
                    or row.mapped_data.get("task_name")
                    or ""
                ),
                "startDate": str(row.mapped_data.get("start_date") or ""),
                "endDate": str(
                    row.mapped_data.get("end_date")
                    or row.mapped_data.get("finish_date")
                    or ""
                ),
                "hasErrors": row.has_errors or row.row_number in error_row_numbers,
            }
        )
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


def build_import_staging_result(
    result: ProjectImportStagingResult,
) -> dict[str, object]:
    return {
        "ok": True,
        "importedCount": result.staged_count,
        "message": f"Import accepted. {result.staged_count} task(s) staged for this project.",
    }

"""Desktop import preview adapter over concrete file parsers."""

from __future__ import annotations

from collections.abc import Callable

from src.core.modules.project_management.application.projects.dto.responses.import_preview import (
    ImportPreviewModel,
    ProjectImportStagingResult,
)
from src.core.modules.project_management.infrastructure.importers.models.import_models import (
    ImportParser,
)
from src.core.modules.project_management.infrastructure.importers.scheduling.mpp.mpp_parser import (
    MSProjectXmlParser,
)
from src.core.modules.project_management.infrastructure.importers.scheduling.primavera.p6_parser import (
    P6Parser,
)
from src.core.modules.project_management.infrastructure.importers.services.validation import (
    ImportValidationService,
)
from src.core.modules.project_management.infrastructure.importers.utils.csv_parser import (
    CsvImportParser,
)
from src.core.platform.common.exceptions import (
    BusinessRuleError,
    NotFoundError,
    ValidationError,
)

_PARSERS: dict[str, Callable[[], ImportParser]] = {
    "csv": CsvImportParser,
    "ms_project_xml": MSProjectXmlParser,
    "p6_xer": P6Parser,
}


def preview_import(
    import_sessions: dict[str, object],
    *,
    file_path: str,
    source_format: str,
) -> ImportPreviewModel:
    normalized_format = (source_format or "csv").strip().lower()
    parser_cls = _PARSERS.get(normalized_format)
    if parser_cls is None:
        raise ValidationError(
            f"Unsupported import format: '{source_format}'. "
            "Supported formats: csv, ms_project_xml, p6_xer.",
            code="IMPORT_FORMAT_UNSUPPORTED",
        )
    try:
        with open(file_path, "rb") as fh:
            source_bytes = fh.read()
    except OSError as exc:
        raise ValidationError(
            "Cannot read the import file. Check that it is accessible and try again.",
            code="IMPORT_FILE_UNREADABLE",
        ) from exc

    rows = parser_cls().parse(source_bytes)
    svc = ImportValidationService()
    issues = svc.validate(rows)
    preview = svc.build_preview(rows, issues)
    import_sessions[preview.session_id] = preview
    return preview


def execute_import(
    import_sessions: dict[str, object],
    *,
    session_id: str,
) -> ProjectImportStagingResult:
    normalized_id = (session_id or "").strip()
    preview = import_sessions.get(normalized_id)
    if not isinstance(preview, ImportPreviewModel):
        raise NotFoundError(
            "Import session not found or expired. Please re-upload the file.",
            code="IMPORT_SESSION_NOT_FOUND",
        )
    if not preview.can_commit:
        raise BusinessRuleError(
            f"Cannot import: {preview.error_rows} row(s) have errors. "
            "Fix the source file and re-upload.",
            code="IMPORT_PREVIEW_HAS_ERRORS",
        )
    del import_sessions[normalized_id]
    return ProjectImportStagingResult(staged_count=preview.valid_rows)

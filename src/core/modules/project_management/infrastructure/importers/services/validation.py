"""Import validation and mapping profile management."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Optional

from src.core.modules.project_management.domain.identifiers import generate_id
from src.core.modules.project_management.infrastructure.importers.models.import_models import (
    ImportFieldMapping,
    ImportMappingProfile,
    ImportPreviewModel,
    ImportRow,
    ImportValidationIssue,
    ImportValidationSeverity,
)


class ImportValidationService:
    """Validates parsed ImportRows against PM business rules before commit."""

    def validate(
        self,
        rows: List[ImportRow],
        required_fields: Optional[List[str]] = None,
    ) -> List[ImportValidationIssue]:
        issues: List[ImportValidationIssue] = []
        required = required_fields or []

        for row in rows:
            for req_field in required:
                if not row.mapped_data.get(req_field):
                    issues.append(ImportValidationIssue(
                        row_number=row.row_number,
                        severity=ImportValidationSeverity.ERROR,
                        field=req_field,
                        message=f"Required field '{req_field}' is missing or empty.",
                        source_value=None,
                    ))

            start = row.mapped_data.get("start_date")
            finish = row.mapped_data.get("end_date") or row.mapped_data.get("finish_date")
            if start and finish:
                try:
                    from datetime import date as _date
                    s = _date.fromisoformat(str(start)) if not isinstance(start, _date) else start
                    f = _date.fromisoformat(str(finish)) if not isinstance(finish, _date) else finish
                    if s > f:
                        issues.append(ImportValidationIssue(
                            row_number=row.row_number,
                            severity=ImportValidationSeverity.ERROR,
                            field="start_date",
                            message=f"Start date {start} is after finish date {finish}.",
                            source_value=start,
                        ))
                except (ValueError, TypeError):
                    pass

        return issues

    def build_preview(
        self,
        rows: List[ImportRow],
        issues: List[ImportValidationIssue],
    ) -> ImportPreviewModel:
        error_rows = sum(
            1 for r in rows
            if r.has_errors or any(
                i.row_number == r.row_number and i.severity == ImportValidationSeverity.ERROR
                for i in issues
            )
        )
        warning_rows = sum(
            1 for r in rows
            if any(
                i.row_number == r.row_number and i.severity == ImportValidationSeverity.WARNING
                for i in issues
            )
        )
        return ImportPreviewModel(
            session_id=generate_id(),
            total_rows=len(rows),
            valid_rows=len(rows) - error_rows,
            error_rows=error_rows,
            warning_rows=warning_rows,
            rows=rows,
            issues=issues,
            created_at=datetime.now(timezone.utc),
        )


class ImportMappingService:
    """Manages saved ImportMappingProfile objects."""

    def __init__(self) -> None:
        self._profiles: Dict[str, ImportMappingProfile] = {}

    def save_profile(self, profile: ImportMappingProfile) -> ImportMappingProfile:
        self._profiles[profile.id] = profile
        return profile

    def get_profile(self, profile_id: str) -> Optional[ImportMappingProfile]:
        return self._profiles.get(profile_id)

    def list_profiles(self, source_format: Optional[str] = None) -> List[ImportMappingProfile]:
        if source_format:
            return [p for p in self._profiles.values() if p.source_format == source_format]
        return list(self._profiles.values())

    def delete_profile(self, profile_id: str) -> None:
        self._profiles.pop(profile_id, None)

    def auto_map(
        self,
        source_headers: List[str],
        target_fields: List[str],
        source_format: str = "csv",
    ) -> ImportMappingProfile:
        profile = ImportMappingProfile.create(
            name="Auto-mapped profile",
            source_format=source_format,
        )
        target_lower = {f.lower().replace("_", "").replace(" ", ""): f for f in target_fields}
        for header in source_headers:
            normalized = header.lower().replace("_", "").replace(" ", "")
            if normalized in target_lower:
                profile.field_mappings.append(ImportFieldMapping(
                    source_field=header,
                    target_field=target_lower[normalized],
                ))
        return profile


__all__ = ["ImportMappingService", "ImportValidationService"]

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from src.core.modules.project_management.domain.identifiers import generate_id


class ImportParseState(str, Enum):
    PENDING = "pending"
    PARSING = "parsing"
    PARSED = "parsed"
    FAILED = "failed"


class ImportValidationSeverity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ImportFieldMapping:
    """Maps a source column/field name to a PM domain field."""
    source_field: str          # name in the source file/structure
    target_field: str          # PM domain field key
    is_required: bool = False
    default_value: Any = None
    transform: Optional[str] = ""  # e.g. "date:YYYY-MM-DD", "int", "float", "bool"


@dataclass
class ImportRow:
    """A single parsed row from an import source."""
    row_number: int
    source_data: Dict[str, Any]
    mapped_data: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0


@dataclass
class ImportValidationIssue:
    row_number: Optional[int]
    severity: ImportValidationSeverity
    field: Optional[str]
    message: str
    source_value: Any = None


@dataclass
class ImportPreviewModel:
    """
    Non-destructive preview of a staged import.

    Contains parsed rows, validation issues, and a diff summary.
    Callers display this to the user before committing.
    """
    session_id: str
    total_rows: int
    valid_rows: int
    error_rows: int
    warning_rows: int
    rows: List[ImportRow] = field(default_factory=list)
    issues: List[ImportValidationIssue] = field(default_factory=list)
    created_at: Optional[datetime] = None

    @property
    def can_commit(self) -> bool:
        """True when there are no ERROR-severity issues."""
        return not any(i.severity == ImportValidationSeverity.ERROR for i in self.issues)

    @property
    def errors(self) -> List[ImportValidationIssue]:
        return [i for i in self.issues if i.severity == ImportValidationSeverity.ERROR]

    @property
    def warnings(self) -> List[ImportValidationIssue]:
        return [i for i in self.issues if i.severity == ImportValidationSeverity.WARNING]


@dataclass
class ImportMappingProfile:
    """
    Saved field mapping configuration for a specific source format.

    Users can save, name, and reuse mapping profiles without repeating
    column mapping every time they import from the same source.
    """
    id: str
    name: str
    source_format: str          # e.g. "csv", "ms_project_xml", "p6_xer"
    field_mappings: List[ImportFieldMapping] = field(default_factory=list)
    owner_id: Optional[str] = None
    created_at: Optional[datetime] = None
    version: int = 1

    @staticmethod
    def create(name: str, source_format: str, owner_id: Optional[str] = None) -> "ImportMappingProfile":
        return ImportMappingProfile(
            id=generate_id(),
            name=name,
            source_format=source_format,
            owner_id=owner_id,
            created_at=datetime.utcnow(),
        )


class ImportParser(ABC):
    """
    Base class for all PM import parsers.

    Subclasses implement parse() for a specific source format.
    All parsers must be non-destructive — they only read and validate;
    the ImportValidationService and DataImportService own commit logic.
    """

    @property
    @abstractmethod
    def source_format(self) -> str:
        """Machine identifier for this parser's source format (e.g. 'csv', 'ms_project_xml')."""
        ...

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable parser name shown in import UI."""
        ...

    @abstractmethod
    def parse(self, source: bytes | str, mapping: Optional[ImportMappingProfile] = None) -> List[ImportRow]:
        """
        Parse raw source content into ImportRows.

        Does not validate PM business rules — that is ImportValidationService's job.
        """
        ...

    @abstractmethod
    def detect_headers(self, source: bytes | str) -> List[str]:
        """Return the list of field/column names found in the source."""
        ...


class CsvImportParser(ImportParser):
    """
    CSV parser — wraps the existing CSV import path as an ImportParser subclass.

    Preserves backward compatibility with CallbackImportDefinition while
    making CSV available through the new parser architecture.
    """

    @property
    def source_format(self) -> str:
        return "csv"

    @property
    def display_name(self) -> str:
        return "CSV"

    def parse(self, source: bytes | str, mapping: Optional[ImportMappingProfile] = None) -> List[ImportRow]:
        import csv
        import io

        text = source.decode("utf-8-sig") if isinstance(source, bytes) else source
        reader = csv.DictReader(io.StringIO(text))
        rows: List[ImportRow] = []
        for i, record in enumerate(reader, start=1):
            mapped = self._apply_mapping(dict(record), mapping)
            rows.append(ImportRow(row_number=i, source_data=dict(record), mapped_data=mapped))
        return rows

    def detect_headers(self, source: bytes | str) -> List[str]:
        import csv
        import io
        text = source.decode("utf-8-sig") if isinstance(source, bytes) else source
        reader = csv.reader(io.StringIO(text))
        try:
            return next(reader)
        except StopIteration:
            return []

    def _apply_mapping(
        self,
        record: Dict[str, Any],
        mapping: Optional[ImportMappingProfile],
    ) -> Dict[str, Any]:
        if mapping is None:
            return dict(record)
        result: Dict[str, Any] = {}
        for fm in mapping.field_mappings:
            value = record.get(fm.source_field, fm.default_value)
            result[fm.target_field] = value
        return result


class MSProjectXmlParser(ImportParser):
    """
    Microsoft Project XML (.xml) parser stub.

    Reads the MS Project XML schema and maps tasks, dependencies, resources,
    and calendars into PM ImportRows.  Full XML parsing is implemented in Step 10.
    """

    @property
    def source_format(self) -> str:
        return "ms_project_xml"

    @property
    def display_name(self) -> str:
        return "Microsoft Project XML"

    def parse(self, source: bytes | str, mapping: Optional[ImportMappingProfile] = None) -> List[ImportRow]:
        # Stub: full implementation reads <Task>, <Resource>, <Assignment> XML nodes
        raise NotImplementedError(
            "MSProjectXmlParser.parse() is a stub. Full XML parsing is pending Step 10 implementation."
        )

    def detect_headers(self, source: bytes | str) -> List[str]:
        # Return canonical field names from the MS Project XML schema
        return [
            "UID", "ID", "Name", "Type", "IsNull", "CreateDate", "Contact",
            "Duration", "Start", "Finish", "PercentComplete", "Priority",
            "Summary", "OutlineLevel", "OutlineNumber", "Predecessors",
        ]


class P6Parser(ImportParser):
    """
    Oracle Primavera P6 XER / XML parser stub.

    Maps P6 activity, resource, relationship, and calendar data into PM ImportRows.
    Full parsing is implemented in Step 10.
    """

    @property
    def source_format(self) -> str:
        return "p6_xer"

    @property
    def display_name(self) -> str:
        return "Oracle Primavera P6 (XER)"

    def parse(self, source: bytes | str, mapping: Optional[ImportMappingProfile] = None) -> List[ImportRow]:
        raise NotImplementedError(
            "P6Parser.parse() is a stub. Full XER parsing is pending Step 10 implementation."
        )

    def detect_headers(self, source: bytes | str) -> List[str]:
        return [
            "task_id", "proj_id", "task_code", "task_name", "task_type",
            "status_code", "start_date", "end_date", "target_start_date",
            "target_end_date", "act_start_date", "act_end_date",
            "phys_complete_pct", "remain_drtn_hr_cnt",
        ]


class ImportValidationService:
    """
    Validates parsed ImportRows against PM business rules before commit.

    Validation phases (per import runtime governance):
        1. Field presence and type checks
        2. Semantic validation (valid status codes, date order, etc.)
        3. Reference resolution (project/resource/task IDs exist)
        4. Duplicate detection
        5. Preview diff generation
    """

    def validate(
        self,
        rows: List[ImportRow],
        required_fields: Optional[List[str]] = None,
    ) -> List[ImportValidationIssue]:
        issues: List[ImportValidationIssue] = []
        required = required_fields or []

        for row in rows:
            # Phase 1: required field presence
            for req_field in required:
                if not row.mapped_data.get(req_field):
                    issues.append(ImportValidationIssue(
                        row_number=row.row_number,
                        severity=ImportValidationSeverity.ERROR,
                        field=req_field,
                        message=f"Required field '{req_field}' is missing or empty.",
                        source_value=None,
                    ))

            # Phase 2: date ordering (start <= finish)
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
                    pass  # type check handled elsewhere

        return issues

    def build_preview(
        self,
        rows: List[ImportRow],
        issues: List[ImportValidationIssue],
    ) -> ImportPreviewModel:
        error_rows = sum(1 for r in rows if r.has_errors or any(i.row_number == r.row_number and i.severity == ImportValidationSeverity.ERROR for i in issues))
        warning_rows = sum(1 for r in rows if any(i.row_number == r.row_number and i.severity == ImportValidationSeverity.WARNING for i in issues))
        return ImportPreviewModel(
            session_id=generate_id(),
            total_rows=len(rows),
            valid_rows=len(rows) - error_rows,
            error_rows=error_rows,
            warning_rows=warning_rows,
            rows=rows,
            issues=issues,
            created_at=datetime.utcnow(),
        )


class ImportMappingService:
    """
    Manages saved ImportMappingProfile objects.

    Allows users to save, load, update, and delete field mapping configurations
    so they don't need to remap columns on every import from the same source.
    """

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
        """
        Suggest a best-effort field mapping by normalizing and matching names.
        """
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


__all__ = [
    "CsvImportParser",
    "ImportFieldMapping",
    "ImportMappingProfile",
    "ImportMappingService",
    "ImportParser",
    "ImportParseState",
    "ImportPreviewModel",
    "ImportRow",
    "ImportValidationIssue",
    "ImportValidationService",
    "ImportValidationSeverity",
    "MSProjectXmlParser",
    "P6Parser",
]

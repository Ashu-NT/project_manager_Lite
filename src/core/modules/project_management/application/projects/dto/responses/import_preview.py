"""Transport-neutral parsed import and preview results."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

class ImportValidationSeverity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"

@dataclass
class ImportRow:
    """A single parsed row from an import source."""
    row_number: int
    source_data: dict[str, Any]
    mapped_data: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0

@dataclass
class ImportValidationIssue:
    row_number: int | None
    severity: ImportValidationSeverity
    field: str | None
    message: str
    source_value: Any = None

@dataclass
class ImportPreviewModel:
    """Non-destructive preview of a staged import."""
    session_id: str
    total_rows: int
    valid_rows: int
    error_rows: int
    warning_rows: int
    rows: list[ImportRow] = field(default_factory=list)
    issues: list[ImportValidationIssue] = field(default_factory=list)
    created_at: datetime | None = None

    @property
    def can_commit(self) -> bool:
        return not any(i.severity == ImportValidationSeverity.ERROR for i in self.issues)

    @property
    def errors(self) -> list[ImportValidationIssue]:
        return [i for i in self.issues if i.severity == ImportValidationSeverity.ERROR]

    @property
    def warnings(self) -> list[ImportValidationIssue]:
        return [i for i in self.issues if i.severity == ImportValidationSeverity.WARNING]

@dataclass(frozen=True, slots=True)
class ProjectImportStagingResult:
    staged_count: int

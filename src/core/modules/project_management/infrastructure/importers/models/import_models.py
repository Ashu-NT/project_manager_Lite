"""Shared import domain models — parsers, rows, validation, mapping profiles."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

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
    source_field: str
    target_field: str
    is_required: bool = False
    default_value: Any = None
    transform: str | None = ""

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

@dataclass
class ImportMappingProfile:
    """Saved field mapping configuration for a specific source format."""
    id: str
    name: str
    source_format: str
    field_mappings: list[ImportFieldMapping] = field(default_factory=list)
    owner_id: str | None = None
    created_at: datetime | None = None
    version: int = 1

    @staticmethod
    def create(name: str, source_format: str, owner_id: str | None = None) -> "ImportMappingProfile":
        return ImportMappingProfile(
            id=generate_id(),
            name=name,
            source_format=source_format,
            owner_id=owner_id,
            created_at=datetime.now(timezone.utc),
        )

class ImportParser(ABC):
    """Base class for all PM import parsers. Parsers are non-destructive."""

    @property
    @abstractmethod
    def source_format(self) -> str: ...

    @property
    @abstractmethod
    def display_name(self) -> str: ...

    @abstractmethod
    def parse(self, source: bytes | str, mapping: ImportMappingProfile | None = None) -> list[ImportRow]: ...

    @abstractmethod
    def detect_headers(self, source: bytes | str) -> list[str]: ...

__all__ = [
    "ImportFieldMapping",
    "ImportMappingProfile",
    "ImportParser",
    "ImportParseState",
    "ImportPreviewModel",
    "ImportRow",
    "ImportValidationIssue",
    "ImportValidationSeverity",
]

"""Shared import domain models — parsers, rows, validation, mapping profiles."""

from __future__ import annotations

from src.core.modules.project_management.application.projects.dto.responses.import_preview import ImportRow

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from src.core.modules.project_management.domain.identifiers import generate_id


class ImportParseState(str, Enum):
    PENDING = "pending"
    PARSING = "parsing"
    PARSED = "parsed"
    FAILED = "failed"



@dataclass
class ImportFieldMapping:
    """Maps a source column/field name to a PM domain field."""
    source_field: str
    target_field: str
    is_required: bool = False
    default_value: Any = None
    transform: str | None = ""







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
    def create(name: str, source_format: str, owner_id: str | None = None) -> ImportMappingProfile:
        return ImportMappingProfile(
            id=generate_id(),
            name=name,
            source_format=source_format,
            owner_id=owner_id,
            created_at=datetime.now(UTC),
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

__all__ = ['ImportFieldMapping', 'ImportMappingProfile', 'ImportParseState', 'ImportParser']

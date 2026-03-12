from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ImportSummary:
    entity_type: str
    created_count: int = 0
    updated_count: int = 0
    error_rows: list[str] = field(default_factory=list)

    @property
    def error_count(self) -> int:
        return len(self.error_rows)


@dataclass(frozen=True)
class ImportFieldSpec:
    key: str
    label: str
    required: bool = False


@dataclass
class ImportPreviewRow:
    line_no: int
    status: str
    action: str
    message: str
    row: dict[str, str] = field(default_factory=dict)


@dataclass
class ImportPreview:
    entity_type: str
    available_columns: list[str]
    mapped_columns: dict[str, str | None]
    rows: list[ImportPreviewRow] = field(default_factory=list)
    created_count: int = 0
    updated_count: int = 0

    @property
    def error_count(self) -> int:
        return sum(1 for row in self.rows if row.status == "ERROR")

    @property
    def ready_count(self) -> int:
        return sum(1 for row in self.rows if row.status == "READY")


__all__ = [
    "ImportFieldSpec",
    "ImportPreview",
    "ImportPreviewRow",
    "ImportSummary",
]

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass(frozen=True)
class RowError:
    line_no: int
    field_key: str | None
    code: str
    message: str
    severity: Literal["error", "warning"] = "error"

    def to_legacy_message(self) -> str:
        prefix = f"line {self.line_no}"
        if self.field_key:
            prefix = f"{prefix} [{self.field_key}]"
        return f"{prefix}: {self.message}"


@dataclass(frozen=True)
class ImportSourceRow:
    line_no: int
    values: dict[str, str]


@dataclass(frozen=True)
class ImportFieldSpec:
    key: str
    label: str
    required: bool = False


@dataclass
class ImportSummary:
    entity_type: str
    created_count: int = 0
    updated_count: int = 0
    error_rows: list[str] = field(default_factory=list)
    row_errors: list[RowError] = field(default_factory=list)

    def add_row_error(
        self,
        *,
        line_no: int,
        message: str,
        field_key: str | None = None,
        code: str = "ROW_ERROR",
        severity: Literal["error", "warning"] = "error",
    ) -> RowError:
        row_error = RowError(
            line_no=line_no,
            field_key=field_key,
            code=code,
            message=message,
            severity=severity,
        )
        self.row_errors.append(row_error)
        self.error_rows.append(row_error.to_legacy_message())
        return row_error

    @property
    def error_count(self) -> int:
        return len(self.error_rows)


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
    "ImportSourceRow",
    "ImportSummary",
    "RowError",
]

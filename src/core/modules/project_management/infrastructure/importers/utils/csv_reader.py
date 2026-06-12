"""CSV file loading and column mapping utilities."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from src.core.platform.importing import ImportFieldSpec


def load_csv_source(file_path: str | Path) -> tuple[list[str], list[tuple[int, dict[str, str]]]]:
    """Read a CSV file and return (columns, [(line_no, row_dict), ...])."""
    path = Path(file_path)
    rows: list[tuple[int, dict[str, str]]] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        columns = [
            str(field or "").strip().lower()
            for field in (reader.fieldnames or [])
            if str(field or "").strip()
        ]
        for idx, raw in enumerate(reader, start=2):
            normalized = {
                str(key or "").strip().lower(): str(value or "").strip()
                for key, value in (raw or {}).items()
                if str(key or "").strip()
            }
            if any(normalized.values()):
                rows.append((idx, normalized))
    return columns, rows


def build_effective_mapping(
    schema: tuple[ImportFieldSpec, ...],
    available_columns: list[str],
    mapping: dict[str, str | None] | None,
) -> dict[str, str | None]:
    """Resolve which CSV column maps to each schema field."""
    normalized_input = {
        str(key or "").strip().lower(): (
            str(value or "").strip().lower() if value not in (None, "") else None
        )
        for key, value in (mapping or {}).items()
    }
    available = {column.lower() for column in available_columns}
    resolved: dict[str, str | None] = {}
    for field_spec in schema:
        selected = normalized_input.get(field_spec.key)
        if selected is None and field_spec.key in available:
            selected = field_spec.key
        resolved[field_spec.key] = selected if selected in available else None
    return resolved


def apply_mapping(
    raw_rows: list[tuple[int, dict[str, str]]],
    effective_mapping: dict[str, str | None],
) -> list[tuple[int, dict[str, str]]]:
    """Apply an effective column mapping to raw rows."""
    return [
        (
            line_no,
            {
                key: str(raw.get(source or "", "") or "").strip() if source else ""
                for key, source in effective_mapping.items()
            },
        )
        for line_no, raw in raw_rows
    ]


def prepare_rows(
    schema: tuple[ImportFieldSpec, ...],
    file_path: str | Path,
    column_mapping: dict[str, str | None] | None,
) -> tuple[list[str], list[tuple[int, dict[str, str]]], dict[str, str | None]]:
    """Load CSV, compute effective mapping, and return mapped rows."""
    columns, raw_rows = load_csv_source(file_path)
    effective = build_effective_mapping(schema, columns, column_mapping)
    rows = apply_mapping(raw_rows, effective)
    return columns, rows, effective


__all__ = [
    "apply_mapping",
    "build_effective_mapping",
    "load_csv_source",
    "prepare_rows",
]

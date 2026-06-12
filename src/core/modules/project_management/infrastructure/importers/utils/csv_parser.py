"""Generic CSV import parser."""

from __future__ import annotations

import csv
import io
from typing import Any

from src.core.modules.project_management.infrastructure.importers.models.import_models import (
    ImportMappingProfile,
    ImportParser,
    ImportRow,
)

class CsvImportParser(ImportParser):
    """
    CSV parser — wraps the CSV import path as an ImportParser subclass.

    Preserves compatibility with CallbackImportDefinition while making CSV
    available through the parser architecture.
    """

    @property
    def source_format(self) -> str:
        return "csv"

    @property
    def display_name(self) -> str:
        return "CSV"

    def parse(self, source: bytes | str, mapping: ImportMappingProfile | None = None) -> list[ImportRow]:
        text = source.decode("utf-8-sig") if isinstance(source, bytes) else source
        reader = csv.DictReader(io.StringIO(text))
        rows: list[ImportRow] = []
        for i, record in enumerate(reader, start=1):
            mapped = self._apply_mapping(dict(record), mapping)
            rows.append(ImportRow(row_number=i, source_data=dict(record), mapped_data=mapped))
        return rows

    def detect_headers(self, source: bytes | str) -> list[str]:
        text = source.decode("utf-8-sig") if isinstance(source, bytes) else source
        reader = csv.reader(io.StringIO(text))
        try:
            return next(reader)
        except StopIteration:
            return []

    def _apply_mapping(
        self,
        record: dict[str, Any],
        mapping: ImportMappingProfile | None,
    ) -> dict[str, Any]:
        if mapping is None:
            return dict(record)
        result: dict[str, Any] = {}
        for fm in mapping.field_mappings:
            result[fm.target_field] = record.get(fm.source_field, fm.default_value)
        return result

__all__ = ["CsvImportParser"]

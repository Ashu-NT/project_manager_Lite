from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from .models import ImportFieldSpec, ImportPreview, ImportSourceRow, ImportSummary


class ImportDefinition(Protocol):
    operation_key: str
    module_code: str
    permission_code: str

    def field_specs(self) -> Sequence[ImportFieldSpec]: ...

    def preview(self, rows: Sequence[ImportSourceRow]) -> ImportPreview: ...

    def execute(self, rows: Sequence[ImportSourceRow]) -> ImportSummary: ...


__all__ = ["ImportDefinition"]

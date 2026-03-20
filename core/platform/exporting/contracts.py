from __future__ import annotations

from pathlib import Path
from typing import Protocol

from .models import ExportArtifact, ExportArtifactDraft


class ExportDefinition(Protocol):
    operation_key: str
    module_code: str
    permission_code: str

    def export(self, request: object) -> ExportArtifact | ExportArtifactDraft | Path | str: ...


__all__ = ["ExportDefinition"]

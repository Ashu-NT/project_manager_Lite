from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class ExportColumnSpec:
    key: str
    label: str


@dataclass(frozen=True)
class TabularExportPayload:
    columns: tuple[ExportColumnSpec, ...]
    rows: tuple[Mapping[str, object], ...]


@dataclass(frozen=True)
class ExportArtifactDraft:
    file_path: Path
    file_name: str | None = None
    media_type: str | None = None


@dataclass(frozen=True)
class ExportArtifact:
    file_path: Path
    file_name: str
    media_type: str | None = None
    metadata: Mapping[str, object] = field(default_factory=dict)


__all__ = [
    "ExportArtifact",
    "ExportArtifactDraft",
    "ExportColumnSpec",
    "TabularExportPayload",
]

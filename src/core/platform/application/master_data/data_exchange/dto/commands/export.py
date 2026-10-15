from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class MasterDataExportRequest:
    output_path: Path
    active_only: bool | None = None

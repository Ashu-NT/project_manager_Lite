from __future__ import annotations

from contextlib import suppress
from pathlib import Path
from typing import Mapping

from .models import ExportArtifact, ExportArtifactDraft


def ensure_output_path(path: str | Path) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    return output_path


def finalize_artifact(
    result: ExportArtifact | ExportArtifactDraft | str | Path,
    *,
    file_name: str | None = None,
    media_type: str | None = None,
    metadata: Mapping[str, object] | None = None,
) -> ExportArtifact:
    if isinstance(result, ExportArtifact):
        return ExportArtifact(
            file_path=result.file_path,
            file_name=file_name or result.file_name,
            media_type=media_type or result.media_type,
            metadata=metadata or result.metadata,
        )

    if isinstance(result, ExportArtifactDraft):
        path = Path(result.file_path)
        return ExportArtifact(
            file_path=path,
            file_name=file_name or result.file_name or path.name,
            media_type=media_type or result.media_type,
            metadata=metadata or {},
        )

    path = Path(result)
    return ExportArtifact(
        file_path=path,
        file_name=file_name or path.name,
        media_type=media_type,
        metadata=metadata or {},
    )


def cleanup_temp_artifact(path: str | Path | None, *, temp_dir: str | Path | None = None) -> None:
    target_path = Path(path) if path else None
    if target_path is not None:
        with suppress(FileNotFoundError, PermissionError, OSError):
            target_path.unlink()

    parent = Path(temp_dir) if temp_dir is not None else (target_path.parent if target_path else None)
    if parent is None:
        return
    if parent.exists():
        with suppress(FileNotFoundError, PermissionError, OSError):
            if not any(parent.iterdir()):
                parent.rmdir()


__all__ = ["cleanup_temp_artifact", "ensure_output_path", "finalize_artifact"]

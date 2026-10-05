from __future__ import annotations

from pathlib import Path
from shutil import copy2
from uuid import uuid4

from src.infra.platform.path import user_data_dir


def store_task_comment_attachments(
    *,
    task_id: str,
    comment_id: str,
    attachments: list[str] | None,
) -> list[str]:
    sources: list[Path] = []
    for raw in attachments or []:
        token = str(raw or "").strip()
        if not token:
            raise ValueError("Attachment source path is required.")
        source = Path(token).expanduser().resolve(strict=True)
        if not source.is_file():
            raise ValueError("Attachment source must be a file.")
        sources.append(source)

    stored: list[str] = []
    base_dir = user_data_dir() / "collaboration" / "attachments" / task_id / comment_id
    try:
        for source in sources:
            target = base_dir / uuid4().hex / source.name
            target.parent.mkdir(parents=True, exist_ok=False)
            stored.append(str(target))
            copy2(source, target)
    except Exception:
        cleanup_task_comment_attachments(stored)
        raise
    return stored


def cleanup_task_comment_attachments(paths: list[str]) -> None:
    root = (user_data_dir() / "collaboration" / "attachments").resolve()
    for raw in paths:
        path = Path(raw).resolve()
        if not path.is_relative_to(root):
            raise ValueError("Attachment cleanup target is outside managed storage.")
        path.unlink(missing_ok=True)
        try:
            path.parent.rmdir()
        except OSError:
            pass


__all__ = ["cleanup_task_comment_attachments", "store_task_comment_attachments"]

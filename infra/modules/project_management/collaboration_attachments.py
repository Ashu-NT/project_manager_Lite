from __future__ import annotations

from pathlib import Path
from shutil import copy2

from src.infra.platform.path import user_data_dir


def store_task_comment_attachments(
    *,
    task_id: str,
    comment_id: str,
    attachments: list[str] | None,
) -> list[str]:
    stored: list[str] = []
    base_dir = user_data_dir() / "collaboration" / "attachments" / task_id / comment_id
    for raw in attachments or []:
        token = str(raw or "").strip()
        if not token:
            continue
        source = Path(token)
        if source.exists() and source.is_file():
            base_dir.mkdir(parents=True, exist_ok=True)
            target = base_dir / source.name
            copy2(source, target)
            stored.append(str(target))
        else:
            stored.append(str(source))
    return stored


__all__ = ["store_task_comment_attachments"]

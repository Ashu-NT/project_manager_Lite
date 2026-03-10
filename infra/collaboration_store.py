from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from infra.path import user_data_dir


_MENTION_RE = re.compile(r"@([A-Za-z0-9_.-]+)")


class TaskCollaborationStore:
    def __init__(self, storage_path: Path | None = None) -> None:
        base = storage_path or (user_data_dir() / "collaboration" / "task_comments.json")
        self._path = Path(base)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            self._write_payload({"comments": []})

    def list_comments(self, task_id: str) -> list[dict[str, Any]]:
        payload = self._read_payload()
        comments = payload.get("comments", [])
        if not isinstance(comments, list):
            return []
        rows = [c for c in comments if isinstance(c, dict) and c.get("task_id") == task_id]
        rows.sort(key=lambda row: str(row.get("created_at") or ""))
        return rows

    def add_comment(
        self,
        *,
        task_id: str,
        author: str,
        body: str,
        attachments: list[str] | None = None,
    ) -> dict[str, Any]:
        text = (body or "").strip()
        if not text:
            raise ValueError("Comment text is required.")
        mentions = sorted({m.lower() for m in _MENTION_RE.findall(text)})
        row = {
            "id": uuid4().hex,
            "task_id": task_id,
            "author": (author or "unknown").strip() or "unknown",
            "body": text,
            "mentions": mentions,
            "attachments": [str(a) for a in (attachments or []) if str(a).strip()],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "read_by": [],
        }
        payload = self._read_payload()
        comments = payload.setdefault("comments", [])
        if not isinstance(comments, list):
            comments = []
            payload["comments"] = comments
        comments.append(row)
        self._write_payload(payload)
        return row

    def unread_mentions_count(self, username: str) -> int:
        user = (username or "").strip().lower()
        if not user:
            return 0
        payload = self._read_payload()
        total = 0
        for row in payload.get("comments", []):
            if not isinstance(row, dict):
                continue
            mentions = [str(m).lower() for m in row.get("mentions", [])]
            if user not in mentions:
                continue
            read_by = [str(v).lower() for v in row.get("read_by", [])]
            if user in read_by:
                continue
            total += 1
        return total

    def mark_task_mentions_read(self, *, task_id: str, username: str) -> None:
        user = (username or "").strip().lower()
        if not user:
            return
        payload = self._read_payload()
        changed = False
        for row in payload.get("comments", []):
            if not isinstance(row, dict) or row.get("task_id") != task_id:
                continue
            mentions = [str(m).lower() for m in row.get("mentions", [])]
            if user not in mentions:
                continue
            read_by = [str(v).lower() for v in row.get("read_by", [])]
            if user in read_by:
                continue
            read_by.append(user)
            row["read_by"] = read_by
            changed = True
        if changed:
            self._write_payload(payload)

    def _read_payload(self) -> dict[str, Any]:
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
        except Exception:
            data = {"comments": []}
        return data if isinstance(data, dict) else {"comments": []}

    def _write_payload(self, payload: dict[str, Any]) -> None:
        self._path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


__all__ = ["TaskCollaborationStore"]


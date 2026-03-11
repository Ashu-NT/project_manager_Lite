from __future__ import annotations

import json
import re
from contextlib import contextmanager
from shutil import copy2
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

from sqlalchemy import select

from infra.db.base import SessionLocal
from infra.db.models import TaskCommentORM
from infra.path import user_data_dir


_MENTION_RE = re.compile(r"@([A-Za-z0-9_.-]+)")


class TaskCollaborationStore:
    def __init__(
        self,
        storage_path: Path | None = None,
        *,
        session_factory: Callable[[], Any] | None = None,
    ) -> None:
        self._path = Path(storage_path) if storage_path is not None else None
        self._session_factory = session_factory or SessionLocal
        self._close_sessions = session_factory is None
        if self._path is not None:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            if not self._path.exists():
                self._write_payload({"comments": []})

    def list_comments(self, task_id: str) -> list[dict[str, Any]]:
        if self._path is None:
            return self._list_comments_db(task_id)
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
        if self._path is None:
            return self._add_comment_db(
                task_id=task_id,
                author=author,
                body=body,
                attachments=attachments,
            )
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
        return self.unread_mentions_count_for_users([user])

    def unread_mentions_count_for_users(self, usernames: list[str]) -> int:
        aliases = {
            str(name).strip().lower()
            for name in (usernames or [])
            if str(name).strip()
        }
        if not aliases:
            return 0
        if self._path is None:
            return self._unread_mentions_count_for_users_db(aliases)
        payload = self._read_payload()
        total = 0
        for row in payload.get("comments", []):
            if not isinstance(row, dict):
                continue
            mentions = {str(m).lower() for m in row.get("mentions", [])}
            if mentions.isdisjoint(aliases):
                continue
            read_by = {str(v).lower() for v in row.get("read_by", [])}
            if not read_by.isdisjoint(aliases):
                continue
            total += 1
        return total

    def mark_task_mentions_read(self, *, task_id: str, username: str) -> None:
        user = (username or "").strip().lower()
        if not user:
            return
        if self._path is None:
            self._mark_task_mentions_read_db(task_id=task_id, username=user)
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
        if self._path is None:
            return {"comments": []}
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
        except Exception:
            data = {"comments": []}
        return data if isinstance(data, dict) else {"comments": []}

    def _write_payload(self, payload: dict[str, Any]) -> None:
        if self._path is None:
            return
        self._path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    def _list_comments_db(self, task_id: str) -> list[dict[str, Any]]:
        with self._session_scope() as session:
            stmt = (
                select(TaskCommentORM)
                .where(TaskCommentORM.task_id == task_id)
                .order_by(TaskCommentORM.created_at.asc())
            )
            rows = session.execute(stmt).scalars().all()
            return [self._comment_row_from_orm(row) for row in rows]

    def _add_comment_db(
        self,
        *,
        task_id: str,
        author: str,
        body: str,
        attachments: list[str] | None,
    ) -> dict[str, Any]:
        text = (body or "").strip()
        if not text:
            raise ValueError("Comment text is required.")
        comment_id = uuid4().hex
        mentions = sorted({m.lower() for m in _MENTION_RE.findall(text)})
        stored_attachments = self._store_db_attachments(task_id=task_id, comment_id=comment_id, attachments=attachments)
        row = TaskCommentORM(
            id=comment_id,
            task_id=task_id,
            author_user_id=None,
            author_username=(author or "unknown").strip() or "unknown",
            body=text,
            mentions_json=json.dumps(mentions),
            attachments_json=json.dumps(stored_attachments),
            read_by_json=json.dumps([]),
            created_at=datetime.now(timezone.utc),
        )
        with self._session_scope() as session:
            session.add(row)
            session.flush()
            result = self._comment_row_from_orm(row)
            session.commit()
        return result

    def _unread_mentions_count_for_users_db(self, aliases: set[str]) -> int:
        with self._session_scope() as session:
            rows = session.execute(select(TaskCommentORM)).scalars().all()
            total = 0
            for row in rows:
                mentions = set(self._decode_json_list(row.mentions_json))
                if mentions.isdisjoint(aliases):
                    continue
                read_by = set(self._decode_json_list(row.read_by_json))
                if not read_by.isdisjoint(aliases):
                    continue
                total += 1
            return total

    def _mark_task_mentions_read_db(self, *, task_id: str, username: str) -> None:
        with self._session_scope() as session:
            stmt = select(TaskCommentORM).where(TaskCommentORM.task_id == task_id)
            rows = session.execute(stmt).scalars().all()
            changed = False
            for row in rows:
                mentions = self._decode_json_list(row.mentions_json)
                if username not in mentions:
                    continue
                read_by = self._decode_json_list(row.read_by_json)
                if username in read_by:
                    continue
                read_by.append(username)
                row.read_by_json = json.dumps(sorted(set(read_by)))
                changed = True
            if changed:
                session.commit()

    def _store_db_attachments(
        self,
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

    @staticmethod
    def _decode_json_list(value: str | None) -> list[str]:
        try:
            data = json.loads(value or "[]")
        except Exception:
            return []
        if not isinstance(data, list):
            return []
        return [str(item).strip().lower() for item in data if str(item).strip()]

    def _comment_row_from_orm(self, row: TaskCommentORM) -> dict[str, Any]:
        created_at = row.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        return {
            "id": row.id,
            "task_id": row.task_id,
            "author": row.author_username or "unknown",
            "body": row.body,
            "mentions": self._decode_json_list(row.mentions_json),
            "attachments": self._decode_json_list_preserve_case(row.attachments_json),
            "created_at": created_at.astimezone(timezone.utc).isoformat(),
            "read_by": self._decode_json_list(row.read_by_json),
        }

    @staticmethod
    def _decode_json_list_preserve_case(value: str | None) -> list[str]:
        try:
            data = json.loads(value or "[]")
        except Exception:
            return []
        if not isinstance(data, list):
            return []
        return [str(item).strip() for item in data if str(item).strip()]

    @contextmanager
    def _session_scope(self):
        session = self._session_factory()
        try:
            yield session
        finally:
            if self._close_sessions and hasattr(session, "close"):
                session.close()


__all__ = ["TaskCollaborationStore"]

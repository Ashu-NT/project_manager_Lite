"""TaskComment core comment entity."""

from __future__ import annotations

from dataclasses import field
from datetime import datetime, timezone
from typing import Iterable

from pydantic import field_validator

from src.core.modules.project_management.domain.identifiers import generate_id
from src.core.platform.common.exceptions import ValidationError
from src.core.platform.common.pydantic import (
    normalize_optional_identifier,
    normalize_optional_text,
    normalize_required_text,
    validated_dataclass,
)


def _coerce_iterable(value: object) -> list[object]:
    if value in (None, ""):
        return []
    if isinstance(value, str):
        return [value]
    try:
        return list(value)
    except TypeError:
        return [value]


def _normalize_unique_values(value: object, *, lowercase: bool = False) -> list[str]:
    normalized: set[str] = set()
    for item in _coerce_iterable(value):
        text = normalize_optional_text(item)
        if not text:
            continue
        normalized.add(text.lower() if lowercase else text)
    return sorted(normalized)


def _normalize_attachment_values(value: object) -> list[str]:
    attachments: list[str] = []
    for item in _coerce_iterable(value):
        text = normalize_optional_text(item)
        if text:
            attachments.append(text)
    return attachments


def _normalize_reactions(value: object) -> dict[str, list[str]]:
    if not value:
        return {}
    if not isinstance(value, dict):
        return {}
    normalized: dict[str, list[str]] = {}
    for raw_emoji, raw_user_ids in value.items():
        emoji = normalize_optional_text(raw_emoji)
        if not emoji:
            continue
        user_ids = _normalize_unique_values(raw_user_ids)
        if user_ids:
            normalized[emoji] = user_ids
    return normalized


def _normalize_optional_datetime(value: object, *, code: str) -> datetime | None:
    if value is None:
        return None
    if not isinstance(value, datetime):
        raise ValidationError(
            "Comment timestamp must be a valid datetime.",
            code=code,
        )
    return value


def normalize_task_comment_body(value: object) -> str:
    return normalize_required_text(
        value,
        message="Comment text is required.",
        code="COLLABORATION_BODY_REQUIRED",
    )


@validated_dataclass
class TaskComment:
    id: str
    task_id: str
    author_user_id: str | None
    author_username: str | None
    body: str
    mentions: list[str] = field(default_factory=list)
    mentioned_user_ids: list[str] = field(default_factory=list)
    attachments: list[str] = field(default_factory=list)
    read_by: list[str] = field(default_factory=list)
    read_by_user_ids: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    parent_comment_id: str | None = None
    updated_at: datetime | None = None
    deleted_at: datetime | None = None
    reactions: dict[str, list[str]] = field(default_factory=dict)

    @field_validator("task_id", mode="before")
    @classmethod
    def _validate_task_id(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Task ID is required.",
            code="COLLABORATION_TASK_REQUIRED",
        )

    @field_validator("author_user_id", mode="before")
    @classmethod
    def _normalize_author_user_id(cls, value: object) -> str | None:
        return normalize_optional_identifier(value)

    @field_validator("author_username", mode="before")
    @classmethod
    def _normalize_author_username(cls, value: object) -> str | None:
        normalized = normalize_optional_text(value)
        return normalized or None

    @field_validator("body", mode="before")
    @classmethod
    def _validate_body(cls, value: object) -> str:
        return normalize_task_comment_body(value)

    @field_validator("mentions", mode="before")
    @classmethod
    def _normalize_mentions(cls, value: object) -> list[str]:
        return _normalize_unique_values(value, lowercase=True)

    @field_validator("mentioned_user_ids", mode="before")
    @classmethod
    def _normalize_mentioned_user_ids(cls, value: object) -> list[str]:
        return _normalize_unique_values(value)

    @field_validator("attachments", mode="before")
    @classmethod
    def _normalize_attachments(cls, value: object) -> list[str]:
        return _normalize_attachment_values(value)

    @field_validator("read_by", mode="before")
    @classmethod
    def _normalize_read_by(cls, value: object) -> list[str]:
        return _normalize_unique_values(value, lowercase=True)

    @field_validator("read_by_user_ids", mode="before")
    @classmethod
    def _normalize_read_by_user_ids(cls, value: object) -> list[str]:
        return _normalize_unique_values(value)

    @field_validator("created_at", mode="before")
    @classmethod
    def _validate_created_at(cls, value: object) -> datetime:
        if not isinstance(value, datetime):
            raise ValidationError(
                "Comment timestamp must be a valid datetime.",
                code="COLLABORATION_TIMESTAMP_INVALID",
            )
        return value

    @field_validator("parent_comment_id", mode="before")
    @classmethod
    def _normalize_parent_comment_id(cls, value: object) -> str | None:
        return normalize_optional_identifier(value)

    @field_validator("updated_at", mode="before")
    @classmethod
    def _validate_updated_at(cls, value: object) -> datetime | None:
        return _normalize_optional_datetime(value, code="COLLABORATION_TIMESTAMP_INVALID")

    @field_validator("deleted_at", mode="before")
    @classmethod
    def _validate_deleted_at(cls, value: object) -> datetime | None:
        return _normalize_optional_datetime(value, code="COLLABORATION_TIMESTAMP_INVALID")

    @field_validator("reactions", mode="before")
    @classmethod
    def _normalize_reactions_field(cls, value: object) -> dict[str, list[str]]:
        return _normalize_reactions(value)

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    @property
    def is_reply(self) -> bool:
        return bool(self.parent_comment_id)

    @staticmethod
    def create(
        *,
        task_id: str,
        author_user_id: str | None,
        author_username: str | None,
        body: str,
        mentions: Iterable[str] | None = None,
        mentioned_user_ids: Iterable[str] | None = None,
        attachments: Iterable[str] | None = None,
        read_by: Iterable[str] | None = None,
        read_by_user_ids: Iterable[str] | None = None,
        parent_comment_id: str | None = None,
    ) -> "TaskComment":
        return TaskComment(
            id=generate_id(),
            task_id=task_id,
            author_user_id=author_user_id,
            author_username=author_username,
            body=body,
            mentions=list(mentions or []),
            mentioned_user_ids=list(mentioned_user_ids or []),
            attachments=list(attachments or []),
            read_by=list(read_by or []),
            read_by_user_ids=list(read_by_user_ids or []),
            parent_comment_id=parent_comment_id,
        )


__all__ = ["TaskComment", "normalize_task_comment_body"]

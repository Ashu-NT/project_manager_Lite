"""Collaboration ORM rows."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.infra.persistence.orm.base import Base


class TaskCommentORM(Base):
    __tablename__ = "task_comments"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    task_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
    )
    author_user_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    author_username: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    mentions_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]", server_default="[]")
    mentioned_user_ids_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]", server_default="[]")
    attachments_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]", server_default="[]")
    read_by_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]", server_default="[]")
    read_by_user_ids_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]", server_default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


Index("idx_task_comments_task", TaskCommentORM.task_id)
Index("idx_task_comments_created", TaskCommentORM.created_at)


class TaskPresenceORM(Base):
    __tablename__ = "task_presence"
    __table_args__ = (
        UniqueConstraint("task_id", "username", name="ux_task_presence_task_username"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    task_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    username: Mapped[str] = mapped_column(String(128), nullable=False)
    display_name: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    activity: Mapped[str] = mapped_column(String(32), nullable=False, default="reviewing", server_default="reviewing")
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


Index("idx_task_presence_task", TaskPresenceORM.task_id)
Index("idx_task_presence_seen", TaskPresenceORM.last_seen_at)

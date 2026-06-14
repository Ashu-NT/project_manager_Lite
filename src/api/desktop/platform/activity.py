from __future__ import annotations

from src.api.desktop.platform._support import execute_desktop_operation
from src.api.desktop.platform.models import DesktopApiResult
from src.api.desktop.platform.models.activity import ActivityEntryDto
from src.core.platform.activity import ActivityService
from src.core.platform.activity.domain.activity_entry import ActivityEntry


class PlatformActivityDesktopApi:
    """Desktop-facing adapter for activity feed queries."""

    def __init__(self, *, activity_service: ActivityService) -> None:
        self._activity_service = activity_service

    def list_recent(
        self,
        *,
        limit: int = 200,
        entity_type: str | None = None,
        entity_id: str | None = None,
        module: str | None = None,
        workspace_id: str | None = None,
    ) -> DesktopApiResult[tuple[ActivityEntryDto, ...]]:
        return execute_desktop_operation(
            lambda: self._serialize_entries(
                self._activity_service.list_recent(
                    limit=limit,
                    entity_type=entity_type,
                    entity_id=entity_id,
                    module=module,
                    workspace_id=workspace_id,
                )
            )
        )

    def _serialize_entries(self, entries: list[ActivityEntry]) -> tuple[ActivityEntryDto, ...]:
        return tuple(self._serialize_entry(e) for e in entries)

    @staticmethod
    def _serialize_entry(entry: ActivityEntry) -> ActivityEntryDto:
        return ActivityEntryDto(
            id=entry.id,
            action=entry.action,
            entity_type=entry.entity_type,
            entity_id=entry.entity_id,
            actor_id=entry.actor_id,
            module=entry.module,
            timestamp=entry.timestamp,
            type=entry.type,
            human_message=entry.human_message,
            details=dict(entry.details or {}),
            icon=entry.icon,
            color=entry.color,
            visibility=entry.visibility,
        )


__all__ = ["PlatformActivityDesktopApi"]

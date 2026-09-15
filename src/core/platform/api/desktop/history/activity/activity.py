from __future__ import annotations

from src.core.platform.api.desktop.support._support import execute_desktop_operation
from src.core.platform.api.desktop.models.common import DesktopApiResult
from src.core.platform.api.desktop.history.activity.models.activity import ActivityEntryDto
from src.core.platform.application.history.activity import ActivityService
from src.core.platform.domain.history.activity.activity_entry import ActivityEntry


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
        parent_entity_id: str | None = None,
    ) -> DesktopApiResult[tuple[ActivityEntryDto, ...]]:
        return execute_desktop_operation(
            lambda: self._serialize_entries(
                self._activity_service.list_recent(
                    limit=limit,
                    entity_type=entity_type,
                    entity_id=entity_id,
                    module=module,
                    workspace_id=workspace_id,
                    parent_entity_id=parent_entity_id,
                )
            )
        )

    def list_for_organization_overview(self, organization_id: str, *, limit: int = 5) -> list[dict]:
        """Pre-formatted dicts ready for AppWidgets.ActivityFeed, scoped to
        one explicit organization (which may not be the caller's active
        one) -- used by Organization Detail's Overview "Recent Activity"
        preview and its full Activity section. Every stored entry here IS
        already curated business activity (Organization/Site/Department/
        Employee/Document CRUD/lifecycle events with a real human_message
        set at write time) -- no client-side guessing needed, unlike the
        raw compliance audit trail."""
        try:
            entries = self._activity_service.list_recent_for_organization_id(
                organization_id, limit=limit
            )
        except Exception:
            return []
        return [self._to_feed_item(entry) for entry in entries]

    @staticmethod
    def _to_feed_item(entry: ActivityEntry) -> dict:
        ts = entry.timestamp.strftime("%Y-%m-%d %H:%M UTC")
        return {
            "id": entry.id,
            "title": entry.human_message or entry.action,
            "statusLabel": "",
            "subtitle": "",
            "metaText": ts,
            "supportingText": "",
            "state": {"icon": entry.icon or ""},
        }

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

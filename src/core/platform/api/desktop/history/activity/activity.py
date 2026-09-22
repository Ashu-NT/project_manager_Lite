from __future__ import annotations

from datetime import datetime

from src.core.platform.api.desktop.support._support import execute_desktop_operation
from src.core.platform.api.desktop.models.common import DesktopApiResult
from src.core.platform.api.desktop.history.activity.models.activity import (
    ActivityEntryDto,
    ActivityEntryPageDto,
)
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

    def list_for_organization_overview(
        self, organization_id: str, *, limit: int = 5, entity_types=None
    ) -> tuple[ActivityEntryDto, ...]:
        """Entries scoped to one explicit organization (which may not be the
        caller's active one), used by Organization Detail's Overview "Recent
        Activity" preview and its full Activity section. Every stored entry
        here is already curated business activity (Organization/Site/
        Department/Employee/Document CRUD/lifecycle events with a real
        human_message set at write time). `entity_types`, when given,
        restricts to exactly those (e.g. Organization Detail's own five
        entity types, excluding other modules' deeply-nested activity that
        happens to share this organization_id)."""
        try:
            entries = self._activity_service.list_recent_for_organization_id(
                organization_id, limit=limit, entity_types=entity_types
            )
        except Exception:
            return ()
        return self._serialize_entries(entries)

    def list_for_entity_overview(
        self, entity_type: str, entity_id: str, organization_id: str, *, limit: int = 5
    ) -> tuple[ActivityEntryDto, ...]:
        """Entries scoped to one specific entity (e.g. one Site) within an
        explicit organization (which may not be the caller's active one),
        used by that entity's Overview "Recent Activity" preview -- the
        entity-scoped analog of list_for_organization_overview above."""
        try:
            entries = self._activity_service.list_recent_for_entity(
                entity_type, entity_id, organization_id, limit=limit
            )
        except Exception:
            return ()
        return self._serialize_entries(entries)

    def list_page_for_entity(
        self,
        entity_type: str,
        entity_id: str,
        organization_id: str,
        *,
        page: int = 1,
        page_size: int = 25,
        search: str = "",
        since: datetime | None = None,
    ) -> DesktopApiResult[ActivityEntryPageDto]:
        return execute_desktop_operation(
            lambda: self._serialize_page(
                self._activity_service.list_recent_page_for_entity(
                    entity_type,
                    entity_id,
                    organization_id,
                    page=page,
                    page_size=page_size,
                    search=search,
                    since=since,
                )
            )
        )

    def list_page_for_organization(
        self,
        organization_id: str,
        *,
        page: int = 1,
        page_size: int = 25,
        search: str = "",
        entity_type: str | None = None,
        entity_types=None,
        since: datetime | None = None,
    ) -> DesktopApiResult[ActivityEntryPageDto]:
        return execute_desktop_operation(
            lambda: self._serialize_page(
                self._activity_service.list_recent_page_for_organization(
                    organization_id,
                    page=page,
                    page_size=page_size,
                    search=search,
                    entity_type=entity_type,
                    entity_types=entity_types,
                    since=since,
                )
            )
        )

    def _serialize_page(self, page) -> ActivityEntryPageDto:
        return ActivityEntryPageDto(
            items=self._serialize_entries(list(page.items)),
            total=page.total,
            filtered_total=page.filtered_total,
            page=page.page,
            page_size=page.page_size,
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

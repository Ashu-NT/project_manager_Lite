from __future__ import annotations

from src.core.global_overview.application.global_overview_service import (
    GlobalOverviewService,
)
from src.core.global_overview.contract.action_center import (
    ActionCenterContribution,
    ActionCenterCursor,
)
from src.core.global_overview.contract.module_summary import (
    ModuleSummaryDto,
)
from src.core.global_overview.contract.overview import (
    AttentionSummaryDto,
    GlobalOverviewCapabilitiesDto,
    GlobalOverviewContextDto,
)
from src.core.platform.api.desktop.history.activity.models.activity import (
    ActivityEntryDto,
)
from src.core.platform.api.desktop.models.common import DesktopApiResult
from src.core.platform.api.desktop.support._support import execute_desktop_operation
from src.core.platform.contract.read.history.activity_actor_reader import (
    ActivityActorPresentation,
)
from src.core.platform.domain.history.activity.activity_entry import ActivityEntry


class GlobalOverviewDesktopApi:
    """Desktop-facing adapter for the Global Overview landing page.

    Each method is independently callable and returns its own DesktopApiResult
    -- one failing (e.g. an Activity dependency error) never prevents the
    others from being called or succeeding. Contains no domain, permission,
    or module-specific rules of its own; it only calls GlobalOverviewService
    and translates the result.
    """

    def __init__(self, *, global_overview_service: GlobalOverviewService) -> None:
        self._global_overview_service = global_overview_service

    def get_context(self) -> DesktopApiResult[GlobalOverviewContextDto]:
        return execute_desktop_operation(self._global_overview_service.get_context)

    def get_attention_summary(self) -> DesktopApiResult[AttentionSummaryDto]:
        return execute_desktop_operation(self._global_overview_service.get_attention_summary)

    def list_module_summaries(self) -> DesktopApiResult[tuple[ModuleSummaryDto, ...]]:
        return execute_desktop_operation(self._global_overview_service.list_module_summaries)

    def get_capabilities(self) -> DesktopApiResult[GlobalOverviewCapabilitiesDto]:
        return execute_desktop_operation(self._global_overview_service.get_capabilities)

    def list_action_center(
        self,
        *,
        limit: int = 50,
        after: ActionCenterCursor | None = None,
    ) -> DesktopApiResult[ActionCenterContribution]:
        return execute_desktop_operation(
            lambda: self._global_overview_service.list_action_center(limit=limit, after=after)
        )

    def list_recent_activity(
        self,
        *,
        limit: int = 50,
    ) -> DesktopApiResult[tuple[ActivityEntryDto, ...]]:
        return execute_desktop_operation(
            lambda: self._serialize_activity_entries(limit=limit)
        )

    def _serialize_activity_entries(self, *, limit: int) -> tuple[ActivityEntryDto, ...]:
        entries = self._global_overview_service.list_recent_activity(limit=limit)
        actors = self._global_overview_service.present_activity_actors(entries)
        return tuple(self._serialize_activity_entry(entry, actors) for entry in entries)

    @staticmethod
    def _serialize_activity_entry(
        entry: ActivityEntry, actors: dict[str, ActivityActorPresentation]
    ) -> ActivityEntryDto:
        actor = actors.get(entry.actor_id) if entry.actor_id else None
        return ActivityEntryDto(
            id=entry.id,
            action=entry.action,
            entity_type=entry.entity_type,
            entity_id=entry.entity_id,
            actor_id=entry.actor_id,
            actor_kind=actor.kind.value if actor else ("missing" if entry.actor_id else "system"),
            actor_display=actor.label if actor else ("Deleted user" if entry.actor_id else "System"),
            module=entry.module,
            timestamp=entry.timestamp,
            type=entry.type,
            human_message=entry.human_message,
            details=dict(entry.details or {}),
            icon=entry.icon,
            color=entry.color,
            visibility=entry.visibility,
        )


__all__ = ["GlobalOverviewDesktopApi"]

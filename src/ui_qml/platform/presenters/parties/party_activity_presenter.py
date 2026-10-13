"""Party Detail's Activity tab -- one Party's own business-activity history
(created/updated/activated/deactivated), built on the same canonical
ActivityItemViewModel/App.Widgets.ActivityFeed architecture Organization's,
Site's, Department's, and Employee's Activity tabs already use. Every entry
here is entity_type="party", entity_id=this party's id."""

from __future__ import annotations

from typing import Any

from src.core.platform.api.desktop.history.activity.activity import (
    PlatformActivityDesktopApi,
)
from src.core.platform.api.desktop.history.activity.models.activity import (
    ActivityEntryDto,
)
from src.ui_qml.platform.presenters.common.activity_presenter_support import (
    ACTIVITY_DATE_FILTER_OPTIONS,
    since_for_date_range,
    split_human_message,
)
from src.ui_qml.shared.models.activity_item import (
    ActivityItemViewModel,
    humanize_action,
    icon_key_for_entity_type,
    serialize_activity_items,
    tone_for_action,
)

# Party lifecycle is 2-state (Active/Inactive) -- only these two actions
# need an explicit tone override, matching the reasoning in
# department_activity_presenter.py/employee_activity_presenter.py.
_ACTIVITY_TONE_OVERRIDE: dict[str, str] = {
    "party.activate": "success",
    "party.deactivate": "warning",
}


class PlatformPartyActivityPresenter:
    def __init__(
        self,
        *,
        activity_api: PlatformActivityDesktopApi | None = None,
    ) -> None:
        self._activity_api = activity_api

    def build_recent_activity(
        self, party_id: str, organization_id: str, *, limit: int = 5
    ) -> list[dict[str, Any]]:
        if self._activity_api is None:
            return []
        entries = self._activity_api.list_for_entity_overview(
            "party", party_id, organization_id, limit=limit
        )
        return serialize_activity_items(
            self._to_item(entry) for entry in entries
        )

    def build_activity_page_for_party(
        self,
        party_id: str,
        organization_id: str,
        *,
        page: int = 1,
        page_size: int = 25,
        search: str = "",
        date_range: str = "",
    ) -> dict[str, Any]:
        if self._activity_api is None:
            return self._empty_result(
                page=page,
                page_size=page_size,
                message="Platform activity API is not connected in this QML preview.",
            )

        result = self._activity_api.list_page_for_entity(
            "party",
            party_id,
            organization_id,
            page=page,
            page_size=page_size,
            search=search.strip(),
            since=since_for_date_range(date_range),
        )
        if not result.ok or result.data is None:
            message = result.error.message if result.error is not None else "Unable to load activity."
            return self._empty_result(page=page, page_size=page_size, message=message)

        entry_page = result.data
        items = [self._to_item(entry) for entry in entry_page.items]
        return {
            "items": serialize_activity_items(items),
            "page": entry_page.page,
            "pageSize": entry_page.page_size,
            "totalCount": entry_page.total,
            "filteredTotal": entry_page.filtered_total,
            "emptyState": "No activity yet. Business activity for this party will appear here.",
            "noResultsState": "No activity matches your current filters.",
        }

    @staticmethod
    def _empty_result(*, page: int, page_size: int, message: str) -> dict[str, Any]:
        return {
            "items": [],
            "page": page,
            "pageSize": page_size,
            "totalCount": 0,
            "filteredTotal": 0,
            "emptyState": message,
            "noResultsState": message,
        }

    def _to_item(
        self, entry: ActivityEntryDto
    ) -> ActivityItemViewModel:
        title, remainder = split_human_message(entry.human_message or "")
        if not title or title == entry.action or "." in title:
            title = humanize_action(entry.action)

        actor_display = entry.actor_display

        tone = _ACTIVITY_TONE_OVERRIDE.get(entry.action) or tone_for_action(entry.action)

        return ActivityItemViewModel(
            id=entry.id,
            title=title,
            actor_display=actor_display,
            occurred_at=entry.timestamp,
            occurred_at_label=entry.timestamp.strftime("%d %b %Y, %H:%M UTC") if entry.timestamp else "",
            icon_key=entry.icon or icon_key_for_entity_type(entry.entity_type),
            tone=tone,
            subject_display=remainder,
        )


__all__ = ["ACTIVITY_DATE_FILTER_OPTIONS", "PlatformPartyActivityPresenter"]

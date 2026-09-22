"""Site Detail's Activity tab -- one Site's own business-activity history
(create/update/activate/deactivate/archive), built on the same canonical
ActivityItemViewModel/App.Widgets.ActivityFeed architecture Organization's
Activity tab already uses (see organization_activity_presenter.py). Every
entry here is entity_type="site", entity_id=this site's id -- there is no
cross-entity lookup to build, since a site's own activity is never about a
different entity the way Organization's five-entity-type feed is.

Calendar assignment and Department/Employee/Document site-linkage are NOT
included: those write paths do not yet populate a queryable site reference
(no related_entity_type/id set for them today), so surfacing them here
would mean fabricating history rather than reporting it. Add them once
those flows are wired to record it -- see the Site Activity investigation
report."""

from __future__ import annotations

from typing import Any

from src.core.platform.api.desktop.history.activity.activity import PlatformActivityDesktopApi
from src.core.platform.api.desktop.history.activity.models.activity import ActivityEntryDto
from src.core.platform.api.desktop.security.auth.user import PlatformUserDesktopApi
from src.ui_qml.platform.presenters.common.activity_presenter_support import (
    ACTIVITY_DATE_FILTER_OPTIONS,
    build_actor_lookup,
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

# Not yet covered by tone_for_action()'s generic verb-keyword classifier --
# "activat"/"archiv" have no unambiguous substring match there ("activat"
# would also match "deactivate"), so these three need an explicit mapping,
# same reasoning as organization_activity_presenter.py's own override dict.
_ACTIVITY_TONE_OVERRIDE: dict[str, str] = {
    "site.activate": "success",
    "site.deactivate": "warning",
    "site.archive": "warning",
}

class PlatformSiteActivityPresenter:
    def __init__(
        self,
        *,
        activity_api: PlatformActivityDesktopApi | None = None,
        user_api: PlatformUserDesktopApi | None = None,
    ) -> None:
        self._activity_api = activity_api
        self._user_api = user_api

    def build_recent_activity(
        self, site_id: str, organization_id: str, *, limit: int = 5
    ) -> list[dict[str, Any]]:
        if self._activity_api is None:
            return []
        entries = self._activity_api.list_for_entity_overview(
            "site", site_id, organization_id, limit=limit
        )
        actor_lookup = build_actor_lookup(self._user_api)
        return serialize_activity_items(
            self._to_item(entry, actor_lookup=actor_lookup) for entry in entries
        )

    def build_activity_page_for_site(
        self,
        site_id: str,
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
            "site",
            site_id,
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
        actor_lookup = build_actor_lookup(self._user_api)
        items = [self._to_item(entry, actor_lookup=actor_lookup) for entry in entry_page.items]
        return {
            "items": serialize_activity_items(items),
            "page": entry_page.page,
            "pageSize": entry_page.page_size,
            "totalCount": entry_page.total,
            "filteredTotal": entry_page.filtered_total,
            "emptyState": "No activity yet. Business activity for this site will appear here.",
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
        self, entry: ActivityEntryDto, *, actor_lookup: dict[str, str]
    ) -> ActivityItemViewModel:
        title, remainder = split_human_message(entry.human_message or "")
        if not title or title == entry.action or "." in title:
            title = humanize_action(entry.action)

        if not entry.actor_id:
            actor_display = "System"
        else:
            actor_display = actor_lookup.get(entry.actor_id) or "Deleted user"

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
            # No activation_state -- this IS the site being viewed, never a
            # different entity to navigate to.
        )


__all__ = ["PlatformSiteActivityPresenter", "ACTIVITY_DATE_FILTER_OPTIONS"]

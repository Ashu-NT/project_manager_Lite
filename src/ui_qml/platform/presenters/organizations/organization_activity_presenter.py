"""Organization Detail's full Activity tab -- a paginated, searchable,
filterable business-activity workspace for one organization (regardless of
which organization is currently active in the caller's session), built
strictly on top of the existing canonical `ActivityItemViewModel` shape and
`App.Widgets.ActivityFeed` renderer. This presenter owns every presentation
decision (title, description, actor, subject, tone, icon) -- it never
invents a second Activity architecture, and it never lets a raw action
code, entity id, or actor id reach the UI as a user-facing label.

Distinct from Organization Detail's Overview "Recent Activity" preview
(`PlatformOrganizationCatalogPresenter.build_recent_activity`), which stays
a small, bounded, unfiltered list."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from src.core.platform.api.desktop.history.activity.activity import PlatformActivityDesktopApi
from src.core.platform.api.desktop.history.activity.models.activity import ActivityEntryDto
from src.core.platform.api.desktop.master_data.department.department import PlatformDepartmentDesktopApi
from src.core.platform.api.desktop.master_data.documents.document import PlatformDocumentDesktopApi
from src.core.platform.api.desktop.master_data.employee.employee import PlatformEmployeeDesktopApi
from src.core.platform.api.desktop.master_data.site.site import PlatformSiteDesktopApi
from src.core.platform.api.desktop.security.auth.user import PlatformUserDesktopApi
from src.ui_qml.shared.models.activity_item import (
    ActivityItemViewModel,
    humanize_action,
    icon_key_for_entity_type,
    serialize_activity_items,
    tone_for_action,
)

# Lifecycle-specific tone overrides not yet covered by the shared, generic
# tone_for_action() verb classifier (site.create/update, department.create/
# update, employee.create, document.create/update already map correctly
# through that shared function's existing keyword lists). Kept local to
# this presenter rather than widening the shared classifier used by every
# other Activity/Audit consumer in the app.
_ACTIVITY_TONE_OVERRIDE: dict[str, str] = {
    "organization.activate": "success",
    "organization.deactivate": "warning",
    "organization.archive": "warning",
    "employee.activate": "success",
    "employee.deactivate": "warning",
    "document.link": "success",
    "document.link_existing": "success",
    "document.unlink": "warning",
    "document.unlink_existing": "warning",
}

# Entity types with a real nested Detail page reachable from Organization
# Detail -- only these rows are clickable. "organization" entries have no
# destination (we are already viewing that organization).
_ACTIVATABLE_ENTITY_TYPES = frozenset({"site", "department", "employee", "document"})

# Organization Detail's Activity tab is this organization's OWN business
# activity -- not a dump of every module event that happens to share its
# organization_id. Project Management writes its own activity for deeply
# nested records (tasks, baselines, timesheets, ...) tagged with the same
# organization_id as the project's own organization, but those are not
# "this organization's" direct records the way Site/Department/Employee/
# Document are (see the Activity report's §1 scope discussion) -- so the
# underlying query is restricted to exactly these five entity types, not
# just filtered after the fact. This also keeps the query itself bounded
# to the (indexed, comparatively small) organization/site/department/
# employee/document rows rather than scanning a tenant's entire PM
# activity history for every Organization Detail page view.
ORGANIZATION_ACTIVITY_ENTITY_TYPES: tuple[str, ...] = (
    "organization", "site", "department", "employee", "document",
)

ACTIVITY_TYPE_FILTER_OPTIONS: tuple[dict[str, str], ...] = (
    {"value": "", "label": "All"},
    {"value": "organization", "label": "Organization"},
    {"value": "site", "label": "Site"},
    {"value": "department", "label": "Department"},
    {"value": "employee", "label": "Employee"},
    {"value": "document", "label": "Document"},
)

ACTIVITY_DATE_FILTER_OPTIONS: tuple[dict[str, str], ...] = (
    {"value": "", "label": "All time"},
    {"value": "today", "label": "Today"},
    {"value": "7d", "label": "Last 7 days"},
    {"value": "30d", "label": "Last 30 days"},
)


def _since_for_date_range(date_range: str) -> datetime | None:
    now = datetime.now(timezone.utc)
    if date_range == "today":
        return now.replace(hour=0, minute=0, second=0, microsecond=0)
    if date_range == "7d":
        return now - timedelta(days=7)
    if date_range == "30d":
        return now - timedelta(days=30)
    return None


def _split_human_message(message: str) -> tuple[str, str]:
    """"Site created — Hamburg Office" -> ("Site created", "Hamburg Office").
    Every create/update/lifecycle human_message recorded for Organization/
    Site/Department/Employee/Document activity is written as "<verb
    phrase> — <subject>" (see site_commands.py/department_commands.py/
    employee_service.py/organization_service.py/document_commands.py).
    Falls back to the whole message as the title when the separator isn't
    present, rather than guessing at a split that isn't there."""
    if " — " in message:
        title, _, remainder = message.partition(" — ")
        return title.strip(), remainder.strip()
    return message.strip(), ""


def _split_document_link_remainder(remainder: str) -> tuple[str, str]:
    """"Report.pdf to site" -> ("Report.pdf", "Linked to site"); "Report.pdf
    from site" -> ("Report.pdf", "Unlinked from site") -- only
    document.link/document.unlink's remainder has this extra
    " to X"/" from X" clause naming the link target's entity type."""
    for marker, verb in ((" to ", "Linked to"), (" from ", "Unlinked from")):
        if marker in remainder:
            subject, _, target = remainder.partition(marker)
            target = target.strip()
            if target:
                return subject.strip(), f"{verb} {target}"
    return remainder, ""


def _paginate_all(api_call, organization_id: str, *, max_pages: int = 20):
    """Yields every DTO across an organization-scoped paginated API,
    page_size=100, capped at max_pages -- the same bounded, no-N+1 pattern
    already used by PlatformDepartmentCatalogPresenter's Site/Department
    name lookups."""
    page = 1
    while page <= max_pages:
        result = api_call(organization_id, page=page, page_size=100, active_only=None)
        if not result.ok or result.data is None:
            return
        for row in result.data.items:
            yield row
        if page * 100 >= result.data.total:
            return
        page += 1


class PlatformOrganizationActivityPresenter:
    def __init__(
        self,
        *,
        activity_api: PlatformActivityDesktopApi | None = None,
        site_api: PlatformSiteDesktopApi | None = None,
        department_api: PlatformDepartmentDesktopApi | None = None,
        employee_api: PlatformEmployeeDesktopApi | None = None,
        document_api: PlatformDocumentDesktopApi | None = None,
        user_api: PlatformUserDesktopApi | None = None,
    ) -> None:
        self._activity_api = activity_api
        self._site_api = site_api
        self._department_api = department_api
        self._employee_api = employee_api
        self._document_api = document_api
        self._user_api = user_api

    def build_activity_page_for_organization(
        self,
        organization_id: str,
        *,
        page: int = 1,
        page_size: int = 25,
        search: str = "",
        entity_type: str = "",
        date_range: str = "",
    ) -> dict[str, Any]:
        if self._activity_api is None:
            return self._empty_result(
                page=page,
                page_size=page_size,
                message="Platform activity API is not connected in this QML preview.",
            )

        # A specific type filter is already one of the five Organization-
        # relevant types (see ACTIVITY_TYPE_FILTER_OPTIONS) -- passing it
        # alone is sufficient. With no specific filter, restrict to all
        # five explicitly rather than leaving the query unrestricted (see
        # ORGANIZATION_ACTIVITY_ENTITY_TYPES's own docstring).
        result = self._activity_api.list_page_for_organization(
            organization_id,
            page=page,
            page_size=page_size,
            search=search.strip(),
            entity_type=entity_type or None,
            entity_types=None if entity_type else ORGANIZATION_ACTIVITY_ENTITY_TYPES,
            since=_since_for_date_range(date_range),
        )
        if not result.ok or result.data is None:
            message = result.error.message if result.error is not None else "Unable to load activity."
            return self._empty_result(page=page, page_size=page_size, message=message)

        entry_page = result.data
        actor_lookup, entity_lookups = self._build_lookups_for_organization(organization_id)
        items = [
            self._to_rich_activity_item(entry, actor_lookup=actor_lookup, entity_lookups=entity_lookups)
            for entry in entry_page.items
        ]
        return {
            "items": serialize_activity_items(items),
            "page": entry_page.page,
            "pageSize": entry_page.page_size,
            "totalCount": entry_page.total,
            "filteredTotal": entry_page.filtered_total,
            "emptyState": "No activity yet. Business activity related to this organization will appear here.",
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

    def _build_lookups_for_organization(
        self, organization_id: str
    ) -> tuple[dict[str, str], dict[str, dict[str, str]]]:
        entity_lookups: dict[str, dict[str, str]] = {
            "site": {}, "department": {}, "employee": {}, "document": {},
        }
        employee_dtos: list[Any] = []

        if self._site_api is not None:
            for row in _paginate_all(self._site_api.list_sites_page_for_organization, organization_id):
                entity_lookups["site"][row.id] = row.name
        if self._department_api is not None:
            for row in _paginate_all(self._department_api.list_departments_page_for_organization, organization_id):
                entity_lookups["department"][row.id] = row.name
        if self._employee_api is not None:
            for row in _paginate_all(self._employee_api.list_employees_page_for_organization, organization_id):
                entity_lookups["employee"][row.id] = row.full_name
                employee_dtos.append(row)
        if self._document_api is not None:
            for row in _paginate_all(self._document_api.list_documents_page_for_organization, organization_id):
                entity_lookups["document"][row.id] = row.title

        actor_lookup = self._build_actor_lookup(employee_dtos)
        return actor_lookup, entity_lookups

    def _build_actor_lookup(self, employee_dtos: list[Any]) -> dict[str, str]:
        """actor_id (a User id) -> human-readable name. Preference order:
        explicit User.display_name, then the linked Employee's full_name,
        then User.username, then User.email -- never falls back to a raw
        user id. A user/employee not present here resolves to "" and the
        caller decides the final "Deleted user"/"System" fallback."""
        fallback: dict[str, str] = {}
        display_name: dict[str, str] = {}
        if self._user_api is not None:
            result = self._user_api.list_users()
            if result.ok and result.data is not None:
                for user in result.data:
                    name = str(user.username or "").strip() or str(user.email or "").strip()
                    if name:
                        fallback[user.id] = name
                    explicit = str(user.display_name or "").strip()
                    if explicit:
                        display_name[user.id] = explicit

        employee_names: dict[str, str] = {}
        for employee in employee_dtos:
            user_id = getattr(employee, "user_id", None)
            full_name = str(getattr(employee, "full_name", "") or "").strip()
            if user_id and full_name:
                employee_names[str(user_id)] = full_name

        # Lowest to highest priority -- each .update() lets a higher-priority
        # source win only where it actually has a value.
        lookup: dict[str, str] = {}
        lookup.update(fallback)
        lookup.update(employee_names)
        lookup.update(display_name)
        return lookup

    def _to_rich_activity_item(
        self,
        entry: ActivityEntryDto,
        *,
        actor_lookup: dict[str, str],
        entity_lookups: dict[str, dict[str, str]],
    ) -> ActivityItemViewModel:
        title, remainder = _split_human_message(entry.human_message or "")
        # Safety net: if the human_message didn't follow the expected
        # "<verb phrase> — <subject>" convention (e.g. it was left as the
        # bare action code), never let a raw "entity.verb" code reach the
        # UI as a title -- humanize it instead.
        if not title or title == entry.action or "." in title:
            title = humanize_action(entry.action)
        description = ""
        if entry.entity_type == "document" and entry.action in (
            "document.link", "document.link_existing", "document.unlink", "document.unlink_existing",
        ):
            subject_raw, description = _split_document_link_remainder(remainder)
        else:
            subject_raw = remainder

        subject_display = entity_lookups.get(entry.entity_type, {}).get(entry.entity_id, "") or subject_raw

        if not entry.actor_id:
            actor_display = "System"
        else:
            actor_display = actor_lookup.get(entry.actor_id) or "Deleted user"

        tone = _ACTIVITY_TONE_OVERRIDE.get(entry.action) or tone_for_action(entry.action)
        icon_key = entry.icon or icon_key_for_entity_type(entry.entity_type)

        activation_state = (
            {"entityType": entry.entity_type, "entityId": entry.entity_id}
            if entry.entity_type in _ACTIVATABLE_ENTITY_TYPES
            else None
        )

        return ActivityItemViewModel(
            id=entry.id,
            title=title,
            description=description,
            actor_display=actor_display,
            occurred_at=entry.timestamp,
            occurred_at_label=entry.timestamp.strftime("%d %b %Y, %H:%M UTC") if entry.timestamp else "",
            icon_key=icon_key,
            tone=tone,
            subject_display=subject_display,
            activation_state=activation_state,
        )


__all__ = [
    "PlatformOrganizationActivityPresenter",
    "ACTIVITY_TYPE_FILTER_OPTIONS",
    "ACTIVITY_DATE_FILTER_OPTIONS",
]

from __future__ import annotations

from src.core.platform.api.desktop.history.activity.activity import PlatformActivityDesktopApi
from src.core.platform.api.desktop.master_data.department.department import PlatformDepartmentDesktopApi
from src.core.platform.api.desktop.master_data.employee.employee import PlatformEmployeeDesktopApi
from src.core.platform.api.desktop.master_data.site.site import PlatformSiteDesktopApi
from src.core.platform.api.desktop.models.common import DesktopApiResult
from src.core.platform.api.desktop.security.auth.user import PlatformUserDesktopApi
from src.ui_qml.modules.project_management.view_models.projects import (
    ProjectCatalogWorkspaceViewModel,
    ProjectRecordViewModel,
    ProjectSectionCollectionViewModel,
)

from .overview_builder import build_empty_overview

# Keyword classification kept local to this builder rather than imported from
# another module's presenter layer -- PM must not import Inventory/Procurement
# packages, and this is a small, self-contained rule, not a shared contract.
_SUCCESS_KEYWORDS = ("creat", "add", "open", "approv", "complet")
_DANGER_KEYWORDS = ("delet", "cancel", "reject", "close", "remov")
_WARNING_KEYWORDS = ("updat", "edit", "modif", "submit", "post", "transfer", "issue", "return", "adjust")

# Display labels for the diffed fields recorded by ProjectLifecycleMixin's
# `_diff_project_fields()` -- kept in the same order a user would scan them.
_CHANGE_FIELD_LABELS: dict[str, str] = {
    "name": "Name",
    "code": "Code",
    "status": "Status",
    "description": "Description",
    "start_date": "Start Date",
    "end_date": "Finish Date",
    "client_name": "Client",
    "client_contact": "Contact",
    "site_id": "Site",
    "department_id": "Department",
    "client_party_id": "Client (Party)",
    "manager_user_id": "Manager",
    # Project-resource fields (from ProjectResourceCommandMixin.update()/
    # set_active()) -- same "changes" diff shape, shown in the same feed.
    "hourly_rate": "Hourly Rate",
    "currency_code": "Currency",
    "planned_hours": "Planned Hours",
    "is_active": "Active",
}
_BOOLEAN_FIELDS: frozenset[str] = frozenset({"is_active"})
# Fields whose recorded from/to values are ids that should be resolved to a
# human label via the matching lookup before display, when the lookup has one.
_CHANGE_FIELD_LOOKUP: dict[str, str] = {
    "site_id": "site",
    "department_id": "department",
    "manager_user_id": "user",
}


def _status_label_for_action(action: str) -> str:
    normalized = (action or "").lower()
    if any(keyword in normalized for keyword in _SUCCESS_KEYWORDS):
        return "Success"
    if any(keyword in normalized for keyword in _DANGER_KEYWORDS):
        return "Danger"
    if any(keyword in normalized for keyword in _WARNING_KEYWORDS):
        return "Warning"
    return ""


def _build_id_lookup(list_result) -> dict[str, str]:
    if not list_result.ok or list_result.data is None:
        return {}
    return {str(row.id): str(getattr(row, "name", "") or "") for row in list_result.data}


def _build_user_lookup(list_result) -> dict[str, str]:
    if not list_result.ok or list_result.data is None:
        return {}
    return {
        str(row.id): str(row.display_name or row.username)
        for row in list_result.data
    }


def _build_actor_lookup(
    user_result,
    employee_result,
) -> dict[str, str]:
    """user_id -> display name, preferring the linked Employee's full name.

    Most users in this app are employees (`Employee.user_id` links back to
    the account), and an employee record's `full_name` is a real recorded
    name rather than a login-oriented username/display_name -- so an
    Employee match, when one exists, wins over the User account's own
    fields.
    """
    lookup = _build_user_lookup(user_result)
    if employee_result is not None and employee_result.ok and employee_result.data is not None:
        for employee in employee_result.data:
            user_id = getattr(employee, "user_id", None)
            full_name = str(getattr(employee, "full_name", "") or "")
            if user_id and full_name:
                lookup[str(user_id)] = full_name
    return lookup


def _resolve_change_value(field_name: str, raw_value: str | None, lookups: dict[str, dict[str, str]]) -> str:
    if raw_value is None:
        return "-"
    if field_name in _BOOLEAN_FIELDS:
        return "Active" if raw_value == "True" else "Inactive"
    lookup_key = _CHANGE_FIELD_LOOKUP.get(field_name)
    if lookup_key is not None:
        resolved = lookups.get(lookup_key, {}).get(raw_value)
        if resolved:
            return resolved
    if field_name == "status":
        return raw_value.replace("_", " ").title()
    return raw_value


def _format_changes_summary(changes: object, lookups: dict[str, dict[str, str]]) -> str:
    if not isinstance(changes, dict) or not changes:
        return ""
    parts: list[str] = []
    for field_name, label in _CHANGE_FIELD_LABELS.items():
        change = changes.get(field_name)
        if not isinstance(change, dict):
            continue
        from_text = _resolve_change_value(field_name, change.get("from"), lookups)
        to_text = _resolve_change_value(field_name, change.get("to"), lookups)
        parts.append(f"{label}: {from_text} → {to_text}")
    return "; ".join(parts)


def build_project_activity_state(
    activity_api: PlatformActivityDesktopApi | None,
    *,
    project_id: str,
    site_api: PlatformSiteDesktopApi | None = None,
    department_api: PlatformDepartmentDesktopApi | None = None,
    user_api: PlatformUserDesktopApi | None = None,
    employee_api: PlatformEmployeeDesktopApi | None = None,
) -> ProjectCatalogWorkspaceViewModel:
    normalized_project_id = (project_id or "").strip()
    items: tuple[ProjectRecordViewModel, ...] = ()
    if activity_api is not None and normalized_project_id:
        # Two calls, not one broad workspace_id query: Task activity also
        # records with workspace_id=<project_id>, and pulling that in here
        # would silently expand this feed far beyond "project + its
        # resources" -- out of scope for this section.
        project_result = activity_api.list_recent(
            entity_type="project",
            entity_id=normalized_project_id,
            limit=50,
        )
        resource_result = activity_api.list_recent(
            entity_type="project_resource",
            workspace_id=normalized_project_id,
            limit=50,
        )
        entries = tuple(project_result.data or ()) + tuple(resource_result.data or ())
        result = DesktopApiResult(ok=True, data=entries) if (project_result.ok or resource_result.ok) else project_result
        if result.ok and result.data is not None:
            entries_sorted = sorted(result.data, key=lambda e: e.timestamp, reverse=True)[:50]
            actor_lookup = _build_actor_lookup(
                user_api.list_users() if user_api is not None else DesktopApiResult(ok=False),
                employee_api.list_employees() if employee_api is not None else None,
            )
            lookups = {
                "site": _build_id_lookup(site_api.list_sites(active_only=None)) if site_api is not None else {},
                "department": (
                    _build_id_lookup(department_api.list_departments(active_only=None))
                    if department_api is not None
                    else {}
                ),
                "user": actor_lookup,
            }
            items = tuple(
                ProjectRecordViewModel(
                    id=entry.id,
                    title=actor_lookup.get(entry.actor_id or "", "") or "System",
                    status_label=_status_label_for_action(entry.action),
                    subtitle=entry.human_message or entry.action,
                    supporting_text=_format_changes_summary(entry.details.get("changes"), lookups),
                    meta_text=entry.timestamp.strftime("%d %b %Y %H:%M") if entry.timestamp else "",
                )
                for entry in entries_sorted
            )
    return ProjectCatalogWorkspaceViewModel(
        overview=build_empty_overview(),
        selected_project_id=normalized_project_id,
        project_activity=ProjectSectionCollectionViewModel(
            title="Activity",
            subtitle=f"{len(items)} recent event(s) for this project." if items else "Recent project activity.",
            empty_state="No activity has been recorded for this project yet.",
            items=items,
        ),
    )

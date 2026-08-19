from __future__ import annotations

from src.core.platform.api.desktop.history.activity.activity import PlatformActivityDesktopApi
from src.core.platform.api.desktop.master_data.department.department import PlatformDepartmentDesktopApi
from src.core.platform.api.desktop.master_data.employee.employee import PlatformEmployeeDesktopApi
from src.core.platform.api.desktop.master_data.site.site import PlatformSiteDesktopApi
from src.core.platform.api.desktop.models.common import DesktopApiResult
from src.core.platform.api.desktop.security.auth.user import PlatformUserDesktopApi
from src.ui_qml.modules.project_management.presenters.common.activity_log_builder import (
    build_activity_records,
    build_actor_lookup,
    build_id_lookup,
    fetch_entity_activity_entries,
)
from src.ui_qml.modules.project_management.view_models.projects import (
    ProjectCatalogWorkspaceViewModel,
    ProjectRecordViewModel,
    ProjectSectionCollectionViewModel,
)

from .overview_builder import build_empty_overview

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
        # A project resource records its own `project_resource` activity
        # with `parent_entity_id=<project_id>` -- scoped via that real
        # column, not the shared `workspace_id` (which Tasks also uses for
        # this same project, and would leak unrelated Task activity in).
        entries = fetch_entity_activity_entries(
            activity_api,
            entity_type="project",
            entity_id=normalized_project_id,
            child_specs=[("project_resource", normalized_project_id)],
            limit=50,
        )
        if entries:
            actor_lookup = build_actor_lookup(
                user_api.list_users() if user_api is not None else DesktopApiResult(ok=False),
                employee_api.list_employees() if employee_api is not None else None,
            )
            lookups = {
                "site": build_id_lookup(site_api.list_sites(active_only=None)) if site_api is not None else {},
                "department": (
                    build_id_lookup(department_api.list_departments(active_only=None))
                    if department_api is not None
                    else {}
                ),
            }
            items = build_activity_records(
                entries,
                record_factory=ProjectRecordViewModel,
                actor_lookup=actor_lookup,
                lookups=lookups,
                field_labels=_CHANGE_FIELD_LABELS,
                field_lookup=_CHANGE_FIELD_LOOKUP,
                boolean_fields=_BOOLEAN_FIELDS,
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

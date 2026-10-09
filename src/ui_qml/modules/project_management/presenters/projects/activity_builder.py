from __future__ import annotations

from src.ui_qml.modules.project_management.presenters.common.activity_log_builder import (
    build_activity_records,
)
from src.ui_qml.shared.models.activity_item import serialize_activity_items

# Display labels for the diffed fields recorded by ProjectUpdateMixin's
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
    "client_party_id": "party",
    "manager_user_id": "user",
}


def build_project_activity_page(
    page,
) -> dict[str, object]:
    items = build_activity_records(
        page.items,
        lookups=page.reference_labels,
        field_labels=_CHANGE_FIELD_LABELS,
        field_lookup=_CHANGE_FIELD_LOOKUP,
        boolean_fields=_BOOLEAN_FIELDS,
    )
    return {
        "items": serialize_activity_items(items),
        "total": page.filtered_total,
        "page": page.page,
        "pageSize": page.page_size,
        "sortKey": page.sort_key,
        "sortDirection": page.sort_direction,
    }


__all__ = ["build_project_activity_page"]

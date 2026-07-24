from __future__ import annotations

from src.core.modules.project_management.api.desktop import (
    ProjectManagementResourcesDesktopApi,
)
from src.ui_qml.modules.project_management.view_models.resources import (
    ResourceCatalogWorkspaceViewModel,
    ResourceEmployeeOptionViewModel,
    ResourceSelectorOptionViewModel,
)

from .availability_builder import build_availability_view_model
from .detail_builder import build_detail_view_model
from .filtering import (
    build_empty_state,
    matches_active,
    matches_category,
    matches_search,
    normalize_active_filter,
    normalize_category_filter,
)
from .overview_builder import build_overview
from .resource_mapper import to_resource_record_view_model
from .selection import resolve_selected_resource_id


def build_workspace_state(
    desktop_api: ProjectManagementResourcesDesktopApi,
    *,
    search_text: str = "",
    active_filter: str = "all",
    category_filter: str = "all",
    selected_resource_id: str | None = None,
    page: int = 1,
    page_size: int = 25,
) -> ResourceCatalogWorkspaceViewModel:
    all_resources = desktop_api.list_resources()
    worker_type_options = tuple(
        ResourceSelectorOptionViewModel(value=option.value, label=option.label)
        for option in desktop_api.list_worker_types()
    )
    category_options = (
        ResourceSelectorOptionViewModel(value="all", label="All categories"),
        *(
            ResourceSelectorOptionViewModel(value=option.value, label=option.label)
            for option in desktop_api.list_categories()
        ),
    )
    employee_options = tuple(
        ResourceEmployeeOptionViewModel(
            value=option.value,
            label=option.label,
            name=option.name,
            title=option.title,
            contact=option.contact,
            context=option.context,
            department=option.department,
            site=option.site,
            is_active=option.is_active,
        )
        for option in desktop_api.list_employees()
    )
    normalized_search = (search_text or "").strip()
    normalized_active_filter = normalize_active_filter(active_filter)
    normalized_category_filter = normalize_category_filter(category_filter, category_options)
    filtered_resources = tuple(
        resource
        for resource in all_resources
        if matches_active(resource, normalized_active_filter)
        and matches_category(resource, normalized_category_filter)
        and matches_search(resource, normalized_search)
    )
    _total_count = len(filtered_resources)
    _page = max(1, page)
    _page_size = max(1, page_size)
    _offset = (_page - 1) * _page_size
    paged_resources = filtered_resources[_offset: _offset + _page_size]
    resolved_selected_resource_id = resolve_selected_resource_id(
        selected_resource_id, filtered_resources
    )
    selected_resource = next(
        (resource for resource in filtered_resources if resource.id == resolved_selected_resource_id),
        None,
    )
    return ResourceCatalogWorkspaceViewModel(
        overview=build_overview(
            all_resources=all_resources,
            filtered_resources=filtered_resources,
        ),
        worker_type_options=worker_type_options,
        category_options=category_options,
        employee_options=employee_options,
        selected_active_filter=normalized_active_filter,
        selected_category_filter=normalized_category_filter,
        search_text=normalized_search,
        resources=tuple(
            to_resource_record_view_model(resource) for resource in paged_resources
        ),
        selected_resource_id=resolved_selected_resource_id,
        selected_resource_detail=build_detail_view_model(desktop_api, selected_resource),
        resource_availability=build_availability_view_model(desktop_api, resolved_selected_resource_id),
        empty_state=build_empty_state(
            all_resources=all_resources,
            filtered_resources=filtered_resources,
            search_text=normalized_search,
            active_filter=normalized_active_filter,
            category_filter=normalized_category_filter,
        ),
        total_count=_total_count,
        page=_page,
        page_size=_page_size,
    )

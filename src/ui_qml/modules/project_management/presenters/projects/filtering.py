from __future__ import annotations


def matches_search(project, search_text: str) -> bool:
    if not search_text:
        return True
    normalized_search = search_text.casefold()
    haystacks = (
        project.name or "",
        project.client_name or "",
        project.client_contact or "",
        project.description or "",
    )
    return any(normalized_search in value.casefold() for value in haystacks)


def matches_status(project, status_filter: str) -> bool:
    if status_filter == "all":
        return True
    return project.status == status_filter


def normalize_status_filter(status_filter: str, status_options) -> str:
    normalized_value = (status_filter or "all").strip().lower()
    available_values = {option.value.lower(): option.value for option in status_options}
    return available_values.get(normalized_value, "all")


def build_empty_state(
    *,
    all_projects,
    filtered_projects,
    search_text: str,
    status_filter: str,
) -> str:
    if filtered_projects:
        return ""
    if not all_projects:
        return "No projects are available yet. Create the first project to start planning."
    if search_text or status_filter != "all":
        return "No projects match the current filters."
    return "No projects are available yet."

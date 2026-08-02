"""Task CSV import — preview and execute functions."""

from __future__ import annotations

from src.core.modules.project_management.domain.enums import TaskStatus
from src.core.platform.importing import ImportPreview, ImportPreviewRow, ImportSummary
from src.core.modules.project_management.infrastructure.importers.utils.coercion import (
    optional_date,
    optional_float,
    optional_int,
    optional_task_status,
    required,
)
from src.core.modules.project_management.infrastructure.importers.utils.lookup import (
    build_project_lookup,
    resolve_project,
)


def preview_tasks(
    rows: list[tuple[int, dict[str, str]]],
    *,
    project_service,
    task_service,
) -> ImportPreview:
    preview = ImportPreview(entity_type="tasks", available_columns=[], mapped_columns={})
    projects = build_project_lookup(project_service)
    for line_no, row in rows:
        try:
            project = resolve_project(
                projects,
                project_id=row.get("project_id") or None,
                project_name=row.get("project_name") or None,
            )
            if project is None:
                raise ValueError("Project reference is required via project_id or project_name.")
            name = required(row, "name")
            tasks = task_service.list_tasks_for_project(project.id)
            task_id = row.get("id") or ""
            task = next((t for t in tasks if t.id == task_id), None) if task_id else None
            if task is None:
                task = next((t for t in tasks if t.name.strip().lower() == name.strip().lower()), None)
            optional_date(row.get("start_date"))
            optional_int(row.get("duration_days"))
            optional_int(row.get("priority"))
            optional_date(row.get("deadline"))
            optional_task_status(row.get("status"))
            optional_float(row.get("percent_complete"))
            optional_int(row.get("sort_order"))
            parent_wbs_code = str(row.get("parent_wbs_code") or "").strip().upper()
            if parent_wbs_code:
                available_wbs_codes = {
                    str(getattr(item, "wbs_code", "") or "").strip().upper()
                    for item in tasks
                }
                available_wbs_codes.update(
                    str(candidate.get("wbs_code") or "").strip().upper()
                    for _, candidate in rows
                    if str(candidate.get("project_id") or "").strip() in {"", project.id}
                )
                if parent_wbs_code not in available_wbs_codes:
                    raise ValueError(
                        f"Parent WBS code '{parent_wbs_code}' was not found in the project or import file."
                    )
            action = "UPDATE" if task is not None else "CREATE"
            preview.rows.append(
                ImportPreviewRow(
                    line_no=line_no,
                    status="READY",
                    action=action,
                    message=f"Ready to {action.lower()} task '{name}' in '{project.name}'.",
                    row=row,
                )
            )
            if action == "CREATE":
                preview.created_count += 1
            else:
                preview.updated_count += 1
        except Exception as exc:
            preview.rows.append(
                ImportPreviewRow(line_no=line_no, status="ERROR", action="ERROR", message=str(exc), row=row)
            )
    return preview


def import_tasks(
    rows: list[tuple[int, dict[str, str]]],
    *,
    project_service,
    task_service,
) -> ImportSummary:
    summary = ImportSummary(entity_type="tasks")
    projects = build_project_lookup(project_service)
    pending = list(rows)
    while pending:
        made_progress = False
        next_pending: list[tuple[int, dict[str, str]]] = []
        for line_no, row in pending:
            project = None
            parent_wbs_code = str(row.get("parent_wbs_code") or "").strip().upper()
            try:
                project = resolve_project(
                    projects,
                    project_id=row.get("project_id") or None,
                    project_name=row.get("project_name") or None,
                )
                if project is None:
                    raise ValueError("Project reference is required via project_id or project_name.")
                current_tasks = task_service.list_tasks_for_project(project.id)
                parent_task = next(
                    (
                        item
                        for item in current_tasks
                        if str(getattr(item, "wbs_code", "") or "").strip().upper()
                        == parent_wbs_code
                    ),
                    None,
                )
                if parent_wbs_code and parent_task is None:
                    next_pending.append((line_no, row))
                    continue
                _import_task_row(
                    row,
                    project=project,
                    parent_task=parent_task,
                    task_service=task_service,
                    summary=summary,
                )
                made_progress = True
            except Exception as exc:
                summary.add_row_error(line_no=line_no, message=str(exc))
                made_progress = True

        if not next_pending:
            break
        if not made_progress:
            for line_no, row in next_pending:
                parent_wbs_code = str(row.get("parent_wbs_code") or "").strip().upper()
                summary.add_row_error(
                    line_no=line_no,
                    message=(
                        f"Parent WBS code '{parent_wbs_code}' was not found or the imported hierarchy contains a cycle."
                    ),
                )
            break
        pending = next_pending
    return summary


def _import_task_row(
    row: dict[str, str],
    *,
    project,
    parent_task,
    task_service,
    summary: ImportSummary,
) -> None:
    name = required(row, "name")
    tasks = task_service.list_tasks_for_project(project.id)
    task = None
    task_id = row.get("id") or ""
    if task_id:
        task = next((item for item in tasks if item.id == task_id), None)
    if task is None:
        task = next(
            (item for item in tasks if item.name.strip().lower() == name.strip().lower()),
            None,
        )
    payload = {
        "name": name,
        "code": str(row.get("task_code") or "").strip(),
        "description": row.get("description", ""),
        "start_date": optional_date(row.get("start_date")),
        "duration_days": optional_int(row.get("duration_days")),
        "priority": optional_int(row.get("priority")) or 0,
        "deadline": optional_date(row.get("deadline")),
    }
    status = optional_task_status(row.get("status"))
    percent_complete = optional_float(row.get("percent_complete"))
    wbs_code = str(row.get("wbs_code") or "").strip()
    sort_order = optional_int(row.get("sort_order"))
    hierarchy_requested = bool(wbs_code or parent_task is not None or sort_order is not None)
    if task is None:
        created = task_service.create_task(
            project.id,
            status=status or TaskStatus.TODO,
            parent_task_id=parent_task.id if parent_task is not None else None,
            wbs_code=wbs_code,
            sort_order=sort_order,
            **payload,
        )
        if percent_complete is not None:
            task_service.update_progress(created.id, percent_complete=percent_complete)
        summary.created_count += 1
        return

    updated = task_service.update_task(
        task.id,
        expected_version=task.version,
        status=status,
        **payload,
    )
    target_parent_id = (
        parent_task.id
        if parent_task is not None
        else (None if hierarchy_requested else task.parent_task_id)
    )
    if (
        target_parent_id != task.parent_task_id
        or (wbs_code and wbs_code.upper() != task.wbs_code)
        or (sort_order is not None and sort_order != task.sort_order)
    ):
        updated = task_service.move_task(
            updated.id,
            parent_task_id=target_parent_id,
            wbs_code=wbs_code or None,
            sort_order=sort_order,
            expected_version=updated.version,
        )
    if percent_complete is not None:
        task_service.update_progress(
            updated.id,
            percent_complete=percent_complete,
            expected_version=updated.version,
        )
    summary.updated_count += 1

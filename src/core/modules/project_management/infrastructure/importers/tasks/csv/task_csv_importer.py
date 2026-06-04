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
            task = None
            task_id = row.get("id") or ""
            if task_id:
                task = next((t for t in tasks if t.id == task_id), None)
            if task is None:
                task = next((t for t in tasks if t.name.strip().lower() == name.strip().lower()), None)
            payload = {
                "name": name,
                "description": row.get("description", ""),
                "start_date": optional_date(row.get("start_date")),
                "duration_days": optional_int(row.get("duration_days")),
                "priority": optional_int(row.get("priority")) or 0,
                "deadline": optional_date(row.get("deadline")),
            }
            status = optional_task_status(row.get("status"))
            percent_complete = optional_float(row.get("percent_complete"))
            if task is None:
                created = task_service.create_task(
                    project.id,
                    status=status or TaskStatus.TODO,
                    **payload,
                )
                if percent_complete is not None:
                    task_service.update_progress(created.id, percent_complete=percent_complete)
                summary.created_count += 1
            else:
                updated = task_service.update_task(
                    task.id,
                    expected_version=task.version,
                    status=status,
                    **payload,
                )
                if percent_complete is not None:
                    task_service.update_progress(
                        updated.id,
                        percent_complete=percent_complete,
                        expected_version=updated.version,
                    )
                summary.updated_count += 1
        except Exception as exc:
            summary.add_row_error(line_no=line_no, message=str(exc))
    return summary

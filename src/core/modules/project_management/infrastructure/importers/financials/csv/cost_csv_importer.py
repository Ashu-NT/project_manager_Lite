"""Financial cost CSV import — preview and execute functions."""

from __future__ import annotations

from src.core.modules.project_management.domain.enums import CostType
from src.core.platform.importing import ImportPreview, ImportPreviewRow, ImportSummary
from src.core.modules.project_management.infrastructure.importers.utils.coercion import (
    optional_cost_type,
    optional_date,
    optional_float,
    required,
)
from src.core.modules.project_management.infrastructure.importers.utils.lookup import (
    build_project_lookup,
    resolve_cost,
    resolve_project,
    resolve_task,
)


def preview_costs(
    rows: list[tuple[int, dict[str, str]]],
    *,
    project_service,
    task_service,
    cost_service,
) -> ImportPreview:
    preview = ImportPreview(entity_type="costs", available_columns=[], mapped_columns={})
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
            resolve_task(
                task_service,
                project_id=project.id,
                task_id=row.get("task_id") or None,
                task_name=row.get("task_name") or None,
            )
            existing = resolve_cost(cost_service, project_id=project.id, cost_id=row.get("id") or None)
            label = required(row, "description")
            optional_float(row.get("planned_amount"))
            optional_float(row.get("committed_amount"))
            optional_float(row.get("actual_amount"))
            optional_cost_type(row.get("cost_type"))
            optional_date(row.get("incurred_date"))
            action = "UPDATE" if existing is not None else "CREATE"
            preview.rows.append(
                ImportPreviewRow(
                    line_no=line_no,
                    status="READY",
                    action=action,
                    message=f"Ready to {action.lower()} cost '{label}' in '{project.name}'.",
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


def import_costs(
    rows: list[tuple[int, dict[str, str]]],
    *,
    project_service,
    task_service,
    cost_service,
) -> ImportSummary:
    summary = ImportSummary(entity_type="costs")
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
            task = resolve_task(
                task_service,
                project_id=project.id,
                task_id=row.get("task_id") or None,
                task_name=row.get("task_name") or None,
            )
            existing = resolve_cost(cost_service, project_id=project.id, cost_id=row.get("id") or None)
            payload = {
                "description": required(row, "description"),
                "planned_amount": optional_float(row.get("planned_amount")) or 0.0,
                "committed_amount": optional_float(row.get("committed_amount")) or 0.0,
                "actual_amount": optional_float(row.get("actual_amount")) or 0.0,
                "cost_type": optional_cost_type(row.get("cost_type")) or CostType.OVERHEAD,
                "currency_code": row.get("currency_code") or None,
                "incurred_date": optional_date(row.get("incurred_date")),
            }
            if existing is None:
                cost_service.add_cost_item(
                    project_id=project.id,
                    task_id=task.id if task is not None else None,
                    **payload,
                )
                summary.created_count += 1
            else:
                cost_service.update_cost_item(existing.id, expected_version=existing.version, **payload)
                summary.updated_count += 1
        except Exception as exc:
            summary.add_row_error(line_no=line_no, message=str(exc))
    return summary

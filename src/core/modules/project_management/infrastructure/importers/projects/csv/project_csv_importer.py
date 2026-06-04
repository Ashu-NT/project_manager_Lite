"""Project CSV import — preview and execute functions."""

from __future__ import annotations

from src.core.modules.project_management.domain.enums import ProjectStatus
from src.core.platform.importing import ImportPreview, ImportPreviewRow, ImportSummary
from src.core.modules.project_management.infrastructure.importers.utils.coercion import (
    optional_date,
    optional_float,
    optional_project_status,
    required,
)
from src.core.modules.project_management.infrastructure.importers.utils.lookup import (
    build_project_lookup,
    resolve_project,
)


def preview_projects(
    rows: list[tuple[int, dict[str, str]]],
    *,
    project_service,
) -> ImportPreview:
    preview = ImportPreview(entity_type="projects", available_columns=[], mapped_columns={})
    existing = build_project_lookup(project_service)
    for line_no, row in rows:
        try:
            name = required(row, "name")
            project = resolve_project(existing, project_id=row.get("id") or None, project_name=name)
            optional_float(row.get("planned_budget"))
            optional_date(row.get("start_date"))
            optional_date(row.get("end_date"))
            optional_project_status(row.get("status"))
            action = "UPDATE" if project is not None else "CREATE"
            preview.rows.append(
                ImportPreviewRow(
                    line_no=line_no,
                    status="READY",
                    action=action,
                    message=f"Ready to {action.lower()} project '{name}'.",
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


def import_projects(
    rows: list[tuple[int, dict[str, str]]],
    *,
    project_service,
) -> ImportSummary:
    summary = ImportSummary(entity_type="projects")
    existing = build_project_lookup(project_service)
    for line_no, row in rows:
        try:
            project_id = row.get("id") or None
            name = required(row, "name")
            project = resolve_project(existing, project_id=project_id, project_name=name)
            payload = {
                "name": name,
                "description": row.get("description", ""),
                "client_name": row.get("client_name") or None,
                "client_contact": row.get("client_contact") or None,
                "planned_budget": optional_float(row.get("planned_budget")),
                "currency": row.get("currency") or None,
                "start_date": optional_date(row.get("start_date")),
                "end_date": optional_date(row.get("end_date")),
            }
            status = optional_project_status(row.get("status"))
            if project is None:
                created = project_service.create_project(**payload)
                if status is not None and status != ProjectStatus.PLANNED:
                    project_service.set_status(created.id, status)
                summary.created_count += 1
            else:
                project_service.update_project(
                    project.id,
                    expected_version=project.version,
                    status=status,
                    **payload,
                )
                summary.updated_count += 1
            existing = build_project_lookup(project_service)
        except Exception as exc:
            summary.add_row_error(line_no=line_no, message=str(exc))
    return summary

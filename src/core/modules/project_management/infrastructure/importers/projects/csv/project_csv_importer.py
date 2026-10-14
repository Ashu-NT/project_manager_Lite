"""Project CSV import — preview and execute functions."""

from __future__ import annotations

from charset_normalizer.api import logger

from src.core.modules.project_management.application.projects.commands.create import (
    ProjectCreateHandler,
)
from src.core.modules.project_management.application.projects.commands.status import (
    ProjectStatusHandler,
)
from src.core.modules.project_management.application.projects.commands.update import (
    ProjectUpdateHandler,
)
from src.core.modules.project_management.application.projects.queries.project_query import (
    ProjectQueryHandler,
)
from src.core.modules.project_management.domain.enums import ProjectStatus
from src.core.modules.project_management.infrastructure.importers.utils.coercion import (
    optional_date,
    optional_project_status,
    required,
)
from src.core.modules.project_management.infrastructure.importers.utils.lookup import (
    build_project_lookup,
    resolve_project,
)
from src.core.platform.domain.data_operations.importing import (
    ImportPreview,
    ImportPreviewRow,
    ImportSummary,
)


def preview_projects(
    rows: list[tuple[int, dict[str, str]]],
    *,
    project_query: ProjectQueryHandler,
) -> ImportPreview:
    preview = ImportPreview(entity_type="projects", available_columns=[], mapped_columns={})
    existing = build_project_lookup(project_query)
    for line_no, row in rows:
        try:
            name = required(row, "name")
            project = resolve_project(existing, project_id=row.get("id") or None, project_name=name)
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
        except Exception as exc:  # noqa: BLE001
            logger.exception("Failed to preview project row at line %s: %s", line_no, exc)
            preview.rows.append(
                ImportPreviewRow(line_no=line_no, status="ERROR", action="ERROR", message=str(exc), row=row)
            )
    return preview


def import_projects(
    rows: list[tuple[int, dict[str, str]]],
    *,
    project_query: ProjectQueryHandler,
    project_create: ProjectCreateHandler,
    project_update: ProjectUpdateHandler,
    project_status: ProjectStatusHandler,
) -> ImportSummary:
    summary = ImportSummary(entity_type="projects")
    existing = build_project_lookup(project_query)
    for line_no, row in rows:
        try:
            project_id = row.get("id") or None
            name = required(row, "name")
            project = resolve_project(existing, project_id=project_id, project_name=name)
            description = row.get("description", "")
            client_name = row.get("client_name") or None
            client_contact = row.get("client_contact") or None
            start_date = optional_date(row.get("start_date"))
            end_date = optional_date(row.get("end_date"))
            status = optional_project_status(row.get("status"))
            if project is None:
                created = project_create.create_project(
                    name=name, description=description, client_name=client_name,
                    client_contact=client_contact, start_date=start_date, end_date=end_date,
                )
                if status is not None and status != ProjectStatus.PLANNED:
                    project_status.set_status(created.id, status)
                summary.created_count += 1
            else:
                project_update.update_project(
                    project.id,
                    expected_version=project.version,
                    status=status,
                    name=name, description=description, client_name=client_name,
                    client_contact=client_contact, start_date=start_date, end_date=end_date,
                )
                summary.updated_count += 1
            existing = build_project_lookup(project_query)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Failed to import project row at line %s: %s", line_no, exc)
            summary.add_row_error(line_no=line_no, message=str(exc))
    return summary

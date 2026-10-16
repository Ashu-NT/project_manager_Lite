"""Resource CSV import — preview and execute functions."""

from __future__ import annotations

import logging
from decimal import Decimal

from src.core.modules.project_management.application.resources.commands.resource_commands import (
    ResourceMasterCommandHandler,
)
from src.core.modules.project_management.application.resources.dto.commands.catalog import (
    ResourceCreateCommand,
    ResourceLifecycleCommand,
    ResourceUpdateCommand,
)
from src.core.modules.project_management.application.resources.queries.resource_queries import (
    ResourceQueryHandler,
)
from src.core.modules.project_management.domain.enums import CostType
from src.core.modules.project_management.infrastructure.importers.utils.coercion import (
    optional_bool,
    optional_cost_type,
    optional_decimal,
    optional_float,
    required,
)
from src.core.platform.domain.data_operations.importing import (
    ImportPreview,
    ImportPreviewRow,
    ImportSummary,
)

logger = logging.getLogger(__name__)


def preview_resources(
    rows: list[tuple[int, dict[str, str]]],
    *,
    resource_query: ResourceQueryHandler,
) -> ImportPreview:
    preview = ImportPreview(entity_type="resources", available_columns=[], mapped_columns={})
    existing = {r.id: r for r in resource_query.list_resources()}
    existing_by_name = {r.name.strip().lower(): r for r in resource_query.list_resources()}
    for line_no, row in rows:
        try:
            name = required(row, "name")
            resource = existing.get(row.get("id") or "") or existing_by_name.get(name.strip().lower())
            optional_decimal(row.get("hourly_rate"))
            optional_float(row.get("capacity_percent"))
            optional_bool(row.get("is_active"), default=True)
            optional_cost_type(row.get("cost_type"))
            action = "UPDATE" if resource is not None else "CREATE"
            preview.rows.append(
                ImportPreviewRow(
                    line_no=line_no,
                    status="READY",
                    action=action,
                    message=f"Ready to {action.lower()} resource '{name}'.",
                    row=row,
                )
            )
            if action == "CREATE":
                preview.created_count += 1
            else:
                preview.updated_count += 1
        except Exception as exc:
            logger.exception("Failed to preview resource row at line %s: %s", line_no, exc)  # noqa: TRY401
            preview.rows.append(
                ImportPreviewRow(line_no=line_no, status="ERROR", action="ERROR", message=str(exc), row=row)
            )
    return preview


def import_resources(
    rows: list[tuple[int, dict[str, str]]],
    *,
    resource_query: ResourceQueryHandler,
    resource_commands: ResourceMasterCommandHandler,
) -> ImportSummary:
    summary = ImportSummary(entity_type="resources")
    existing = {r.id: r for r in resource_query.list_resources()}
    existing_by_name = {r.name.strip().lower(): r for r in resource_query.list_resources()}
    for line_no, row in rows:
        try:
            resource = existing.get(row.get("id") or "") or existing_by_name.get(
                required(row, "name").strip().lower()
            )
            command = ResourceCreateCommand(
                name=required(row, "name"),
                code=row.get("code", ""),
                role=row.get("role", ""),
                hourly_rate=optional_decimal(row.get("hourly_rate")) or Decimal(0),
                cost_type=(optional_cost_type(row.get("cost_type")) or CostType.LABOR).value,
                currency_code=row.get("currency_code") or None,
                capacity_percent=optional_float(row.get("capacity_percent")) or 100.0,
                address=row.get("address", ""),
                contact=row.get("contact", ""),
                kind=resource.kind.value if resource is not None else "PERSON",
                worker_type=resource.worker_type.value if resource is not None else "EXTERNAL",
                employee_id=resource.employee_id if resource is not None else None,
                department_id=resource.department_id if resource is not None else None,
                site_id=resource.site_id if resource is not None else None,
            )
            requested_active = optional_bool(row.get("is_active"), default=True)
            if resource is None:
                resource = resource_commands.create_resource(command)
                summary.created_count += 1
            else:
                resource = resource_commands.update_resource(ResourceUpdateCommand(
                    resource_id=resource.id, expected_version=resource.version,
                    name=command.name, code=command.code, kind=command.kind,
                    role=command.role, hourly_rate=command.hourly_rate,
                    cost_type=command.cost_type, currency_code=command.currency_code,
                    capacity_percent=command.capacity_percent, address=command.address,
                    contact=command.contact, worker_type=command.worker_type,
                    employee_id=command.employee_id, department_id=command.department_id,
                    site_id=command.site_id,
                ))
                summary.updated_count += 1
            if resource.is_active != requested_active:
                operation = (
                    resource_commands.reactivate_resource
                    if requested_active
                    else resource_commands.deactivate_resource
                )
                resource = operation(ResourceLifecycleCommand(
                    resource_id=resource.id,
                    expected_version=resource.version,
                ))
            existing = {r.id: r for r in resource_query.list_resources()}
            existing_by_name = {r.name.strip().lower(): r for r in resource_query.list_resources()}
        except Exception as exc:
            logger.exception("Failed to import resource row at line %s: %s", line_no, exc)  # noqa: TRY401
            summary.add_row_error(line_no=line_no, message=str(exc))
    return summary

"""Resource CSV import — preview and execute functions."""

from __future__ import annotations

from decimal import Decimal

from src.core.modules.project_management.domain.enums import CostType
from src.core.modules.project_management.application.resources.resource_master_events import (
    ResourceMasterChangeType,
)
from src.core.modules.project_management.application.resources.resource_master_uow import (
    ResourceMasterUnitOfWork,
)
from src.core.platform.domain.data_operations.importing import ImportPreview, ImportPreviewRow, ImportSummary
from src.core.modules.project_management.infrastructure.importers.utils.coercion import (
    optional_bool,
    optional_cost_type,
    optional_decimal,
    optional_float,
    required,
)


def preview_resources(
    rows: list[tuple[int, dict[str, str]]],
    *,
    resource_service,
) -> ImportPreview:
    preview = ImportPreview(entity_type="resources", available_columns=[], mapped_columns={})
    existing = {r.id: r for r in resource_service.list_resources()}
    existing_by_name = {r.name.strip().lower(): r for r in resource_service.list_resources()}
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
            preview.rows.append(
                ImportPreviewRow(line_no=line_no, status="ERROR", action="ERROR", message=str(exc), row=row)
            )
    return preview


def import_resources(
    rows: list[tuple[int, dict[str, str]]],
    *,
    resource_service,
) -> ImportSummary:
    summary = ImportSummary(entity_type="resources")
    existing = {r.id: r for r in resource_service.list_resources()}
    existing_by_name = {r.name.strip().lower(): r for r in resource_service.list_resources()}
    uow = ResourceMasterUnitOfWork(
        resource_service._session,
        resource_service._tenant_context_service,
    )
    for line_no, row in rows:
        try:
            resource = existing.get(row.get("id") or "") or existing_by_name.get(
                required(row, "name").strip().lower()
            )
            payload = {
                "name": required(row, "name"),
                "code": row.get("code", ""),
                "role": row.get("role", ""),
                "hourly_rate": optional_decimal(row.get("hourly_rate")) or Decimal("0"),
                "cost_type": optional_cost_type(row.get("cost_type")) or CostType.LABOR,
                "currency_code": row.get("currency_code") or None,
                "capacity_percent": optional_float(row.get("capacity_percent")) or 100.0,
                "address": row.get("address", ""),
                "contact": row.get("contact", ""),
            }
            requested_active = optional_bool(row.get("is_active"), default=True)
            if resource is None:
                resource = uow.execute(
                    lambda: resource_service.create_resource(**payload),
                    change_type=ResourceMasterChangeType.CREATED,
                )
                summary.created_count += 1
            else:
                payload.update(
                    kind=resource.kind,
                    worker_type=resource.worker_type,
                    employee_id=resource.employee_id,
                    department_id=resource.department_id,
                    site_id=resource.site_id,
                )
                resource = uow.execute(
                    lambda: resource_service.update_resource(
                        resource_id=resource.id,
                        expected_version=resource.version,
                        **payload,
                    ),
                    change_type=ResourceMasterChangeType.UPDATED,
                )
                summary.updated_count += 1
            if resource.is_active != requested_active:
                operation = (
                    resource_service.reactivate_resource
                    if requested_active
                    else resource_service.deactivate_resource
                )
                resource = uow.execute(
                    lambda: operation(
                        resource_id=resource.id,
                        expected_version=resource.version,
                    ),
                    change_type=(
                        ResourceMasterChangeType.REACTIVATED
                        if requested_active
                        else ResourceMasterChangeType.DEACTIVATED
                    ),
                )
            existing = {r.id: r for r in resource_service.list_resources()}
            existing_by_name = {r.name.strip().lower(): r for r in resource_service.list_resources()}
        except Exception as exc:
            summary.add_row_error(line_no=line_no, message=str(exc))
    return summary

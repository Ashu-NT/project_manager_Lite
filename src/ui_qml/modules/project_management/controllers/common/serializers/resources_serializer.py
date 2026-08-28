from __future__ import annotations

from src.ui_qml.modules.project_management.view_models.resources import (
    ResourceAvailabilityViewModel,
    ResourceCatalogOverviewViewModel,
    ResourceDetailViewModel,
    ResourceEmployeeOptionViewModel,
    ResourceInspectorViewModel,
    ResourceRecordViewModel,
)


def _hours_label(value: float) -> str:
    return f"{value:,.1f} h"


def _availability_day_status(day) -> str:
    if day.overallocated:
        return "Over capacity"
    if day.effective_capacity_hours <= 0:
        return "Non-working"
    return "Within capacity"


def serialize_resource_catalog_overview_view_model(
    view_model: ResourceCatalogOverviewViewModel,
) -> dict[str, object]:
    return {
        "title": view_model.title,
        "subtitle": view_model.subtitle,
        "metrics": [
            {
                "label": metric.label,
                "value": metric.value,
                "supportingText": metric.supporting_text,
            }
            for metric in view_model.metrics
        ],
    }


def serialize_resource_employee_option_view_models(
    view_models: tuple[ResourceEmployeeOptionViewModel, ...],
) -> list[dict[str, object]]:
    return [
        {
            "value": view_model.value,
            "label": view_model.label,
            "name": view_model.name,
            "title": view_model.title,
            "contact": view_model.contact,
            "context": view_model.context,
            "department": view_model.department,
            "site": view_model.site,
            "departmentId": view_model.department_id,
            "siteId": view_model.site_id,
            "isActive": view_model.is_active,
        }
        for view_model in view_models
    ]


def serialize_resource_record_view_models(
    view_models: tuple[ResourceRecordViewModel, ...],
) -> list[dict[str, object]]:
    return [
        {
            "id": view_model.id,
            "title": view_model.title,
            "resourceCode": str(view_model.state.get("resourceCode", "") or ""),
            "statusLabel": view_model.status_label,
            "subtitle": view_model.subtitle,
            "supportingText": view_model.supporting_text,
            "metaText": view_model.meta_text,
            "role": str(view_model.state.get("role", "") or ""),
            "organization": str(view_model.state.get("organization", "") or ""),
            "department": str(view_model.state.get("department", "") or ""),
            "site": str(view_model.state.get("site", "") or ""),
            "workerTypeLabel": str(view_model.state.get("workerTypeLabel", "") or ""),
            "costTypeLabel": str(view_model.state.get("costTypeLabel", "") or ""),
            "capacityPercent": float(view_model.state.get("capacityPercent", 0.0) or 0.0),
            "capacityLabel": str(view_model.state.get("capacityLabel", "") or ""),
            "canPrimaryAction": view_model.can_primary_action,
            "canSecondaryAction": view_model.can_secondary_action,
            "canTertiaryAction": view_model.can_tertiary_action,
            "state": dict(view_model.state),
        }
        for view_model in view_models
    ]


def serialize_resource_availability_view_model(
    vm: ResourceAvailabilityViewModel,
) -> dict[str, object]:
    return {
        "resourceId": vm.resource_id,
        "startDate": vm.start_date,
        "endDate": vm.end_date,
        "fromDateLabel": vm.from_date_label,
        "toDateLabel": vm.to_date_label,
        "calendarSourceLabel": vm.calendar_source_label,
        "capacityPercent": vm.capacity_percent,
        "baseCapacityHours": vm.base_capacity_hours,
        "effectiveCapacityHours": vm.effective_capacity_hours,
        "plannedCommitmentHours": vm.planned_commitment_hours,
        "allocatedPlannedHours": vm.allocated_planned_hours,
        "remainingCapacityHours": vm.remaining_capacity_hours,
        "utilizationPercent": vm.utilization_percent,
        "utilizationLabel": vm.utilization_label,
        "overallocated": vm.overallocated,
        "conflictDays": vm.conflict_days,
        "projectCount": vm.project_count,
        "assignmentCount": vm.assignment_count,
        "days": [
            {
                "id": d.work_date,
                "workDate": d.work_date,
                "dateLabel": d.date_label,
                "baseCapacityHours": d.base_capacity_hours,
                "baseCapacityLabel": _hours_label(d.base_capacity_hours),
                "effectiveCapacityHours": d.effective_capacity_hours,
                "effectiveCapacityLabel": _hours_label(d.effective_capacity_hours),
                "plannedCommitmentHours": d.planned_commitment_hours,
                "plannedCommitmentLabel": _hours_label(d.planned_commitment_hours),
                "remainingCapacityHours": d.remaining_capacity_hours,
                "remainingCapacityLabel": _hours_label(d.remaining_capacity_hours),
                "utilizationPercent": d.utilization_percent,
                "utilizationLabel": d.utilization_label,
                "overallocated": d.overallocated,
                "statusLabel": _availability_day_status(d),
                "assignmentCount": d.assignment_count,
            }
            for d in vm.days
        ],
    }


def serialize_resource_detail_view_model(
    view_model: ResourceDetailViewModel,
) -> dict[str, object]:
    return {
        "id": view_model.id,
        "title": view_model.title,
        "statusLabel": view_model.status_label,
        "subtitle": view_model.subtitle,
        "description": view_model.description,
        "emptyState": view_model.empty_state,
        "fields": [
            {
                "label": field.label,
                "value": field.value,
                "supportingText": field.supporting_text,
            }
            for field in view_model.fields
        ],
        "state": dict(view_model.state),
    }


def serialize_resource_inspector_view_model(
    view_model: ResourceInspectorViewModel,
) -> dict[str, object]:
    return {
        "id": view_model.id,
        "title": view_model.title,
        "statusLabel": view_model.status_label,
        "fields": [
            {
                "label": field.label,
                "value": field.value,
                "supportingText": field.supporting_text,
            }
            for field in view_model.fields
        ],
        "state": dict(view_model.state),
    }


__all__ = [
    "serialize_resource_availability_view_model",
    "serialize_resource_catalog_overview_view_model",
    "serialize_resource_detail_view_model",
    "serialize_resource_employee_option_view_models",
    "serialize_resource_inspector_view_model",
    "serialize_resource_record_view_models",
]

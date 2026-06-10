from __future__ import annotations

from src.ui_qml.modules.project_management.view_models.resources import (
    ResourceAvailabilityViewModel,
    ResourceCatalogOverviewViewModel,
    ResourceCertificationViewModel,
    ResourceDetailViewModel,
    ResourceEmployeeOptionViewModel,
    ResourceRecordViewModel,
    ResourceSkillViewModel,
)


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
            "workerTypeLabel": str(view_model.state.get("workerTypeLabel", "") or ""),
            "costTypeLabel": str(view_model.state.get("costTypeLabel", "") or ""),
            "hourlyRateLabel": str(view_model.state.get("hourlyRateLabel", "") or ""),
            "canPrimaryAction": view_model.can_primary_action,
            "canSecondaryAction": view_model.can_secondary_action,
            "canTertiaryAction": view_model.can_tertiary_action,
            "utilizationValue": {
                "value": float(view_model.state.get("capacityPercent", "0") or "0") / 100.0,
                "label": view_model.state.get("capacityLabel", "—"),
            },
            "state": dict(view_model.state),
        }
        for view_model in view_models
    ]


def serialize_resource_skill_view_models(
    view_models: tuple[ResourceSkillViewModel, ...],
) -> list[dict[str, object]]:
    return [
        {
            "id": vm.id,
            "title": vm.skill_name or vm.skill_code,
            "subtitle": vm.skill_code,
            "statusLabel": vm.proficiency_label,
            "metaText": vm.notes or "",
            "skillCode": vm.skill_code,
            "skillName": vm.skill_name,
            "proficiency": vm.proficiency,
            "proficiencyLabel": vm.proficiency_label,
            "notes": vm.notes,
        }
        for vm in view_models
    ]


def serialize_resource_certification_view_models(
    view_models: tuple[ResourceCertificationViewModel, ...],
) -> list[dict[str, object]]:
    return [
        {
            "id": vm.id,
            "title": vm.certification_name or vm.certification_code,
            "subtitle": vm.certification_code,
            "statusLabel": vm.cert_status,
            "metaText": vm.expiry_date or "",
            "certificationCode": vm.certification_code,
            "certificationName": vm.certification_name,
            "issuedDate": vm.issued_date or "",
            "expiryDate": vm.expiry_date or "",
            "issuingBody": vm.issuing_body,
            "notes": vm.notes,
            "certStatus": vm.cert_status,
            "certStatusLabel": vm.cert_status_label,
        }
        for vm in view_models
    ]


def serialize_resource_availability_view_model(
    vm: ResourceAvailabilityViewModel,
) -> dict[str, object]:
    return {
        "resourceId": vm.resource_id,
        "peakLoadPercent": vm.peak_load_percent,
        "averageLoadPercent": vm.average_load_percent,
        "overloadedDays": vm.overloaded_days,
        "availableDays": vm.available_days,
        "isAvailable": vm.is_available,
        "fromDateLabel": vm.from_date_label,
        "toDateLabel": vm.to_date_label,
        "days": [
            {
                "dateLabel": d.date_label,
                "allocationPercent": d.allocation_percent,
                "allocationLabel": d.allocation_label,
                "overloaded": d.overloaded,
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


__all__ = [
    "serialize_resource_availability_view_model",
    "serialize_resource_catalog_overview_view_model",
    "serialize_resource_certification_view_models",
    "serialize_resource_detail_view_model",
    "serialize_resource_employee_option_view_models",
    "serialize_resource_record_view_models",
    "serialize_resource_skill_view_models",
]

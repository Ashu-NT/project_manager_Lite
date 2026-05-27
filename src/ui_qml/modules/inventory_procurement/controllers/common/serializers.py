from __future__ import annotations

from src.ui_qml.modules.inventory_procurement.view_models.catalog import (
    InventoryCatalogOverviewViewModel,
    InventoryDetailViewModel,
    InventoryDocumentOptionViewModel,
    InventoryRecordViewModel,
)
from src.ui_qml.modules.inventory_procurement.view_models.dashboard import (
    InventoryDashboardOverviewViewModel,
    InventoryDashboardSectionViewModel,
)
from src.ui_qml.modules.inventory_procurement.view_models.foundation import (
    InventoryInventoryFoundationViewModel,
)
from src.ui_qml.modules.inventory_procurement.view_models.workspace import (
    InventoryProcurementWorkspaceViewModel,
)


def serialize_workspace_view_model(
    view_model: InventoryProcurementWorkspaceViewModel,
) -> dict[str, str]:
    return {
        "routeId": view_model.route_id,
        "title": view_model.title,
        "summary": view_model.summary,
        "migrationStatus": view_model.migration_status,
        "legacyRuntimeStatus": view_model.legacy_runtime_status,
    }


def serialize_dashboard_overview_view_model(
    view_model: InventoryDashboardOverviewViewModel,
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


def serialize_dashboard_section_view_models(
    view_models: tuple[InventoryDashboardSectionViewModel, ...],
) -> list[dict[str, object]]:
    return [
        {
            "title": view_model.title,
            "subtitle": view_model.subtitle,
            "emptyState": view_model.empty_state,
            "rows": [
                {
                    "id": row.id,
                    "title": row.title,
                    "subtitle": row.subtitle,
                    "statusLabel": row.status_label,
                    "supportingText": row.supporting_text,
                    "metaText": row.meta_text,
                    "tone": row.tone,
                }
                for row in view_model.rows
            ],
        }
        for view_model in view_models
    ]


def serialize_selector_options(view_models) -> list[dict[str, str]]:
    return [
        {
            "value": view_model.value,
            "label": view_model.label,
        }
        for view_model in view_models
    ]


def serialize_document_option_view_models(
    view_models: tuple[InventoryDocumentOptionViewModel, ...],
) -> list[dict[str, object]]:
    return [
        {
            "value": view_model.value,
            "label": view_model.label,
            "documentType": view_model.document_type,
            "storageKind": view_model.storage_kind,
            "effectiveDateLabel": view_model.effective_date_label,
            "isActive": view_model.is_active,
        }
        for view_model in view_models
    ]


def serialize_catalog_overview_view_model(
    view_model: InventoryCatalogOverviewViewModel,
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


_RESERVED_ROW_KEYS: frozenset[str] = frozenset({
    "id", "title", "statusLabel", "subtitle", "supportingText",
    "metaText", "canPrimaryAction", "canSecondaryAction",
    "canTertiaryAction", "state",
})


def serialize_record_view_models(
    view_models: tuple[InventoryRecordViewModel, ...],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for view_model in view_models:
        state = dict(view_model.state)
        row: dict[str, object] = {
            "id": view_model.id,
            "title": view_model.title,
            "statusLabel": view_model.status_label,
            "subtitle": view_model.subtitle,
            "supportingText": view_model.supporting_text,
            "metaText": view_model.meta_text,
            "canPrimaryAction": view_model.can_primary_action,
            "canSecondaryAction": view_model.can_secondary_action,
            "canTertiaryAction": view_model.can_tertiary_action,
            "state": state,
        }
        for key, value in state.items():
            if key not in _RESERVED_ROW_KEYS:
                row[key] = value
        rows.append(row)
    return rows


def serialize_catalog_detail_view_model(
    view_model: InventoryDetailViewModel,
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
        "linkedDocuments": serialize_document_option_view_models(
            view_model.linked_documents
        ),
        "state": dict(view_model.state),
    }


def serialize_foundation_view_model(
    view_model: InventoryInventoryFoundationViewModel,
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
        "moduleLinks": [
            {
                "code": link.code,
                "label": link.label,
                "kind": link.kind,
                "isEnabled": link.is_enabled,
                "statusLabel": link.status_label,
                "reason": link.reason,
                "routeId": link.route_id,
            }
            for link in view_model.module_links
        ],
        "locationTypeOptions": serialize_selector_options(view_model.location_type_options),
        "cycleCountStatusOptions": serialize_selector_options(
            view_model.cycle_count_status_options
        ),
        "locations": serialize_record_view_models(view_model.locations),
        "reorderPolicies": serialize_record_view_models(view_model.reorder_policies),
        "cycleCounts": serialize_record_view_models(view_model.cycle_counts),
        "valuationSignals": serialize_record_view_models(view_model.valuation_signals),
        "trackingSignals": serialize_record_view_models(view_model.tracking_signals),
        "activitySignals": serialize_record_view_models(view_model.activity_signals),
    }


def serialize_audit_entries_for_activity(
    entries: object,
    entity_id: str,
) -> list[dict[str, object]]:
    items: list[dict[str, object]] = []
    for entry in entries:
        if getattr(entry, "entity_id", None) != entity_id:
            continue
        action = getattr(entry, "action", "") or ""
        details = getattr(entry, "details_label", "") or action
        actor = getattr(entry, "actor_username", "") or ""
        title = f"{details} — {actor}" if actor else details
        meta = str(getattr(entry, "occurred_at", "") or "")
        al = action.lower()
        if any(k in al for k in ("creat", "add", "open", "approv", "complet", "receiv")):
            status = "success"
        elif any(k in al for k in ("delet", "cancel", "reject", "close", "remov")):
            status = "danger"
        elif any(k in al for k in ("updat", "edit", "modif", "submit", "post", "transfer", "issue", "return", "adjust")):
            status = "warning"
        else:
            status = ""
        items.append({"title": title, "metaText": meta, "statusLabel": status, "routeId": ""})
    return items


__all__ = [
    "serialize_audit_entries_for_activity",
    "serialize_catalog_detail_view_model",
    "serialize_catalog_overview_view_model",
    "serialize_document_option_view_models",
    "serialize_foundation_view_model",
    "serialize_record_view_models",
    "serialize_selector_options",
    "serialize_dashboard_overview_view_model",
    "serialize_dashboard_section_view_models",
    "serialize_workspace_view_model",
]

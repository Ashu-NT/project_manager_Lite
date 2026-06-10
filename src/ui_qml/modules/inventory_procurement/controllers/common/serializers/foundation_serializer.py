from __future__ import annotations

from src.ui_qml.modules.inventory_procurement.view_models.foundation import (
    InventoryInventoryFoundationViewModel,
)

from .record_serializer import serialize_record_view_models
from .selector_serializer import serialize_selector_options


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

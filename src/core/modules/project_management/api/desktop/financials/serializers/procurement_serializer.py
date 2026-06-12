"""Procurement requisition serializer."""

from __future__ import annotations

from src.core.modules.project_management.api.desktop.financials.models.procurement import ProjectRequisitionDesktopDto


def serialize_requisition(requisition) -> ProjectRequisitionDesktopDto:
    status_value = str(
        getattr(getattr(requisition, "status", None), "value", None)
        or getattr(requisition, "status", "")
        or ""
    )
    return ProjectRequisitionDesktopDto(
        id=requisition.id,
        requisition_number=str(getattr(requisition, "requisition_number", "") or ""),
        status=status_value,
        status_label=status_value.replace("_", " ").title(),
        purpose=str(getattr(requisition, "purpose", "") or ""),
        needed_by_date=getattr(requisition, "needed_by_date", None),
        priority=str(getattr(requisition, "priority", "") or ""),
        notes=str(getattr(requisition, "notes", "") or ""),
    )


__all__ = ["serialize_requisition"]

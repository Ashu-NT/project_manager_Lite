from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def approval_module_label(request: object) -> str:
    explicit = str(_payload(request).get("module_label") or getattr(request, "module_label", "") or "").strip()
    if explicit:
        return explicit
    request_type = str(getattr(request, "request_type", "") or "").strip().lower()
    entity_type = str(getattr(request, "entity_type", "") or "").strip().lower()
    if request_type.startswith("purchase_requisition.") or request_type.startswith("purchase_order."):
        return "Inventory & Procurement"
    if entity_type in {"purchase_requisition", "purchase_order"}:
        return "Inventory & Procurement"
    if request_type.startswith(("baseline.", "dependency.", "cost.")):
        return "Project Management"
    if entity_type in {"project_baseline", "task_dependency", "cost_item"}:
        return "Project Management"
    return "Shared Governance"


def approval_context_label(request: object) -> str:
    explicit = str(_payload(request).get("context_label") or getattr(request, "context_label", "") or "").strip()
    if explicit:
        return explicit
    payload = _payload(request)
    project_name = str(payload.get("project_name") or "").strip()
    if project_name:
        return project_name
    requisition_number = str(payload.get("requisition_number") or "").strip()
    if requisition_number:
        return f"Requisition {requisition_number}"
    po_number = str(payload.get("po_number") or "").strip()
    if po_number:
        supplier_name = str(payload.get("supplier_name") or "").strip()
        site_name = str(payload.get("site_name") or "").strip()
        line_count = int(payload.get("line_count") or 0)
        total_amount = payload.get("total_amount")
        currency_code = str(payload.get("currency_code") or "").strip()

        segments = [f"PO {po_number}"]
        if supplier_name:
            segments.append(supplier_name)
        if site_name:
            segments.append(site_name)
        if line_count:
            segments.append(f"{line_count} line{'s' if line_count != 1 else ''}")
        if total_amount not in (None, ""):
            amount = (
                f"{currency_code} {total_amount:.2f}"
                if isinstance(total_amount, (int, float))
                else f"{currency_code} {total_amount}"
            )
            segments.append(amount)

        return " | ".join(segments)
    project_id = str(getattr(request, "project_id", "") or "").strip()
    if project_id:
        return project_id
    return "-"


def approval_display_label(request: object) -> str:
    explicit = str(_payload(request).get("display_label") or getattr(request, "display_label", "") or "").strip()
    if explicit:
        return explicit

    payload = _payload(request)
    request_type = str(getattr(request, "request_type", "") or "").strip()

    if request_type == "baseline.create":
        baseline_name = str(payload.get("name") or "Baseline").strip() or "Baseline"
        project_name = str(payload.get("project_name") or "selected project").strip() or "selected project"
        return f"Create baseline '{baseline_name}' for {project_name}"

    if request_type == "dependency.add":
        predecessor_name = str(payload.get("predecessor_name") or "predecessor task").strip() or "predecessor task"
        successor_name = str(payload.get("successor_name") or "successor task").strip() or "successor task"
        dependency_type = str(payload.get("dependency_type") or "FS").strip().upper()
        lag_days = int(payload.get("lag_days") or 0)
        lag_label = f", lag {lag_days}d" if lag_days else ""
        return f"Add dependency: {predecessor_name} -> {successor_name} ({dependency_type}{lag_label})"

    if request_type == "dependency.remove":
        predecessor_name = str(payload.get("predecessor_name") or "").strip()
        successor_name = str(payload.get("successor_name") or "").strip()
        if predecessor_name and successor_name:
            return f"Remove dependency: {predecessor_name} -> {successor_name}"
        return "Remove dependency"

    if request_type.startswith("cost."):
        action = {
            "cost.add": "Add",
            "cost.update": "Update",
            "cost.delete": "Delete",
        }.get(request_type, "Change")
        description = str(payload.get("description") or "").strip() or "cost item"
        task_name = str(payload.get("task_name") or "").strip()
        project_name = str(payload.get("project_name") or "").strip()
        if task_name:
            return f"{action} cost '{description}' for task '{task_name}'"
        if project_name:
            return f"{action} cost '{description}' for {project_name}"
        return f"{action} cost '{description}'"

    if request_type == "purchase_requisition.submit":
        requisition_number = str(payload.get("requisition_number") or "").strip()
        if requisition_number:
            return f"Submit requisition {requisition_number}"
        return "Submit purchase requisition"

    if request_type == "purchase_order.submit":
        po_number = str(payload.get("po_number") or "").strip()
        supplier_name = str(payload.get("supplier_name") or "").strip()
        site_name = str(payload.get("site_name") or "").strip()
        line_count = int(payload.get("line_count") or 0)
        total_amount = payload.get("total_amount")
        currency_code = str(payload.get("currency_code") or "").strip()

        base = "Submit purchase order"
        if po_number:
            base = f"{base} {po_number}"

        details: list[str] = []
        if supplier_name:
            details.append(f"supplier {supplier_name}")
        if site_name:
            details.append(f"site {site_name}")
        if line_count:
            details.append(f"{line_count} line{'s' if line_count != 1 else ''}")
        if total_amount not in (None, ""):
            amount = (
                f"{currency_code} {total_amount:.2f}"
                if isinstance(total_amount, (int, float))
                else f"{currency_code} {total_amount}"
            )
            details.append(amount)

        if details:
            base = f"{base} ({', '.join(details)})"
        return base

    fallback = str(getattr(request, "entity_type", "") or "governed change").replace("_", " ").strip()
    return fallback.title()


def _payload(request: object) -> dict[str, Any]:
    payload = getattr(request, "payload", None)
    if isinstance(payload, Mapping):
        return dict(payload)
    return {}

from __future__ import annotations

from src.core.modules.maintenance.api.desktop import MaintenanceWorkOrderUpdateCommand


def set_work_order_status(
    desktop_api,
    work_order_id: str,
    *,
    status: str,
    expected_version: int,
) -> None:
    if not (work_order_id or "").strip():
        raise ValueError("Work order ID is required before updating status.")
    if not (status or "").strip():
        raise ValueError("Choose a status before saving.")
    desktop_api.update_work_order(
        MaintenanceWorkOrderUpdateCommand(
            work_order_id=work_order_id.strip(),
            status=status.strip(),
            expected_version=expected_version,
        )
    )

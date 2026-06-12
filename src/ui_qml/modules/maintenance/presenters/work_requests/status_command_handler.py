from __future__ import annotations

from src.core.modules.maintenance.api.desktop import MaintenanceWorkRequestUpdateCommand


def set_work_request_status(
    desktop_api,
    work_request_id: str,
    *,
    status: str,
    expected_version: int,
) -> None:
    if not (work_request_id or "").strip():
        raise ValueError("Work request ID is required before updating status.")
    if not (status or "").strip():
        raise ValueError("Choose a status before saving.")
    desktop_api.update_work_request(
        MaintenanceWorkRequestUpdateCommand(
            work_request_id=work_request_id.strip(),
            status=status.strip(),
            expected_version=expected_version,
        )
    )

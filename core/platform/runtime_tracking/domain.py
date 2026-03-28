from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from core.platform.common.ids import generate_id


@dataclass
class RuntimeExecution:
    id: str
    operation_type: str
    operation_key: str
    module_code: str
    status: str
    requested_by_user_id: str | None = None
    requested_by_username: str | None = None
    input_path: str | None = None
    output_path: str | None = None
    created_count: int = 0
    updated_count: int = 0
    error_count: int = 0
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @staticmethod
    def create(
        *,
        operation_type: str,
        operation_key: str,
        module_code: str,
        requested_by_user_id: str | None = None,
        requested_by_username: str | None = None,
        input_path: str | None = None,
        output_path: str | None = None,
    ) -> "RuntimeExecution":
        now = datetime.now(timezone.utc)
        return RuntimeExecution(
            id=generate_id(),
            operation_type=str(operation_type or "").strip() or "runtime",
            operation_key=str(operation_key or "").strip() or "operation",
            module_code=str(module_code or "").strip() or "platform",
            status="RUNNING",
            requested_by_user_id=requested_by_user_id,
            requested_by_username=requested_by_username,
            input_path=(str(input_path or "").strip() or None),
            output_path=(str(output_path or "").strip() or None),
            started_at=now,
            completed_at=None,
            created_at=now,
            updated_at=now,
        )


__all__ = ["RuntimeExecution"]

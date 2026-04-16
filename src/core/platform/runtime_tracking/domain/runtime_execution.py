from __future__ import annotations

from dataclasses import dataclass, field
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
    output_file_name: str | None = None
    output_media_type: str | None = None
    output_metadata: dict[str, object] = field(default_factory=dict)
    created_count: int = 0
    updated_count: int = 0
    error_count: int = 0
    error_message: str | None = None
    cancellation_requested_at: datetime | None = None
    cancellation_requested_by_user_id: str | None = None
    cancellation_requested_by_username: str | None = None
    retry_of_execution_id: str | None = None
    attempt_number: int = 1
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
        retry_of_execution_id: str | None = None,
        attempt_number: int = 1,
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
            output_file_name=None,
            output_media_type=None,
            output_metadata={},
            started_at=now,
            completed_at=None,
            cancellation_requested_at=None,
            cancellation_requested_by_user_id=None,
            cancellation_requested_by_username=None,
            retry_of_execution_id=(str(retry_of_execution_id or "").strip() or None),
            attempt_number=max(1, int(attempt_number or 1)),
            created_at=now,
            updated_at=now,
        )


__all__ = ["RuntimeExecution"]

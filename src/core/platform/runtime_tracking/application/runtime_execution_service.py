from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from core.platform.auth.session import UserSessionContext
from src.core.platform.runtime_tracking.contracts import RuntimeExecutionRepository
from src.core.platform.runtime_tracking.domain import RuntimeExecution


class RuntimeExecutionService:
    def __init__(
        self,
        *,
        runtime_execution_repo: RuntimeExecutionRepository,
        user_session: UserSessionContext | None = None,
    ) -> None:
        self._runtime_execution_repo = runtime_execution_repo
        self._user_session = user_session

    def start_execution(
        self,
        *,
        operation_type: str,
        operation_key: str,
        module_code: str,
        input_path: str | Path | None = None,
        output_path: str | Path | None = None,
        retry_of_execution_id: str | None = None,
        attempt_number: int | None = None,
    ) -> RuntimeExecution:
        principal = self._user_session.principal if self._user_session is not None else None
        resolved_attempt_number = max(1, int(attempt_number or 1))
        if retry_of_execution_id and attempt_number is None:
            previous = self._runtime_execution_repo.get(retry_of_execution_id)
            if previous is not None:
                resolved_attempt_number = max(1, int(previous.attempt_number or 1)) + 1
        execution = RuntimeExecution.create(
            operation_type=operation_type,
            operation_key=operation_key,
            module_code=module_code,
            requested_by_user_id=getattr(principal, "user_id", None),
            requested_by_username=str(getattr(principal, "username", "") or "") or None,
            input_path=str(input_path) if input_path is not None else None,
            output_path=str(output_path) if output_path is not None else None,
            retry_of_execution_id=retry_of_execution_id,
            attempt_number=resolved_attempt_number,
        )
        self._runtime_execution_repo.add(execution)
        return execution

    def complete_execution(
        self,
        execution: RuntimeExecution,
        *,
        output_path: str | Path | None = None,
        output_file_name: str | None = None,
        output_media_type: str | None = None,
        output_metadata: dict[str, object] | None = None,
        created_count: int | None = None,
        updated_count: int | None = None,
        error_count: int | None = None,
    ) -> RuntimeExecution:
        execution.status = "COMPLETED"
        execution.output_path = str(output_path) if output_path is not None else execution.output_path
        execution.output_file_name = (str(output_file_name or "").strip() or execution.output_file_name)
        execution.output_media_type = (str(output_media_type or "").strip() or execution.output_media_type)
        execution.output_metadata = dict(output_metadata or execution.output_metadata or {})
        execution.created_count = int(created_count or 0)
        execution.updated_count = int(updated_count or 0)
        execution.error_count = int(error_count or 0)
        execution.completed_at = datetime.now(timezone.utc)
        execution.updated_at = execution.completed_at
        self._runtime_execution_repo.update(execution)
        return execution

    def fail_execution(
        self,
        execution: RuntimeExecution,
        *,
        error_message: str,
        output_path: str | Path | None = None,
        output_file_name: str | None = None,
        output_media_type: str | None = None,
        output_metadata: dict[str, object] | None = None,
    ) -> RuntimeExecution:
        execution.status = "FAILED"
        execution.error_message = str(error_message or "").strip() or "Runtime execution failed."
        execution.output_path = str(output_path) if output_path is not None else execution.output_path
        execution.output_file_name = (str(output_file_name or "").strip() or execution.output_file_name)
        execution.output_media_type = (str(output_media_type or "").strip() or execution.output_media_type)
        execution.output_metadata = dict(output_metadata or execution.output_metadata or {})
        execution.completed_at = datetime.now(timezone.utc)
        execution.updated_at = execution.completed_at
        self._runtime_execution_repo.update(execution)
        return execution

    def request_cancellation(self, execution_id: str) -> RuntimeExecution:
        execution = self.get_execution(execution_id)
        if execution is None:
            raise ValueError("Runtime execution not found.")
        if execution.status in {"COMPLETED", "FAILED", "CANCELLED"}:
            return execution
        principal = self._user_session.principal if self._user_session is not None else None
        execution.status = "CANCELLATION_REQUESTED"
        execution.cancellation_requested_at = datetime.now(timezone.utc)
        execution.cancellation_requested_by_user_id = getattr(principal, "user_id", None)
        execution.cancellation_requested_by_username = str(getattr(principal, "username", "") or "") or None
        execution.updated_at = execution.cancellation_requested_at
        self._runtime_execution_repo.update(execution)
        return execution

    def cancel_execution(self, execution: RuntimeExecution, *, error_message: str | None = None) -> RuntimeExecution:
        execution.status = "CANCELLED"
        execution.error_message = str(error_message or "").strip() or "Runtime execution cancelled."
        execution.completed_at = datetime.now(timezone.utc)
        execution.updated_at = execution.completed_at
        self._runtime_execution_repo.update(execution)
        return execution

    def start_retry(
        self,
        execution_id: str,
        *,
        input_path: str | Path | None = None,
        output_path: str | Path | None = None,
    ) -> RuntimeExecution:
        previous = self.get_execution(execution_id)
        if previous is None:
            raise ValueError("Runtime execution not found.")
        return self.start_execution(
            operation_type=previous.operation_type,
            operation_key=previous.operation_key,
            module_code=previous.module_code,
            input_path=input_path if input_path is not None else previous.input_path,
            output_path=output_path if output_path is not None else previous.output_path,
            retry_of_execution_id=previous.id,
        )

    def get_execution(self, execution_id: str) -> RuntimeExecution | None:
        return self._runtime_execution_repo.get(execution_id)

    def list_recent(
        self,
        *,
        limit: int = 200,
        module_code: str | None = None,
        status: str | None = None,
    ) -> list[RuntimeExecution]:
        return self._runtime_execution_repo.list_recent(
            limit=limit,
            module_code=module_code,
            status=status,
        )


__all__ = ["RuntimeExecutionService"]

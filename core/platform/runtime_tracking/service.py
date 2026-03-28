from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from core.platform.auth.session import UserSessionContext
from core.platform.runtime_tracking.contracts import RuntimeExecutionRepository
from core.platform.runtime_tracking.domain import RuntimeExecution


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
    ) -> RuntimeExecution:
        principal = self._user_session.principal if self._user_session is not None else None
        execution = RuntimeExecution.create(
            operation_type=operation_type,
            operation_key=operation_key,
            module_code=module_code,
            requested_by_user_id=getattr(principal, "user_id", None),
            requested_by_username=str(getattr(principal, "username", "") or "") or None,
            input_path=str(input_path) if input_path is not None else None,
            output_path=str(output_path) if output_path is not None else None,
        )
        self._runtime_execution_repo.add(execution)
        return execution

    def complete_execution(
        self,
        execution: RuntimeExecution,
        *,
        output_path: str | Path | None = None,
        created_count: int | None = None,
        updated_count: int | None = None,
        error_count: int | None = None,
    ) -> RuntimeExecution:
        execution.status = "COMPLETED"
        execution.output_path = str(output_path) if output_path is not None else execution.output_path
        execution.created_count = int(created_count or 0)
        execution.updated_count = int(updated_count or 0)
        execution.error_count = int(error_count or 0)
        execution.completed_at = datetime.now(timezone.utc)
        execution.updated_at = execution.completed_at
        self._runtime_execution_repo.update(execution)
        return execution

    def fail_execution(self, execution: RuntimeExecution, *, error_message: str) -> RuntimeExecution:
        execution.status = "FAILED"
        execution.error_message = str(error_message or "").strip() or "Runtime execution failed."
        execution.completed_at = datetime.now(timezone.utc)
        execution.updated_at = execution.completed_at
        self._runtime_execution_repo.update(execution)
        return execution

    def list_recent(self, *, limit: int = 200) -> list[RuntimeExecution]:
        return self._runtime_execution_repo.list_recent(limit=limit)


__all__ = ["RuntimeExecutionService"]

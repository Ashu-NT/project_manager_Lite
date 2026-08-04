from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from src.core.platform.auth.domain.session import UserSessionContext
from src.core.platform.common.exceptions import BusinessRuleError
from src.core.platform.contract.data_operations.runtime_tracking.contracts import RuntimeExecutionRepository
from src.core.platform.domain.data_operations.runtime_tracking import RuntimeExecution
from src.core.platform.tenancy.tenant_context import TenantContextService


class RuntimeExecutionService:
    def __init__(
        self,
        *,
        runtime_execution_repo: RuntimeExecutionRepository,
        tenant_context_service: TenantContextService,
        user_session: UserSessionContext | None = None,
    ) -> None:
        self._runtime_execution_repo = runtime_execution_repo
        self._tenant_context_service = tenant_context_service
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
        ctx = self._tenant_context_service.require_organization_context(
            operation_label="start runtime execution"
        )
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
            tenant_id=ctx.tenant_id,
            organization_id=ctx.organization_id,
            requested_by_user_id=getattr(principal, "user_id", None),
            requested_by_username=str(getattr(principal, "username", "") or "") or None,
            authorization_context_id=(
                str(getattr(principal, "session_id", "") or "").strip() or None
            ),
            input_path=input_path,
            output_path=output_path,
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
        self._require_execution_scope(execution, operation_label="complete runtime execution")
        execution.status = "COMPLETED"
        if output_path is not None:
            execution.output_path = output_path
        if str(output_file_name or "").strip():
            execution.output_file_name = output_file_name
        if str(output_media_type or "").strip():
            execution.output_media_type = output_media_type
        if output_metadata is not None:
            execution.output_metadata = output_metadata
        execution.created_count = created_count
        execution.updated_count = updated_count
        execution.error_count = error_count
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
        self._require_execution_scope(execution, operation_label="fail runtime execution")
        execution.status = "FAILED"
        execution.error_message = str(error_message or "").strip() or "Runtime execution failed."
        if output_path is not None:
            execution.output_path = output_path
        if str(output_file_name or "").strip():
            execution.output_file_name = output_file_name
        if str(output_media_type or "").strip():
            execution.output_media_type = output_media_type
        if output_metadata is not None:
            execution.output_metadata = output_metadata
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
        self._require_execution_scope(execution, operation_label="cancel runtime execution")
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

    def artifact_metadata(
        self,
        execution: RuntimeExecution,
        metadata: dict[str, object] | None = None,
    ) -> dict[str, object]:
        self._require_execution_scope(execution, operation_label="qualify runtime artifact")
        return {
            **dict(metadata or {}),
            "runtime_execution_id": execution.id,
            "tenant_id": execution.tenant_id,
            "organization_id": execution.organization_id,
            "authorization_context_id": execution.authorization_context_id or "",
        }

    def _require_execution_scope(
        self,
        execution: RuntimeExecution,
        *,
        operation_label: str,
    ) -> None:
        ctx = self._tenant_context_service.require_organization_context(
            operation_label=operation_label
        )
        if (
            execution.tenant_id != ctx.tenant_id
            or execution.organization_id != ctx.organization_id
        ):
            raise BusinessRuleError(
                "Runtime execution is outside the active tenant scope.",
                code="RUNTIME_EXECUTION_SCOPE_VIOLATION",
            )


__all__ = ["RuntimeExecutionService"]

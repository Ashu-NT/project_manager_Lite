from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.platform.runtime_tracking.contracts import RuntimeExecutionRepository
from core.platform.runtime_tracking.domain import RuntimeExecution
from src.infra.persistence.orm.platform.models import RuntimeExecutionORM


def _from_orm(obj: RuntimeExecutionORM) -> RuntimeExecution:
    return RuntimeExecution(
        id=obj.id,
        operation_type=obj.operation_type,
        operation_key=obj.operation_key,
        module_code=obj.module_code,
        status=obj.status,
        requested_by_user_id=obj.requested_by_user_id,
        requested_by_username=obj.requested_by_username,
        input_path=obj.input_path,
        output_path=obj.output_path,
        output_file_name=obj.output_file_name,
        output_media_type=obj.output_media_type,
        output_metadata=json.loads(obj.output_metadata_json or "{}"),
        created_count=obj.created_count,
        updated_count=obj.updated_count,
        error_count=obj.error_count,
        error_message=obj.error_message,
        cancellation_requested_at=obj.cancellation_requested_at,
        cancellation_requested_by_user_id=obj.cancellation_requested_by_user_id,
        cancellation_requested_by_username=obj.cancellation_requested_by_username,
        retry_of_execution_id=obj.retry_of_execution_id,
        attempt_number=obj.attempt_number,
        started_at=obj.started_at,
        completed_at=obj.completed_at,
        created_at=obj.created_at,
        updated_at=obj.updated_at,
    )


def _to_orm(execution: RuntimeExecution) -> RuntimeExecutionORM:
    return RuntimeExecutionORM(
        id=execution.id,
        operation_type=execution.operation_type,
        operation_key=execution.operation_key,
        module_code=execution.module_code,
        status=execution.status,
        requested_by_user_id=execution.requested_by_user_id,
        requested_by_username=execution.requested_by_username,
        input_path=execution.input_path,
        output_path=execution.output_path,
        output_file_name=execution.output_file_name,
        output_media_type=execution.output_media_type,
        output_metadata_json=json.dumps(execution.output_metadata or {}, sort_keys=True, default=str),
        created_count=execution.created_count,
        updated_count=execution.updated_count,
        error_count=execution.error_count,
        error_message=execution.error_message,
        cancellation_requested_at=execution.cancellation_requested_at,
        cancellation_requested_by_user_id=execution.cancellation_requested_by_user_id,
        cancellation_requested_by_username=execution.cancellation_requested_by_username,
        retry_of_execution_id=execution.retry_of_execution_id,
        attempt_number=execution.attempt_number,
        started_at=execution.started_at,
        completed_at=execution.completed_at,
        created_at=execution.created_at,
        updated_at=execution.updated_at,
    )


class SqlAlchemyRuntimeExecutionRepository(RuntimeExecutionRepository):
    def __init__(self, session: Session):
        self.session = session

    def add(self, execution: RuntimeExecution) -> None:
        self.session.add(_to_orm(execution))
        self.session.flush()

    def update(self, execution: RuntimeExecution) -> None:
        obj = self.session.get(RuntimeExecutionORM, execution.id)
        if obj is None:
            raise ValueError("Runtime execution not found.")
        obj.operation_type = execution.operation_type
        obj.operation_key = execution.operation_key
        obj.module_code = execution.module_code
        obj.status = execution.status
        obj.requested_by_user_id = execution.requested_by_user_id
        obj.requested_by_username = execution.requested_by_username
        obj.input_path = execution.input_path
        obj.output_path = execution.output_path
        obj.output_file_name = execution.output_file_name
        obj.output_media_type = execution.output_media_type
        obj.output_metadata_json = json.dumps(execution.output_metadata or {}, sort_keys=True, default=str)
        obj.created_count = execution.created_count
        obj.updated_count = execution.updated_count
        obj.error_count = execution.error_count
        obj.error_message = execution.error_message
        obj.cancellation_requested_at = execution.cancellation_requested_at
        obj.cancellation_requested_by_user_id = execution.cancellation_requested_by_user_id
        obj.cancellation_requested_by_username = execution.cancellation_requested_by_username
        obj.retry_of_execution_id = execution.retry_of_execution_id
        obj.attempt_number = execution.attempt_number
        obj.started_at = execution.started_at
        obj.completed_at = execution.completed_at
        obj.created_at = execution.created_at
        obj.updated_at = execution.updated_at
        self.session.flush()

    def get(self, execution_id: str) -> RuntimeExecution | None:
        obj = self.session.get(RuntimeExecutionORM, execution_id)
        return _from_orm(obj) if obj else None

    def list_recent(
        self,
        *,
        limit: int = 200,
        module_code: str | None = None,
        status: str | None = None,
    ) -> list[RuntimeExecution]:
        query = select(RuntimeExecutionORM)
        if module_code:
            query = query.where(RuntimeExecutionORM.module_code == str(module_code).strip())
        if status:
            query = query.where(RuntimeExecutionORM.status == str(status).strip().upper())
        rows = self.session.execute(
            query.order_by(RuntimeExecutionORM.started_at.desc()).limit(max(1, int(limit or 200)))
        ).scalars().all()
        return [_from_orm(row) for row in rows]


__all__ = ["SqlAlchemyRuntimeExecutionRepository"]

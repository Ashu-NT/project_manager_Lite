from __future__ import annotations

from src.core.platform.contract.repositories.data_operations.runtime_tracking.contracts import (
    RuntimeExecutionRepository,
)
from src.core.platform.domain.data_operations.runtime_tracking import RuntimeExecution


class RuntimeExecutionQueryHandler:
    """Read scoped execution history without mutating execution state."""

    def __init__(self, *, runtime_execution_repo: RuntimeExecutionRepository) -> None:
        self._runtime_execution_repo = runtime_execution_repo

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


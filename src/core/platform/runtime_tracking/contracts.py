from __future__ import annotations

from abc import ABC, abstractmethod

from src.core.platform.runtime_tracking.domain import RuntimeExecution


class RuntimeExecutionRepository(ABC):
    @abstractmethod
    def add(self, execution: RuntimeExecution) -> None: ...

    @abstractmethod
    def update(self, execution: RuntimeExecution) -> None: ...

    @abstractmethod
    def get(self, execution_id: str) -> RuntimeExecution | None: ...

    @abstractmethod
    def list_recent(
        self,
        *,
        limit: int = 200,
        module_code: str | None = None,
        status: str | None = None,
    ) -> list[RuntimeExecution]: ...


__all__ = ["RuntimeExecutionRepository"]

from abc import ABC, abstractmethod

from src.core.modules.project_management.domain.financials.labor_posting import ApprovedTimeLaborPosting


class ApprovedTimeLaborPostingRepository(ABC):
    @abstractmethod
    def add(self, posting: ApprovedTimeLaborPosting) -> None: ...

    @abstractmethod
    def get_latest(self, time_entry_id: str, *, for_update: bool = False) -> ApprovedTimeLaborPosting | None: ...

    @abstractmethod
    def flush(self) -> None: ...


__all__ = ["ApprovedTimeLaborPostingRepository"]

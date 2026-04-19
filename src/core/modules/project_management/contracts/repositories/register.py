from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from core.modules.project_management.domain.register import (
    RegisterEntry,
    RegisterEntrySeverity,
    RegisterEntryStatus,
    RegisterEntryType,
)


class RegisterEntryRepository(ABC):
    @abstractmethod
    def add(self, entry: RegisterEntry) -> None: ...

    @abstractmethod
    def update(self, entry: RegisterEntry) -> None: ...

    @abstractmethod
    def delete(self, entry_id: str) -> None: ...

    @abstractmethod
    def get(self, entry_id: str) -> Optional[RegisterEntry]: ...

    @abstractmethod
    def list_entries(
        self,
        *,
        project_id: str | None = None,
        entry_type: RegisterEntryType | None = None,
        status: RegisterEntryStatus | None = None,
        severity: RegisterEntrySeverity | None = None,
    ) -> List[RegisterEntry]: ...

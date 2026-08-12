from __future__ import annotations

from abc import ABC, abstractmethod

from src.core.modules.project_management.domain.financials.billing_preparation import (
    BillableSourceType,
    ProjectBillingExternalEvent,
    ProjectBillingPreparation,
    ProjectBillingPreparationLine,
    ProjectBillingSourceLock,
)
from src.core.modules.project_management.domain.financials.billing_profile import (
    ProjectBillingProfile,
    ProjectBillingScheduleLine,
)


class ProjectBillingRepository(ABC):
    @abstractmethod
    def add_profile(self, profile: ProjectBillingProfile) -> None: ...

    @abstractmethod
    def get_profile(self, project_id: str) -> ProjectBillingProfile | None: ...

    @abstractmethod
    def update_profile(
        self, profile: ProjectBillingProfile, *, expected_row_version: int
    ) -> None: ...

    @abstractmethod
    def add_schedule_line(self, line: ProjectBillingScheduleLine) -> None: ...

    @abstractmethod
    def get_schedule_line(self, line_id: str) -> ProjectBillingScheduleLine | None: ...

    @abstractmethod
    def list_schedule_lines(self, project_id: str) -> list[ProjectBillingScheduleLine]: ...

    @abstractmethod
    def update_schedule_line(
        self, line: ProjectBillingScheduleLine, *, expected_row_version: int
    ) -> None: ...

    @abstractmethod
    def add_preparation(self, preparation: ProjectBillingPreparation) -> None: ...

    @abstractmethod
    def get_preparation(self, preparation_id: str) -> ProjectBillingPreparation | None: ...

    @abstractmethod
    def get_preparation_by_idempotency_key(
        self, idempotency_key: str
    ) -> ProjectBillingPreparation | None: ...

    @abstractmethod
    def list_preparations(
        self, project_id: str, *, offset: int = 0, limit: int = 50
    ) -> tuple[list[ProjectBillingPreparation], int]: ...

    @abstractmethod
    def update_preparation(
        self, preparation: ProjectBillingPreparation, *, expected_row_version: int
    ) -> None: ...

    @abstractmethod
    def reserve_source(
        self,
        line: ProjectBillingPreparationLine,
        source_lock: ProjectBillingSourceLock,
    ) -> None: ...

    @abstractmethod
    def list_preparation_lines(
        self, preparation_id: str
    ) -> list[ProjectBillingPreparationLine]: ...

    @abstractmethod
    def get_source_lock(
        self, *, source_type: BillableSourceType, source_id: str
    ) -> ProjectBillingSourceLock | None: ...

    @abstractmethod
    def list_source_locks(self, preparation_id: str) -> list[ProjectBillingSourceLock]: ...

    @abstractmethod
    def update_source_lock(self, source_lock: ProjectBillingSourceLock) -> None: ...

    @abstractmethod
    def add_external_event(self, event: ProjectBillingExternalEvent) -> None: ...

    @abstractmethod
    def get_external_event_by_idempotency_key(
        self, *, external_system: str, idempotency_key: str
    ) -> ProjectBillingExternalEvent | None: ...

    @abstractmethod
    def list_external_events(
        self, preparation_id: str
    ) -> list[ProjectBillingExternalEvent]: ...

    @abstractmethod
    def list_latest_external_events(
        self, preparation_ids: tuple[str, ...]
    ) -> dict[str, ProjectBillingExternalEvent]: ...

    @abstractmethod
    def flush(self) -> None: ...


__all__ = ["ProjectBillingRepository"]

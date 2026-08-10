from __future__ import annotations

from abc import ABC, abstractmethod

from src.core.modules.project_management.domain.financials.legacy_migration import (
    LegacyCostMigrationItem,
    LegacyCostMigrationPurpose,
    LegacyCostMigrationRun,
)


class LegacyCostMigrationRepository(ABC):
    @abstractmethod
    def add_run(self, run: LegacyCostMigrationRun) -> None: ...

    @abstractmethod
    def update_run(self, run: LegacyCostMigrationRun) -> None: ...

    @abstractmethod
    def get_item(
        self, legacy_cost_item_id: str, purpose: LegacyCostMigrationPurpose
    ) -> LegacyCostMigrationItem | None: ...

    @abstractmethod
    def save_item(self, item: LegacyCostMigrationItem) -> None: ...

    @abstractmethod
    def list_items_for_project(self, project_id: str) -> list[LegacyCostMigrationItem]: ...


__all__ = ["LegacyCostMigrationRepository"]

from typing import Protocol

from src.core.modules.project_management.domain.financials.accounting.handoff import AccountingHandoffSnapshot


class AccountingHandoffRepository(Protocol):
    def get_for_preparation(self, project_id: str, preparation_id: str) -> AccountingHandoffSnapshot | None: ...

    def add(self, snapshot: AccountingHandoffSnapshot) -> None: ...

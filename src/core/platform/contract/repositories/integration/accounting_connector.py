from typing import Protocol

from src.core.platform.domain.integration.accounting.connector import AccountingConnectorConfiguration


class AccountingConnectorRepository(Protocol):
    def get(self, *, for_update: bool = False) -> AccountingConnectorConfiguration | None: ...

    def save(self, configuration: AccountingConnectorConfiguration, *, expected_version: int | None) -> None: ...

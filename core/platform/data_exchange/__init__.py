from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.platform.data_exchange.service import MasterDataExchangeService

__all__ = ["MasterDataExchangeService"]


def __getattr__(name: str):
    if name == "MasterDataExchangeService":
        from core.platform.data_exchange.service import MasterDataExchangeService

        return MasterDataExchangeService
    raise AttributeError(name)

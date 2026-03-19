from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.platform.party.domain import Party, PartyType
    from core.platform.party.service import PartyService

__all__ = ["Party", "PartyService", "PartyType"]


def __getattr__(name: str):
    if name == "Party":
        from core.platform.party.domain import Party

        return Party
    if name == "PartyType":
        from core.platform.party.domain import PartyType

        return PartyType
    if name == "PartyService":
        from core.platform.party.service import PartyService

        return PartyService
    raise AttributeError(name)

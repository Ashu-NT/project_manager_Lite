from __future__ import annotations

from src.core.platform.auth.authorization import require_permission
from src.core.platform.org.domain import Site
from src.core.platform.org import SiteService
from src.core.platform.party import PartyService
from src.core.platform.party.domain import Party, PartyType

_DEFAULT_BUSINESS_PARTY_TYPES = (
    PartyType.SUPPLIER,
    PartyType.MANUFACTURER,
    PartyType.VENDOR,
    PartyType.CONTRACTOR,
    PartyType.SERVICE_PROVIDER,
)


class InventoryReferenceService:
    def __init__(
        self,
        *,
        site_service: SiteService,
        party_service: PartyService,
        user_session=None,
    ):
        self._site_service = site_service
        self._party_service = party_service
        self._user_session = user_session

    def list_sites(self, *, active_only: bool | None = True) -> list[Site]:
        self._require_inventory_read("list inventory reference sites")
        return self._site_service.list_sites(active_only=active_only)

    def search_sites(
        self,
        *,
        search_text: str = "",
        active_only: bool | None = True,
    ) -> list[Site]:
        self._require_inventory_read("search inventory reference sites")
        return self._site_service.search_sites(search_text=search_text, active_only=active_only)

    def get_site(self, site_id: str) -> Site:
        self._require_inventory_read("view inventory reference site")
        return self._site_service.get_site(site_id)

    def list_business_parties(
        self,
        *,
        active_only: bool | None = True,
        party_types: tuple[PartyType, ...] = _DEFAULT_BUSINESS_PARTY_TYPES,
    ) -> list[Party]:
        self._require_inventory_read("list inventory business parties")
        allowed_types = set(party_types)
        return [
            party
            for party in self._party_service.list_parties(active_only=active_only)
            if party.party_type in allowed_types
        ]

    def search_business_parties(
        self,
        *,
        search_text: str = "",
        active_only: bool | None = True,
        party_types: tuple[PartyType, ...] = _DEFAULT_BUSINESS_PARTY_TYPES,
    ) -> list[Party]:
        self._require_inventory_read("search inventory business parties")
        normalized_search = (search_text or "").strip().lower()
        rows = self.list_business_parties(active_only=active_only, party_types=party_types)
        if not normalized_search:
            return rows
        return [
            party
            for party in rows
            if normalized_search in " ".join(
                filter(
                    None,
                    [
                        party.party_code,
                        party.party_name,
                        party.party_type.value,
                        party.legal_name,
                        party.contact_name,
                        party.country,
                        party.city,
                    ],
                )
            ).lower()
        ]

    def get_party(self, party_id: str) -> Party:
        self._require_inventory_read("view inventory business party")
        party = self._party_service.get_party(party_id)
        if party.party_type not in set(_DEFAULT_BUSINESS_PARTY_TYPES):
            raise ValueError("Party is not in the inventory business-party scope.")
        return party

    def _require_inventory_read(self, operation_label: str) -> None:
        require_permission(self._user_session, "inventory.read", operation_label=operation_label)


__all__ = ["InventoryReferenceService"]

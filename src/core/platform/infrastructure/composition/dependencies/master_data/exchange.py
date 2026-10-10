"""Build Platform master-data import/export coordination."""

from __future__ import annotations

from src.core.platform.application.master_data.data_exchange import (
    MasterDataExchangeService,
)
from src.core.platform.application.master_data.party.party_service import PartyService
from src.core.platform.application.master_data.site.site_service import SiteService
from src.core.platform.domain.security.auth.session import UserSessionContext


def build_master_data_exchange_service(
    *,
    site_service: SiteService,
    party_service: PartyService,
    user_session: UserSessionContext,
) -> MasterDataExchangeService:
    return MasterDataExchangeService(
        site_service=site_service,
        party_service=party_service,
        user_session=user_session,
    )

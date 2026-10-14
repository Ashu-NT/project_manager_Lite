"""Build Platform master-data import/export coordination."""

from __future__ import annotations

from src.core.platform.application.master_data.data_exchange import (
    MasterDataExchangeService,
)
from src.core.platform.application.master_data.party import (
    PartyCommandHandler,
    PartyQueryHandler,
)
from src.core.platform.application.master_data.site import (
    SiteCommandHandler,
    SiteQueryHandler,
)
from src.core.platform.domain.security.auth.session import UserSessionContext


def build_master_data_exchange_service(
    *,
    site_commands: SiteCommandHandler,
    site_query: SiteQueryHandler,
    party_commands: PartyCommandHandler,
    party_query: PartyQueryHandler,
    user_session: UserSessionContext,
) -> MasterDataExchangeService:
    return MasterDataExchangeService(
        site_commands=site_commands,
        site_query=site_query,
        party_commands=party_commands,
        party_query=party_query,
        user_session=user_session,
    )

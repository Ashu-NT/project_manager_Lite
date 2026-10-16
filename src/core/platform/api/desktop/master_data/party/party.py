from __future__ import annotations

from src.core.platform.api.desktop.models.common import DesktopApiResult
from src.core.platform.api.desktop.support._support import (
    execute_desktop_operation,
)
from src.core.platform.application.master_data.org.dto.responses.organization import (
    OrganizationDto,
)
from src.core.platform.application.master_data.party import (
    PartyCommandHandler,
    PartyQueryHandler,
)
from src.core.platform.application.master_data.party.dto.commands.party import (
    PartyCreateCommand,
    PartyUpdateCommand,
)
from src.core.platform.application.master_data.party.dto.responses.party import (
    PartyDto,
    PartyPageDto,
)
from src.core.platform.contract.read.overview.platform_overview_rollup_reader import (
    PartyRollupSummary,
)


class PlatformPartyDesktopApi:
    """Desktop-facing adapter for platform party master data."""

    def __init__(
        self,
        *,
        party_commands: PartyCommandHandler,
        party_query: PartyQueryHandler,
    ) -> None:
        self._party_commands = party_commands
        self._party_query = party_query

    def get_context(self) -> DesktopApiResult[OrganizationDto]:
        return execute_desktop_operation(
            lambda: self._party_query.get_context_organization()
        )

    def list_parties(
        self,
        *,
        active_only: bool | None = None,
    ) -> DesktopApiResult[tuple[PartyDto, ...]]:
        return execute_desktop_operation(
            lambda: tuple(
                party
                for party in self._party_query.list_parties(active_only=active_only)
            )
        )

    def list_parties_page_for_organization(
        self,
        organization_id: str,
        *,
        page: int = 1,
        page_size: int = 25,
        search: str = "",
        active_only: bool | None = None,
        party_type: str | None = None,
        role: str | None = None,
    ) -> DesktopApiResult[PartyPageDto]:
        return execute_desktop_operation(
            lambda: self._party_query.list_parties_page_for_organization(
                    organization_id,
                    page=page,
                    page_size=page_size,
                    search=search,
                    active_only=active_only,
                    party_type=party_type,
                    role=role,
                )
        )

    def get_party_rollup_summary(self) -> DesktopApiResult[PartyRollupSummary]:
        return execute_desktop_operation(
            lambda: self._party_query.get_party_rollup_summary()
        )

    def create_party(self, command: PartyCreateCommand) -> DesktopApiResult[PartyDto]:
        return execute_desktop_operation(
            lambda: self._party_commands.create_party(command)
        )

    def update_party(self, command: PartyUpdateCommand) -> DesktopApiResult[PartyDto]:
        return execute_desktop_operation(
            lambda: self._party_commands.update_party(command)
        )

    def activate_party(self, party_id: str) -> DesktopApiResult[PartyDto]:
        return execute_desktop_operation(
            lambda: self._party_commands.activate_party(party_id)
        )

    def deactivate_party(self, party_id: str) -> DesktopApiResult[PartyDto]:
        return execute_desktop_operation(
            lambda: self._party_commands.deactivate_party(party_id)
        )





__all__ = ["PlatformPartyDesktopApi"]

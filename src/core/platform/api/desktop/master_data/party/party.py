from __future__ import annotations

from src.core.platform.api.desktop.master_data.org.models.organization import (
    OrganizationDto,
)
from src.core.platform.api.desktop.master_data.party.models.party import (
    PartyDto,
    PartyPageDto,
    PartyRollupSummaryDto,
)
from src.core.platform.api.desktop.models.common import DesktopApiResult
from src.core.platform.api.desktop.support._support import (
    execute_desktop_operation,
    serialize_organization,
)
from src.core.platform.application.master_data.party import (
    PartyCommandHandler,
    PartyQueryHandler,
)
from src.core.platform.application.master_data.party.dto.commands.party import (
    PartyCreateCommand,
    PartyUpdateCommand,
)
from src.core.platform.domain.master_data.party import Party


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
            lambda: serialize_organization(self._party_query.get_context_organization())
        )

    def list_parties(
        self,
        *,
        active_only: bool | None = None,
    ) -> DesktopApiResult[tuple[PartyDto, ...]]:
        return execute_desktop_operation(
            lambda: tuple(
                self._serialize_party(party)
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
            lambda: self._serialize_party_page(
                self._party_query.list_parties_page_for_organization(
                    organization_id,
                    page=page,
                    page_size=page_size,
                    search=search,
                    active_only=active_only,
                    party_type=party_type,
                    role=role,
                )
            )
        )

    def get_party_rollup_summary(self) -> DesktopApiResult[PartyRollupSummaryDto]:
        return execute_desktop_operation(
            lambda: self._serialize_rollup_summary(
                self._party_query.get_party_rollup_summary()
            )
        )

    def create_party(self, command: PartyCreateCommand) -> DesktopApiResult[PartyDto]:
        return execute_desktop_operation(
            lambda: self._serialize_party(
                self._party_commands.create_party(command)
            )
        )

    def update_party(self, command: PartyUpdateCommand) -> DesktopApiResult[PartyDto]:
        return execute_desktop_operation(
            lambda: self._serialize_party(
                self._party_commands.update_party(command)
            )
        )

    def activate_party(self, party_id: str) -> DesktopApiResult[PartyDto]:
        return execute_desktop_operation(
            lambda: self._serialize_party(self._party_commands.activate_party(party_id))
        )

    def deactivate_party(self, party_id: str) -> DesktopApiResult[PartyDto]:
        return execute_desktop_operation(
            lambda: self._serialize_party(self._party_commands.deactivate_party(party_id))
        )

    @staticmethod
    def _serialize_rollup_summary(summary) -> PartyRollupSummaryDto:
        return PartyRollupSummaryDto(total=summary.total, active=summary.active)

    def _serialize_party_page(self, page) -> PartyPageDto:
        return PartyPageDto(
            items=tuple(self._serialize_party(party) for party in page.items),
            total=page.total,
            filtered_total=page.filtered_total,
            page=page.page,
            page_size=page.page_size,
        )

    @staticmethod
    def _serialize_party(party: Party) -> PartyDto:
        return PartyDto(
            id=party.id,
            organization_id=party.organization_id,
            party_code=party.party_code,
            party_name=party.party_name,
            party_type=party.party_type,
            roles=party.roles,
            legal_name=party.legal_name,
            contact_name=party.contact_name,
            email=party.email,
            phone=party.phone,
            country=party.country,
            city=party.city,
            address_line_1=party.address_line_1,
            address_line_2=party.address_line_2,
            postal_code=party.postal_code,
            website=party.website,
            registration_number=party.registration_number,
            tax_identifier=party.tax_identifier,
            external_reference=party.external_reference,
            status=party.status.value,
            is_active=party.is_active,
            created_at=party.created_at,
            updated_at=party.updated_at,
            notes=party.notes,
            version=party.version,
        )


__all__ = ["PlatformPartyDesktopApi"]

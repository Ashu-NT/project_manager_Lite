from __future__ import annotations

from src.api.desktop.platform._support import execute_desktop_operation, serialize_organization
from src.api.desktop.platform.models import (
    DesktopApiResult,
    OrganizationDto,
    PartyCreateCommand,
    PartyDto,
    PartyUpdateCommand,
)
from src.core.platform.party import PartyService
from src.core.platform.party.domain import Party


class PlatformPartyDesktopApi:
    """Desktop-facing adapter for platform party master data."""

    def __init__(self, *, party_service: PartyService) -> None:
        self._party_service = party_service

    def get_context(self) -> DesktopApiResult[OrganizationDto]:
        return execute_desktop_operation(
            lambda: serialize_organization(self._party_service.get_context_organization())
        )

    def list_parties(
        self,
        *,
        active_only: bool | None = None,
    ) -> DesktopApiResult[tuple[PartyDto, ...]]:
        return execute_desktop_operation(
            lambda: tuple(
                self._serialize_party(party)
                for party in self._party_service.list_parties(active_only=active_only)
            )
        )

    def create_party(self, command: PartyCreateCommand) -> DesktopApiResult[PartyDto]:
        return execute_desktop_operation(
            lambda: self._serialize_party(
                self._party_service.create_party(
                    party_code=command.party_code,
                    party_name=command.party_name,
                    party_type=command.party_type,
                    legal_name=command.legal_name,
                    contact_name=command.contact_name,
                    email=command.email,
                    phone=command.phone,
                    country=command.country,
                    city=command.city,
                    address_line_1=command.address_line_1,
                    address_line_2=command.address_line_2,
                    postal_code=command.postal_code,
                    website=command.website,
                    tax_registration_number=command.tax_registration_number,
                    external_reference=command.external_reference,
                    is_active=command.is_active,
                    notes=command.notes,
                )
            )
        )

    def update_party(self, command: PartyUpdateCommand) -> DesktopApiResult[PartyDto]:
        return execute_desktop_operation(
            lambda: self._serialize_party(
                self._party_service.update_party(
                    command.party_id,
                    party_code=command.party_code,
                    party_name=command.party_name,
                    party_type=command.party_type,
                    legal_name=command.legal_name,
                    contact_name=command.contact_name,
                    email=command.email,
                    phone=command.phone,
                    country=command.country,
                    city=command.city,
                    address_line_1=command.address_line_1,
                    address_line_2=command.address_line_2,
                    postal_code=command.postal_code,
                    website=command.website,
                    tax_registration_number=command.tax_registration_number,
                    external_reference=command.external_reference,
                    is_active=command.is_active,
                    notes=command.notes,
                    expected_version=command.expected_version,
                )
            )
        )

    @staticmethod
    def _serialize_party(party: Party) -> PartyDto:
        return PartyDto(
            id=party.id,
            organization_id=party.organization_id,
            party_code=party.party_code,
            party_name=party.party_name,
            party_type=party.party_type,
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
            tax_registration_number=party.tax_registration_number,
            external_reference=party.external_reference,
            is_active=party.is_active,
            created_at=party.created_at,
            updated_at=party.updated_at,
            notes=party.notes,
            version=party.version,
        )


__all__ = ["PlatformPartyDesktopApi"]

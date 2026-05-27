from __future__ import annotations

from typing import Any

from src.api.desktop.platform import (
    PartyCreateCommand,
    PartyDto,
    PartyUpdateCommand,
    PlatformPartyDesktopApi,
)
from src.api.desktop.platform.models import DesktopApiResult
from src.core.platform.party.domain import PartyType
from src.ui_qml.platform.presenters.support import (
    bool_value,
    option_item,
    optional_string_value,
    preview_error_result,
    string_value,
    title_case_code,
)
from src.ui_qml.platform.view_models import (
    PlatformWorkspaceActionItemViewModel,
    PlatformWorkspaceActionListViewModel,
)


class PlatformPartyCatalogPresenter:
    def __init__(self, *, party_api: PlatformPartyDesktopApi | None = None) -> None:
        self._party_api = party_api

    def build_catalog(self) -> PlatformWorkspaceActionListViewModel:
        if self._party_api is None:
            return PlatformWorkspaceActionListViewModel(
                title="Parties",
                subtitle="Shared supplier and partner records appear here once the platform party API is connected.",
                empty_state="Platform party API is not connected in this QML preview.",
            )

        context_result = self._party_api.get_context()
        parties_result = self._party_api.list_parties(active_only=None)
        if not parties_result.ok or parties_result.data is None:
            message = parties_result.error.message if parties_result.error is not None else "Unable to load parties."
            return PlatformWorkspaceActionListViewModel(
                title="Parties",
                subtitle=message,
                empty_state=message,
            )

        context_label = (
            context_result.data.display_name
            if context_result.ok and context_result.data is not None
            else "Context unavailable"
        )
        return PlatformWorkspaceActionListViewModel(
            title="Parties",
            subtitle=f"Shared supplier, contractor, and partner master data for {context_label}.",
            empty_state="No parties are available yet.",
            items=tuple(self._serialize_party(row) for row in parties_result.data),
        )

    def build_type_options(self) -> tuple[dict[str, str], ...]:
        return tuple(
            option_item(
                label=title_case_code(party_type),
                value=party_type.value,
            )
            for party_type in PartyType
        )

    def create_party(self, payload: dict[str, Any]) -> DesktopApiResult[PartyDto]:
        if self._party_api is None:
            return preview_error_result("Platform party API is not connected in this QML preview.")
        return self._party_api.create_party(
            PartyCreateCommand(
                party_code=string_value(payload, "partyCode"),
                party_name=string_value(payload, "partyName"),
                party_type=string_value(payload, "partyType", default=PartyType.GENERAL.value),
                legal_name=string_value(payload, "legalName"),
                contact_name=string_value(payload, "contactName"),
                email=optional_string_value(payload, "email"),
                phone=optional_string_value(payload, "phone"),
                country=string_value(payload, "country"),
                city=string_value(payload, "city"),
                address_line_1=string_value(payload, "addressLine1"),
                address_line_2=string_value(payload, "addressLine2"),
                postal_code=string_value(payload, "postalCode"),
                website=string_value(payload, "website"),
                tax_registration_number=string_value(payload, "taxRegistrationNumber"),
                external_reference=string_value(payload, "externalReference"),
                is_active=bool_value(payload, "isActive", default=True),
                notes=string_value(payload, "notes"),
            )
        )

    def update_party(self, payload: dict[str, Any]) -> DesktopApiResult[PartyDto]:
        if self._party_api is None:
            return preview_error_result("Platform party API is not connected in this QML preview.")
        return self._party_api.update_party(
            PartyUpdateCommand(
                party_id=string_value(payload, "partyId"),
                party_code=string_value(payload, "partyCode"),
                party_name=string_value(payload, "partyName"),
                party_type=string_value(payload, "partyType", default=PartyType.GENERAL.value),
                legal_name=string_value(payload, "legalName"),
                contact_name=string_value(payload, "contactName"),
                email=optional_string_value(payload, "email"),
                phone=optional_string_value(payload, "phone"),
                country=string_value(payload, "country"),
                city=string_value(payload, "city"),
                address_line_1=string_value(payload, "addressLine1"),
                address_line_2=string_value(payload, "addressLine2"),
                postal_code=string_value(payload, "postalCode"),
                website=string_value(payload, "website"),
                tax_registration_number=string_value(payload, "taxRegistrationNumber"),
                external_reference=string_value(payload, "externalReference"),
                is_active=bool_value(payload, "isActive", default=True),
                notes=string_value(payload, "notes"),
            )
        )

    def toggle_party_active(
        self,
        *,
        party_id: str,
        is_active: bool,
        expected_version: int | None,
    ) -> DesktopApiResult[PartyDto]:
        if self._party_api is None:
            return preview_error_result("Platform party API is not connected in this QML preview.")
        return self._party_api.update_party(
            PartyUpdateCommand(
                party_id=party_id,
                is_active=not is_active,
                expected_version=expected_version,
            )
        )

    @staticmethod
    def _serialize_party(row: PartyDto) -> PlatformWorkspaceActionItemViewModel:
        contact_label = row.contact_name or row.email or row.phone or "No contact details"
        return PlatformWorkspaceActionItemViewModel(
            id=row.id,
            title=row.party_name,
            status_label="Active" if row.is_active else "Inactive",
            subtitle=f"{row.party_code} | {title_case_code(row.party_type)}",
            supporting_text=f"{contact_label} | {row.city or '-'}, {row.country or '-'}",
            meta_text=row.legal_name or row.website or "Shared platform party record",
            can_primary_action=True,
            can_secondary_action=True,
            state={
                "id": row.id,
                "partyId": row.id,
                "partyCode": row.party_code,
                "partyName": row.party_name,
                "partyType": getattr(row.party_type, "value", row.party_type),
                "legalName": row.legal_name,
                "contactName": row.contact_name,
                "email": row.email,
                "phone": row.phone,
                "country": row.country,
                "city": row.city,
                "addressLine1": row.address_line_1,
                "addressLine2": row.address_line_2,
                "postalCode": row.postal_code,
                "website": row.website,
                "taxRegistrationNumber": row.tax_registration_number,
                "externalReference": row.external_reference,
                "notes": row.notes,
                "isActive": row.is_active,
                "version": row.version,
            },
        )


__all__ = ["PlatformPartyCatalogPresenter"]

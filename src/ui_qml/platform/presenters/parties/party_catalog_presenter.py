from __future__ import annotations

from typing import Any

from src.core.platform.api.desktop.master_data.party.models.party import (
    PartyCreateCommand,
    PartyDto,
    PartyUpdateCommand,
)
from src.core.platform.api.desktop.master_data.party.party import (
    PlatformPartyDesktopApi,
)
from src.core.platform.api.desktop.models.common import DesktopApiResult
from src.core.platform.domain.master_data.party import PartyRole, PartyType
from src.ui_qml.platform.presenters.common.presenter_support_helpers import (
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

_DEFAULT_PARTY_PAGE_SIZE = 25
PARTY_PAGE_SIZE_OPTIONS: tuple[int, ...] = (25, 50, 100)

# Party lifecycle is a plain 2-state ACTIVE/INACTIVE model (PartyLifecycleStatus)
# -- the same tone shape Employee's own 2-state status label uses.
_PARTY_STATUS_TONE = {True: "success", False: "neutral"}


def _party_status_label(is_active: bool) -> dict[str, str]:
    return {"label": "Active" if is_active else "Inactive", "tone": _PARTY_STATUS_TONE[is_active]}


def _roles_label(roles: tuple[PartyRole, ...]) -> str:
    """Human-readable, compact roles summary for the table column and
    Inspector -- e.g. "Supplier, Customer" or "Supplier, Customer +2" once
    the role count gets large enough to crowd a row. Never raw enum
    formatting (SERVICE_PROVIDER)."""
    if not roles:
        return ""
    labels = [title_case_code(role) for role in roles]
    if len(labels) <= 3:
        return ", ".join(labels)
    return ", ".join(labels[:2]) + f" +{len(labels) - 2}"


class PlatformPartyCatalogPresenter:
    def __init__(self, *, party_api: PlatformPartyDesktopApi | None = None) -> None:
        self._party_api = party_api

    def build_catalog(self) -> PlatformWorkspaceActionListViewModel:
        if self._party_api is None:
            return PlatformWorkspaceActionListViewModel(
                title="Parties",
                subtitle="Shared external party and counterparty master data for the organization.",
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
            subtitle=f"Shared external party and counterparty master data for {context_label}.",
            empty_state="No parties are available yet.",
            items=tuple(self._serialize_party(row) for row in parties_result.data),
        )

    def build_catalog_page(
        self,
        *,
        page: int = 1,
        page_size: int = _DEFAULT_PARTY_PAGE_SIZE,
        search: str = "",
        status: str = "",
        party_type: str = "",
        role: str = "",
    ) -> PlatformWorkspaceActionListViewModel:
        """Server-side paginated Parties page for the primary Platform >
        Parties destination, scoped to the caller's currently active
        organization -- mirrors Employee's own build_catalog_page exactly.
        Never loads the full Party table and filters in QML."""
        if self._party_api is None:
            return PlatformWorkspaceActionListViewModel(
                title="Parties",
                subtitle="Parties appear here once the platform party API is connected.",
                empty_state="Platform party API is not connected in this QML preview.",
                paginated=True,
                page=page,
                page_size=page_size,
            )
        context_result = self._party_api.get_context()
        if not context_result.ok or context_result.data is None:
            message = context_result.error.message if context_result.error is not None else "Unable to load parties."
            return PlatformWorkspaceActionListViewModel(
                title="Parties",
                subtitle=message,
                empty_state=message,
                paginated=True,
                page=page,
                page_size=page_size,
            )

        organization_id = context_result.data.id
        active_only: bool | None
        if status == "active":
            active_only = True
        elif status == "inactive":
            active_only = False
        else:
            active_only = None

        result = self._party_api.list_parties_page_for_organization(
            organization_id,
            page=page,
            page_size=page_size,
            search=search.strip(),
            active_only=active_only,
            party_type=party_type or None,
            role=role or None,
        )
        if not result.ok or result.data is None:
            message = result.error.message if result.error is not None else "Unable to load parties."
            return PlatformWorkspaceActionListViewModel(
                title="Parties",
                subtitle=message,
                empty_state=message,
                paginated=True,
                page=page,
                page_size=page_size,
            )

        party_page = result.data
        return PlatformWorkspaceActionListViewModel(
            title="Parties",
            subtitle=f"Shared external party and counterparty master data for {context_result.data.display_name}.",
            empty_state="No parties yet. Create the first party for this organization.",
            no_results_state="No parties match your current filters.",
            items=tuple(self._serialize_party(row) for row in party_page.items),
            paginated=True,
            page=party_page.page,
            page_size=party_page.page_size,
            total_count=party_page.total,
            filtered_total=party_page.filtered_total,
        )

    def build_type_options(self) -> tuple[dict[str, str], ...]:
        return tuple(
            option_item(
                label=title_case_code(party_type),
                value=party_type.value,
            )
            for party_type in PartyType
        )

    def build_role_options(self) -> tuple[dict[str, str], ...]:
        return tuple(
            option_item(
                label=title_case_code(role),
                value=role.value,
            )
            for role in PartyRole
        )

    def suggest_code(self, payload: dict[str, Any]) -> str:
        """Suggest a unique party code (PTY-<NAME>-0001 / PTY-<YEAR>-0001)."""
        from src.core.platform.common.code_generation import CodeGenerator

        existing: set[str] = set()
        if self._party_api is not None:
            result = self._party_api.list_parties(active_only=None)
            if result.ok and result.data is not None:
                existing = {str(getattr(row, "party_code", "") or "").upper() for row in result.data}
        name = string_value(payload, "partyName")
        return CodeGenerator().generate(
            "party",
            exists=lambda code: code.upper() in existing,
            name=name or None,
            use_year=not bool(name),
        )

    def create_party(self, payload: dict[str, Any]) -> DesktopApiResult[PartyDto]:
        if self._party_api is None:
            return preview_error_result("Platform party API is not connected in this QML preview.")
        return self._party_api.create_party(
            PartyCreateCommand(
                party_code=string_value(payload, "partyCode"),
                party_name=string_value(payload, "partyName"),
                party_type=string_value(payload, "partyType", default=PartyType.ORGANIZATION.value),
                roles=self._roles_value(payload),
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
                registration_number=string_value(payload, "registrationNumber"),
                tax_identifier=string_value(payload, "taxIdentifier"),
                external_reference=string_value(payload, "externalReference"),
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
                party_type=string_value(payload, "partyType", default=PartyType.ORGANIZATION.value),
                roles=self._roles_value(payload),
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
                registration_number=string_value(payload, "registrationNumber"),
                tax_identifier=string_value(payload, "taxIdentifier"),
                external_reference=string_value(payload, "externalReference"),
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
        # expected_version isn't honored here -- activate_party/deactivate_party
        # are the real lifecycle commands and don't take an optimistic-lock
        # token (they reject same-state transitions instead); kept as a
        # parameter only for call-site compatibility.
        if self._party_api is None:
            return preview_error_result("Platform party API is not connected in this QML preview.")
        if is_active:
            return self._party_api.deactivate_party(party_id)
        return self._party_api.activate_party(party_id)

    def activate_party(self, party_id: str) -> DesktopApiResult[PartyDto]:
        if self._party_api is None:
            return preview_error_result("Platform party API is not connected in this QML preview.")
        return self._party_api.activate_party(party_id)

    def deactivate_party(self, party_id: str) -> DesktopApiResult[PartyDto]:
        if self._party_api is None:
            return preview_error_result("Platform party API is not connected in this QML preview.")
        return self._party_api.deactivate_party(party_id)

    @staticmethod
    def _roles_value(payload: dict[str, Any]) -> list[str]:
        raw = payload.get("roles", [])
        if raw is None:
            return []
        if isinstance(raw, str):
            return [part.strip() for part in raw.split(",") if part.strip()]
        return [str(item).strip() for item in raw if str(item).strip()]

    @staticmethod
    def _serialize_party(row: PartyDto) -> PlatformWorkspaceActionItemViewModel:
        contact_label = row.contact_name or row.email or row.phone or "No contact details"
        roles_label = _roles_label(row.roles)
        return PlatformWorkspaceActionItemViewModel(
            id=row.id,
            title=row.party_name,
            status_label=_party_status_label(row.is_active),
            subtitle=row.party_code,
            supporting_text=f"{contact_label} | {row.city or '-'}, {row.country or '-'}",
            meta_text=roles_label or row.legal_name or "Shared platform party record",
            can_primary_action=True,
            can_secondary_action=True,
            state={
                "id": row.id,
                "partyId": row.id,
                "partyCode": row.party_code,
                "partyName": row.party_name,
                "partyType": getattr(row.party_type, "value", row.party_type),
                "partyTypeLabel": title_case_code(row.party_type),
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
                "roles": [role.value for role in row.roles],
                "rolesLabel": roles_label,
                "registrationNumber": row.registration_number,
                "taxIdentifier": row.tax_identifier,
                "externalReference": row.external_reference,
                "notes": row.notes,
                "status": row.status,
                "isActive": row.is_active,
                "updatedAt": row.updated_at.strftime("%d %b %Y") if row.updated_at else "",
                "version": row.version,
            },
        )

__all__ = ["PARTY_PAGE_SIZE_OPTIONS", "PlatformPartyCatalogPresenter"]

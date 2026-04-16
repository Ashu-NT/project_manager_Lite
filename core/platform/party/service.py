from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.platform.audit.helpers import record_audit
from src.core.platform.auth.authorization import require_any_permission, require_permission
from core.platform.common.exceptions import ConcurrencyError, NotFoundError, ValidationError
from core.platform.common.interfaces import OrganizationRepository
from core.platform.org.domain import Organization
from core.platform.notifications.domain_events import domain_events
from core.platform.org.support import normalize_code, normalize_email, normalize_name, normalize_phone
from core.platform.party.domain import Party, PartyType
from core.platform.party.interfaces import PartyRepository


def _normalize_optional_text(value: str | None) -> str:
    return (value or "").strip()


def _coerce_party_type(value: PartyType | str | None) -> PartyType:
    if isinstance(value, PartyType):
        return value
    raw = str(value or PartyType.GENERAL.value).strip().upper()
    try:
        return PartyType(raw)
    except ValueError as exc:
        raise ValidationError("Party type is invalid.", code="PARTY_TYPE_INVALID") from exc


class PartyService:
    def __init__(
        self,
        session: Session,
        party_repo: PartyRepository,
        *,
        organization_repo: OrganizationRepository,
        user_session=None,
        audit_service=None,
    ):
        self._session = session
        self._party_repo = party_repo
        self._organization_repo = organization_repo
        self._user_session = user_session
        self._audit_service = audit_service

    def list_parties(self, *, active_only: bool | None = None) -> list[Party]:
        self._require_party_read_access("list parties")
        organization = self._active_organization()
        return self._party_repo.list_for_organization(organization.id, active_only=active_only)

    def search_parties(
        self,
        *,
        search_text: str = "",
        active_only: bool | None = True,
        party_type: PartyType | str | None = None,
    ) -> list[Party]:
        self._require_party_read_access("search parties")
        normalized_search = _normalize_optional_text(search_text).lower()
        resolved_type = _coerce_party_type(party_type) if party_type is not None else None
        rows = self._party_repo.list_for_organization(self._active_organization().id, active_only=active_only)
        filtered = [party for party in rows if resolved_type is None or party.party_type == resolved_type]
        if not normalized_search:
            return filtered
        return [
            party
            for party in filtered
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
                        party.external_reference,
                    ],
                )
            ).lower()
        ]

    def get_party(self, party_id: str) -> Party:
        self._require_party_read_access("view party")
        organization = self._active_organization()
        party = self._party_repo.get(party_id)
        if party is None or party.organization_id != organization.id:
            raise NotFoundError("Party not found in the active organization.", code="PARTY_NOT_FOUND")
        return party

    def find_party_by_code(self, party_code: str) -> Party | None:
        self._require_party_read_access("resolve party")
        normalized_code = normalize_code(party_code, label="Party code")
        return self._party_repo.get_by_code(self._active_organization().id, normalized_code)

    def get_context_organization(self) -> Organization:
        require_permission(self._user_session, "settings.manage", operation_label="view party context")
        return self._active_organization()

    def create_party(
        self,
        *,
        party_code: str,
        party_name: str | None = None,
        name: str | None = None,
        party_type: PartyType | str = PartyType.GENERAL,
        legal_name: str = "",
        contact_name: str = "",
        email: str | None = None,
        phone: str | None = None,
        country: str = "",
        city: str = "",
        address_line_1: str = "",
        address_line_2: str = "",
        postal_code: str = "",
        website: str = "",
        tax_registration_number: str = "",
        external_reference: str = "",
        is_active: bool = True,
        notes: str = "",
    ) -> Party:
        require_permission(self._user_session, "settings.manage", operation_label="create party")
        organization = self._active_organization()
        normalized_code = normalize_code(party_code, label="Party code")
        normalized_name = normalize_name(party_name if party_name is not None else name, label="Party name")
        if self._party_repo.get_by_code(organization.id, normalized_code) is not None:
            raise ValidationError("Party code already exists in the active organization.", code="PARTY_CODE_EXISTS")
        party = Party.create(
            organization_id=organization.id,
            party_code=normalized_code,
            party_name=normalized_name,
            party_type=_coerce_party_type(party_type),
            legal_name=_normalize_optional_text(legal_name),
            contact_name=_normalize_optional_text(contact_name),
            email=normalize_email(email) or "",
            phone=normalize_phone(phone) or "",
            country=_normalize_optional_text(country),
            city=_normalize_optional_text(city),
            address_line_1=_normalize_optional_text(address_line_1),
            address_line_2=_normalize_optional_text(address_line_2),
            postal_code=_normalize_optional_text(postal_code),
            website=_normalize_optional_text(website),
            tax_registration_number=_normalize_optional_text(tax_registration_number),
            external_reference=_normalize_optional_text(external_reference),
            is_active=bool(is_active),
            notes=_normalize_optional_text(notes),
        )
        try:
            self._party_repo.add(party)
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            raise ValidationError("Party code already exists in the active organization.", code="PARTY_CODE_EXISTS") from exc
        except Exception:
            self._session.rollback()
            raise
        record_audit(
            self,
            action="party.create",
            entity_type="party",
            entity_id=party.id,
            details={
                "organization_id": organization.id,
                "party_code": party.party_code,
                "party_name": party.party_name,
                "party_type": party.party_type.value,
                "is_active": str(party.is_active),
            },
        )
        domain_events.parties_changed.emit(party.id)
        return party

    def update_party(
        self,
        party_id: str,
        *,
        party_code: str | None = None,
        party_name: str | None = None,
        name: str | None = None,
        party_type: PartyType | str | None = None,
        legal_name: str | None = None,
        contact_name: str | None = None,
        email: str | None = None,
        phone: str | None = None,
        country: str | None = None,
        city: str | None = None,
        address_line_1: str | None = None,
        address_line_2: str | None = None,
        postal_code: str | None = None,
        website: str | None = None,
        tax_registration_number: str | None = None,
        external_reference: str | None = None,
        is_active: bool | None = None,
        notes: str | None = None,
        expected_version: int | None = None,
    ) -> Party:
        require_permission(self._user_session, "settings.manage", operation_label="update party")
        organization = self._active_organization()
        party = self._party_repo.get(party_id)
        if party is None or party.organization_id != organization.id:
            raise NotFoundError("Party not found in the active organization.", code="PARTY_NOT_FOUND")
        if expected_version is not None and party.version != expected_version:
            raise ConcurrencyError(
                "Party changed since you opened it. Refresh and try again.",
                code="STALE_WRITE",
            )
        if party_code is not None:
            normalized_code = normalize_code(party_code, label="Party code")
            existing = self._party_repo.get_by_code(organization.id, normalized_code)
            if existing is not None and existing.id != party.id:
                raise ValidationError("Party code already exists in the active organization.", code="PARTY_CODE_EXISTS")
            party.party_code = normalized_code
        if party_name is not None or name is not None:
            party.party_name = normalize_name(
                party_name if party_name is not None else name,
                label="Party name",
            )
        if party_type is not None:
            party.party_type = _coerce_party_type(party_type)
        if legal_name is not None:
            party.legal_name = _normalize_optional_text(legal_name)
        if contact_name is not None:
            party.contact_name = _normalize_optional_text(contact_name)
        if email is not None:
            party.email = normalize_email(email) or ""
        if phone is not None:
            party.phone = normalize_phone(phone) or ""
        if country is not None:
            party.country = _normalize_optional_text(country)
        if city is not None:
            party.city = _normalize_optional_text(city)
        if address_line_1 is not None:
            party.address_line_1 = _normalize_optional_text(address_line_1)
        if address_line_2 is not None:
            party.address_line_2 = _normalize_optional_text(address_line_2)
        if postal_code is not None:
            party.postal_code = _normalize_optional_text(postal_code)
        if website is not None:
            party.website = _normalize_optional_text(website)
        if tax_registration_number is not None:
            party.tax_registration_number = _normalize_optional_text(tax_registration_number)
        if external_reference is not None:
            party.external_reference = _normalize_optional_text(external_reference)
        if is_active is not None:
            party.is_active = bool(is_active)
        if notes is not None:
            party.notes = _normalize_optional_text(notes)
        party.updated_at = datetime.now(timezone.utc)
        try:
            self._party_repo.update(party)
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            raise ValidationError("Party code already exists in the active organization.", code="PARTY_CODE_EXISTS") from exc
        except Exception:
            self._session.rollback()
            raise
        record_audit(
            self,
            action="party.update",
            entity_type="party",
            entity_id=party.id,
            details={
                "organization_id": organization.id,
                "party_code": party.party_code,
                "party_name": party.party_name,
                "party_type": party.party_type.value,
                "is_active": str(party.is_active),
            },
        )
        domain_events.parties_changed.emit(party.id)
        return party

    def _active_organization(self) -> Organization:
        organization = self._organization_repo.get_active()
        if organization is None:
            raise NotFoundError("Active organization not found.", code="ORGANIZATION_NOT_FOUND")
        return organization

    def _require_party_read_access(self, operation_label: str) -> None:
        require_any_permission(
            self._user_session,
            ("settings.manage", "party.read"),
            operation_label=operation_label,
        )


__all__ = ["PartyService"]

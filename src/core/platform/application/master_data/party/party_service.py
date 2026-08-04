from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.core.platform.application.security.authorization.enforcement.permission_checks import require_any_permission, require_permission
from src.core.platform.common.exceptions import BusinessRuleError, ConcurrencyError, NotFoundError, ValidationError
from src.core.platform.contract.master_data.org.contracts import OrganizationRepository
from src.core.platform.domain.master_data.org import Organization
from src.core.platform.contract.master_data.party.contracts import PartyRepository
from src.core.platform.domain.master_data.party import (
    Party,
    PartyType,
    coerce_party_type,
    normalize_party_code,
)
from src.core.platform.application.tenant.tenancy import TenantContextService
from src.core.shared.audit import record_audit_entry
from src.core.shared.events.domain_events import domain_events

if TYPE_CHECKING:
    from src.core.platform.application.history.audit.enterprise_audit_service import EnterpriseAuditService
    from src.core.platform.auth.domain.session import UserSessionContext


class PartyService:
    def __init__(
        self,
        session: Session,
        party_repo: PartyRepository,
        *,
        organization_repo: OrganizationRepository,
        user_session: UserSessionContext | None = None,
        enterprise_audit_service: EnterpriseAuditService | None = None,
        tenant_context_service: TenantContextService | None = None,
    ):
        self._session = session
        self._party_repo = party_repo
        self._organization_repo = organization_repo
        self._user_session = user_session
        self._enterprise_audit_service = enterprise_audit_service
        self._tenant_context_service = tenant_context_service

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
        normalized_search = (search_text or "").strip().lower()
        resolved_type = coerce_party_type(party_type) if party_type is not None else None
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
        normalized_code = normalize_party_code(party_code)
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
        party = Party.create(
            organization_id=organization.id,
            party_code=party_code,
            party_name=party_name if party_name is not None else name,
            party_type=party_type,
            legal_name=legal_name,
            contact_name=contact_name,
            email=email or "",
            phone=phone or "",
            country=country,
            city=city,
            address_line_1=address_line_1,
            address_line_2=address_line_2,
            postal_code=postal_code,
            website=website,
            tax_registration_number=tax_registration_number,
            external_reference=external_reference,
            is_active=bool(is_active),
            notes=notes,
        )
        if self._party_repo.get_by_code(organization.id, party.party_code) is not None:
            raise ValidationError("Party code already exists in the active organization.", code="PARTY_CODE_EXISTS")
        try:
            self._party_repo.add(party)
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            raise ValidationError("Party code already exists in the active organization.", code="PARTY_CODE_EXISTS") from exc
        except Exception:
            self._session.rollback()
            raise
        record_audit_entry(
            self,
            operation="create",
            entity_type="party",
            entity_id=party.id,
            module="platform",
            severity="low",
            metadata={
                "action": "party.create",
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

        candidate = replace(
            party,
            party_code=party_code if party_code is not None else party.party_code,
            party_name=(
                party_name if party_name is not None else name
                if party_name is not None or name is not None
                else party.party_name
            ),
            party_type=party_type if party_type is not None else party.party_type,
            legal_name=legal_name if legal_name is not None else party.legal_name,
            contact_name=contact_name if contact_name is not None else party.contact_name,
            email=email if email is not None else party.email,
            phone=phone if phone is not None else party.phone,
            country=country if country is not None else party.country,
            city=city if city is not None else party.city,
            address_line_1=address_line_1 if address_line_1 is not None else party.address_line_1,
            address_line_2=address_line_2 if address_line_2 is not None else party.address_line_2,
            postal_code=postal_code if postal_code is not None else party.postal_code,
            website=website if website is not None else party.website,
            tax_registration_number=(
                tax_registration_number
                if tax_registration_number is not None
                else party.tax_registration_number
            ),
            external_reference=external_reference if external_reference is not None else party.external_reference,
            is_active=bool(is_active) if is_active is not None else party.is_active,
            notes=notes if notes is not None else party.notes,
            updated_at=datetime.now(timezone.utc),
        )
        if party_code is not None:
            existing = self._party_repo.get_by_code(organization.id, candidate.party_code)
            if existing is not None and existing.id != party.id:
                raise ValidationError("Party code already exists in the active organization.", code="PARTY_CODE_EXISTS")

        try:
            self._party_repo.update(candidate)
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            raise ValidationError("Party code already exists in the active organization.", code="PARTY_CODE_EXISTS") from exc
        except Exception:
            self._session.rollback()
            raise
        record_audit_entry(
            self,
            operation="update",
            entity_type="party",
            entity_id=candidate.id,
            module="platform",
            severity="low",
            metadata={
                "action": "party.update",
                "organization_id": organization.id,
                "party_code": candidate.party_code,
                "party_name": candidate.party_name,
                "party_type": candidate.party_type.value,
                "is_active": str(candidate.is_active),
            },
        )
        domain_events.parties_changed.emit(candidate.id)
        return candidate

    def _active_organization(self) -> Organization:
        if self._tenant_context_service is None:
            raise BusinessRuleError(
                "Active organization context is required.",
                code="TENANT_CONTEXT_REQUIRED",
            )
        organization = self._tenant_context_service.get_active_organization()
        if organization is None:
            raise BusinessRuleError(
                "Active organization context is required.",
                code="TENANT_CONTEXT_REQUIRED",
            )
        return organization

    def _require_party_read_access(self, operation_label: str) -> None:
        require_any_permission(
            self._user_session,
            ("settings.manage", "party.read"),
            operation_label=operation_label,
        )


__all__ = ["PartyService"]

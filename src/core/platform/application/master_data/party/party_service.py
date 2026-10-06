from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_any_permission,
    require_permission,
)
from src.core.platform.application.tenant.tenancy import TenantContextService
from src.core.platform.common.exceptions import (
    BusinessRuleError,
    ConcurrencyError,
    NotFoundError,
    ValidationError,
)
from src.core.platform.common.ids import generate_id
from src.core.platform.contract.read.overview.platform_overview_rollup_reader import (
    PartyRollupSummary,
    PlatformOverviewRollupReader,
)
from src.core.platform.contract.repositories.master_data.org.contracts import (
    OrganizationRepository,
)
from src.core.platform.contract.repositories.master_data.party.contracts import (
    PartyRepository,
)
from src.core.platform.contract.uow.party_unit_of_work import PartyUnitOfWorkFactory
from src.core.platform.domain.master_data.org import Organization
from src.core.platform.domain.master_data.party import (
    Party,
    PartyRole,
    PartyType,
    coerce_party_type,
    normalize_party_code,
)
from src.core.platform.domain.master_data.party.events import (
    PartyCreated,
    PartyProfileUpdated,
)
from src.core.shared.activity import record_activity
from src.core.shared.audit import record_audit_entry
from src.core.shared.events.domain_event_context import DomainEventContext
from src.core.shared.time.clock import Clock

from . import party_commands as _cmd

_DEFAULT_PARTY_PAGE_SIZE = 25
PARTY_PAGE_SIZE_OPTIONS: tuple[int, ...] = (25, 50, 100)


@dataclass(frozen=True)
class PartyPage:
    items: list[Party] = field(default_factory=list)
    total: int = 0
    filtered_total: int = 0
    page: int = 1
    page_size: int = _DEFAULT_PARTY_PAGE_SIZE

if TYPE_CHECKING:
    from src.core.platform.application.history.audit.enterprise_audit_service import (
        EnterpriseAuditService,
    )
    from src.core.platform.domain.security.auth.session import UserSessionContext


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
        overview_rollup_reader: PlatformOverviewRollupReader | None = None,
        uow_factory: PartyUnitOfWorkFactory,
        clock: Clock,
    ):
        self._session = session
        self._party_repo = party_repo
        self._organization_repo = organization_repo
        self._user_session = user_session
        self._enterprise_audit_service = enterprise_audit_service
        self._tenant_context_service = tenant_context_service
        self._overview_rollup_reader = overview_rollup_reader
        self._uow_factory = uow_factory
        self._clock = clock

    def _new_context(self, *, causation_id: str | None = None) -> DomainEventContext:
        return DomainEventContext(correlation_id=generate_id(), causation_id=causation_id)

    def activate_party(self, party_id: str) -> Party:
        return _cmd.activate_party(self, party_id)

    def deactivate_party(self, party_id: str) -> Party:
        return _cmd.deactivate_party(self, party_id)

    def list_parties(self, *, active_only: bool | None = None) -> list[Party]:
        self._require_party_read_access("list parties")
        organization = self._active_organization()
        return self._party_repo.list_for_organization(organization.id, active_only=active_only)

    def get_party_rollup_summary(self) -> PartyRollupSummary:
        self._require_party_read_access("view party rollup summary")
        organization = self._active_organization()
        if self._tenant_context_service is None:
            raise BusinessRuleError(
                "Active organization context is required.",
                code="TENANT_CONTEXT_REQUIRED",
            )
        tenant_id = self._tenant_context_service.require_active_tenant_id(
            operation_label="view party rollup summary",
        )
        if self._overview_rollup_reader is None:
            raise RuntimeError("Platform overview rollup reader is not configured.")
        return self._overview_rollup_reader.get_party_summary(
            organization_id=organization.id,
            tenant_id=tenant_id,
        )

    def search_parties(
        self,
        *,
        search_text: str = "",
        active_only: bool | None = True,
        party_type: PartyType | str | None = None,
    ) -> list[Party]:
        """Kept for source-compatibility with any existing caller; real
        callers should prefer list_parties_page_for_organization's real
        SQL-level filtering below, which this does not use (in-Python
        filtering over the full organization list remains the historical
        behavior here, now scoped correctly to party_type as an identity
        axis rather than the old role-flavored enum)."""
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

    def list_parties_page_for_organization(
        self,
        organization_id: str,
        *,
        page: int = 1,
        page_size: int = _DEFAULT_PARTY_PAGE_SIZE,
        search: str = "",
        active_only: bool | None = None,
        party_type: PartyType | str | None = None,
        role: PartyRole | str | None = None,
    ) -> PartyPage:
        """Tenant-scoped (not ambient-active-organization-scoped) real
        SQL-level paginated/searchable read -- replaces search_parties()'s
        full-list-then-Python-filter approach for any real standalone
        Parties workspace. Works regardless of which organization is
        currently active in the caller's session."""
        self._require_party_read_access("list parties page for organization")
        if self._tenant_context_service is None:
            raise BusinessRuleError(
                "Active organization context is required.",
                code="TENANT_CONTEXT_REQUIRED",
            )
        tenant_id = self._tenant_context_service.require_active_tenant_id(
            operation_label="list parties page for organization",
        )
        normalized_page = max(1, page)
        normalized_page_size = page_size if page_size in PARTY_PAGE_SIZE_OPTIONS else _DEFAULT_PARTY_PAGE_SIZE
        resolved_type = coerce_party_type(party_type).value if party_type is not None else None
        resolved_role = (
            (role.value if isinstance(role, PartyRole) else PartyRole(str(role).upper()).value)
            if role
            else None
        )
        items, total, filtered_total = self._party_repo.list_page_for_organization_in_tenant(
            organization_id,
            tenant_id,
            page=normalized_page,
            page_size=normalized_page_size,
            search=search,
            active_only=active_only,
            party_type=resolved_type,
            role=resolved_role,
        )
        return PartyPage(
            items=items,
            total=total,
            filtered_total=filtered_total,
            page=normalized_page,
            page_size=normalized_page_size,
        )

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
        self._require_party_read_access("view party context")
        return self._active_organization()

    def create_party(
        self,
        *,
        party_code: str,
        party_name: str | None = None,
        name: str | None = None,
        party_type: PartyType | str = PartyType.ORGANIZATION,
        roles: object = (),
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
        registration_number: str = "",
        tax_identifier: str = "",
        external_reference: str = "",
        notes: str = "",
    ) -> Party:
        # No `is_active`/`status` parameter -- every new Party starts
        # ACTIVE (PartyLifecycleStatus's own default). Use
        # activate_party/deactivate_party afterward to change it.
        require_permission(self._user_session, "party.manage", operation_label="create party")
        organization = self._active_organization()
        tenant_id = organization.tenant_id
        party = Party.create(
            organization_id=organization.id,
            party_code=party_code,
            party_name=party_name if party_name is not None else name,
            party_type=party_type,
            roles=roles,
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
            registration_number=registration_number,
            tax_identifier=tax_identifier,
            external_reference=external_reference,
            notes=notes,
        )
        with self._uow_factory.create(context=self._new_context()) as uow:
            if uow.parties.get_by_code(organization.id, party.party_code) is not None:
                raise ValidationError(
                    "Party code already exists in the active organization.", code="PARTY_CODE_EXISTS"
                )
            try:
                uow.parties.add(party)
                record_audit_entry(
                    uow,
                    operation="create",
                    entity_type="party",
                    entity_id=party.id,
                    module="platform",
                    organization_id=organization.id,
                    category="MASTER_DATA",
                    severity="low",
                    after_data={"party_code": party.party_code, "party_name": party.party_name},
                    metadata={"action": "party.create"},
                    commit=False,
                    fail_closed=True,
                )
                record_activity(
                    uow,
                    action="party.create",
                    entity_type="party",
                    entity_id=party.id,
                    module="platform",
                    organization_id=organization.id,
                    message=f"Party created — {party.party_name}",
                    icon="party",
                    commit=False,
                )
                uow.record_event(
                    PartyCreated(
                        tenant_id=tenant_id,
                        organization_id=organization.id,
                        party_id=party.id,
                        occurred_at=self._clock.now(),
                    )
                )
                uow.commit()
            except IntegrityError as exc:
                raise ValidationError(
                    "Party code already exists in the active organization.", code="PARTY_CODE_EXISTS"
                ) from exc
        return party

    def update_party(
        self,
        party_id: str,
        *,
        party_code: str | None = None,
        party_name: str | None = None,
        name: str | None = None,
        party_type: PartyType | str | None = None,
        roles: object | None = None,
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
        registration_number: str | None = None,
        tax_identifier: str | None = None,
        external_reference: str | None = None,
        notes: str | None = None,
        expected_version: int | None = None,
    ) -> Party:
        # No `is_active`/`status` parameter here either -- lifecycle changes
        # only ever happen through activate_party/deactivate_party.
        require_permission(self._user_session, "party.manage", operation_label="update party")
        organization = self._active_organization()
        tenant_id = organization.tenant_id
        with self._uow_factory.create(context=self._new_context()) as uow:
            party = uow.parties.get(party_id)
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
                roles=roles if roles is not None else party.roles,
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
                registration_number=(
                    registration_number if registration_number is not None else party.registration_number
                ),
                tax_identifier=tax_identifier if tax_identifier is not None else party.tax_identifier,
                external_reference=external_reference if external_reference is not None else party.external_reference,
                notes=notes if notes is not None else party.notes,
            )
            profile_changed = (
                candidate.party_code != party.party_code
                or candidate.party_name != party.party_name
                or candidate.party_type != party.party_type
                or candidate.roles != party.roles
                or candidate.legal_name != party.legal_name
                or candidate.contact_name != party.contact_name
                or candidate.email != party.email
                or candidate.phone != party.phone
                or candidate.country != party.country
                or candidate.city != party.city
                or candidate.address_line_1 != party.address_line_1
                or candidate.address_line_2 != party.address_line_2
                or candidate.postal_code != party.postal_code
                or candidate.website != party.website
                or candidate.registration_number != party.registration_number
                or candidate.tax_identifier != party.tax_identifier
                or candidate.external_reference != party.external_reference
                or candidate.notes != party.notes
            )
            if not profile_changed:
                return party
            candidate = replace(candidate, updated_at=datetime.now(timezone.utc))
            if party_code is not None:
                existing = uow.parties.get_by_code(organization.id, candidate.party_code)
                if existing is not None and existing.id != party.id:
                    raise ValidationError(
                        "Party code already exists in the active organization.", code="PARTY_CODE_EXISTS"
                    )

            try:
                uow.parties.update(candidate)
                record_audit_entry(
                    uow,
                    operation="update",
                    entity_type="party",
                    entity_id=candidate.id,
                    module="platform",
                    organization_id=organization.id,
                    category="MASTER_DATA",
                    severity="low",
                    metadata={"action": "party.update"},
                    commit=False,
                    fail_closed=True,
                )
                record_activity(
                    uow,
                    action="party.update",
                    entity_type="party",
                    entity_id=candidate.id,
                    module="platform",
                    organization_id=organization.id,
                    message=f"Party updated — {candidate.party_name}",
                    icon="party",
                    commit=False,
                )
                uow.record_event(
                    PartyProfileUpdated(
                        tenant_id=tenant_id,
                        organization_id=organization.id,
                        party_id=candidate.id,
                        occurred_at=self._clock.now(),
                    )
                )
                uow.commit()
            except IntegrityError as exc:
                raise ValidationError(
                    "Party code already exists in the active organization.", code="PARTY_CODE_EXISTS"
                ) from exc
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

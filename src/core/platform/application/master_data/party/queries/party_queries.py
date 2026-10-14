from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from src.core.platform.application.master_data.party.party_context import (
    active_organization,
)
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_any_permission,
)
from src.core.platform.application.tenant.tenancy import TenantContextService
from src.core.platform.common.exceptions import (
    BusinessRuleError,
    NotFoundError,
)
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
from src.core.platform.domain.master_data.org import Organization
from src.core.platform.domain.master_data.party import (
    Party,
    PartyRole,
    PartyType,
    coerce_party_type,
    normalize_party_code,
)

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
    from src.core.platform.domain.security.auth.session import UserSessionContext


class PartyQueryHandler:
    """Party reads: active-organization lists, search and lookups, the overview
    rollup, and the tenant-scoped page for any organization."""

    def __init__(
        self,
        *,
        party_repo: PartyRepository,
        organization_repo: OrganizationRepository,
        user_session: UserSessionContext | None,
        tenant_context_service: TenantContextService | None,
        overview_rollup_reader: PlatformOverviewRollupReader | None,
    ) -> None:
        self._party_repo = party_repo
        self._organization_repo = organization_repo
        self._user_session = user_session
        self._tenant_context_service = tenant_context_service
        self._overview_rollup_reader = overview_rollup_reader

    def list_parties(self, *, active_only: bool | None = None) -> list[Party]:
        self._require_party_read_access("list parties")
        organization = active_organization(self._tenant_context_service)
        return self._party_repo.list_for_organization(organization.id, active_only=active_only)

    def get_party_rollup_summary(self) -> PartyRollupSummary:
        self._require_party_read_access("view party rollup summary")
        organization = active_organization(self._tenant_context_service)
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
        rows = self._party_repo.list_for_organization(active_organization(self._tenant_context_service).id, active_only=active_only)
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
        organization = active_organization(self._tenant_context_service)
        party = self._party_repo.get(party_id)
        if party is None or party.organization_id != organization.id:
            raise NotFoundError("Party not found in the active organization.", code="PARTY_NOT_FOUND")
        return party

    def find_party_by_code(self, party_code: str) -> Party | None:
        self._require_party_read_access("resolve party")
        normalized_code = normalize_party_code(party_code)
        return self._party_repo.get_by_code(active_organization(self._tenant_context_service).id, normalized_code)

    def get_context_organization(self) -> Organization:
        self._require_party_read_access("view party context")
        return active_organization(self._tenant_context_service)

    def _require_party_read_access(self, operation_label: str) -> None:
        require_any_permission(
            self._user_session,
            ("settings.manage", "party.read"),
            operation_label=operation_label,
        )


__all__ = ["PARTY_PAGE_SIZE_OPTIONS", "PartyPage", "PartyQueryHandler"]

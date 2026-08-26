from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.core.shared.audit import record_audit_entry
from src.core.platform.common.exceptions import (
    BusinessRuleError,
    ConcurrencyError,
    NotFoundError,
    ValidationError,
)
from src.core.platform.common.ids import generate_id
from src.core.shared.events.domain_event_context import DomainEventContext
from src.core.shared.events.domain_events import domain_events
from src.core.platform.application.security.authorization.enforcement.permission_checks import require_permission
from src.core.platform.contract.persistence.organization_unit_of_work import (
    OrganizationUnitOfWorkFactory,
)
from src.core.platform.contract.read.overview.platform_overview_rollup_reader import PlatformOverviewRollupReader
from src.core.platform.contract.repositories.master_data.org.contracts import OrganizationRepository
from src.core.platform.domain.master_data.org import Organization
from src.core.platform.domain.master_data.org.events import OrganizationCreated
from src.core.platform.domain.master_data.org.support import (
    DEFAULT_ORGANIZATION_CODE,
    DEFAULT_ORGANIZATION_CURRENCY,
    DEFAULT_ORGANIZATION_NAME,
    DEFAULT_ORGANIZATION_TIMEZONE,
)
from src.core.shared.time.clock import Clock

if TYPE_CHECKING:
    from src.core.platform.application.history.audit.enterprise_audit_service import EnterpriseAuditService
    from src.core.platform.domain.security.auth.session import UserSessionContext
    from src.core.platform.application.tenant.tenancy.tenant_context import TenantContextService


class OrganizationService:
    def __init__(
        self,
        session: Session,
        organization_repo: OrganizationRepository,
        *,
        uow_factory: OrganizationUnitOfWorkFactory,
        clock: Clock,
        user_session: UserSessionContext | None = None,
        enterprise_audit_service: EnterpriseAuditService | None = None,
        tenant_context_service: TenantContextService | None = None,
        overview_rollup_reader: PlatformOverviewRollupReader | None = None,
    ):
        self._session = session
        self._organization_repo = organization_repo
        self._uow_factory = uow_factory
        self._clock = clock
        self._user_session = user_session
        self._enterprise_audit_service = enterprise_audit_service
        self._tenant_context_service = tenant_context_service
        self._overview_rollup_reader = overview_rollup_reader

    def _new_context(self, *, causation_id: str | None = None) -> DomainEventContext:
        return DomainEventContext(correlation_id=generate_id(), causation_id=causation_id)

    # ------------------------------------------------------------------
    # Tenant context — the single gateway for all runtime methods.
    # Raises TENANT_CONTEXT_REQUIRED immediately if no active tenant.
    # ------------------------------------------------------------------

    def _require_current_tenant_id(self, *, operation_label: str) -> str:
        if self._user_session is None:
            raise BusinessRuleError(
                f"Tenant context is required to {operation_label}.",
                code="TENANT_CONTEXT_REQUIRED",
            )
        tenant_id = str(self._user_session.active_tenant_id() or "").strip()
        if not tenant_id:
            raise BusinessRuleError(
                f"Tenant context is required to {operation_label}.",
                code="TENANT_CONTEXT_REQUIRED",
            )
        return tenant_id

    def require_current_tenant_id(self, *, operation_label: str) -> str:
        """Public accessor (P4C) for `PlatformRuntimeApplicationService.provision_organization`,
        which needs the same tenant-resolution guard every Organization method uses internally
        before it can call `_create_organization_using`/`_activate_organization_using` inside its
        own provisioning UnitOfWork. Reuses the existing guard rather than duplicating it."""
        return self._require_current_tenant_id(operation_label=operation_label)

    # ------------------------------------------------------------------
    # Bootstrap — runs before a tenant record exists in the system.
    # Uses unscoped list_all() only when no tenant context is present.
    # When a tenant context IS present (runtime re-call), scopes by it
    # so it never creates an untenanted organization at runtime.
    # ------------------------------------------------------------------

    def bootstrap_defaults(self) -> None:
        bootstrap_tenant_id = (
            str(self._user_session.active_tenant_id() or "").strip()
            if self._user_session is not None
            else ""
        ) or None

        if bootstrap_tenant_id:
            if self._organization_repo.list_for_tenant(bootstrap_tenant_id):
                return
        else:
            if self._organization_repo.list_all():
                return

        organization = Organization.create(
            organization_code=DEFAULT_ORGANIZATION_CODE,
            display_name=DEFAULT_ORGANIZATION_NAME,
            timezone_name=DEFAULT_ORGANIZATION_TIMEZONE,
            base_currency=DEFAULT_ORGANIZATION_CURRENCY,
            is_enabled=True,
            tenant_id=bootstrap_tenant_id,
        )
        with self._uow_factory.create(context=self._new_context()) as uow:
            uow.organizations.add(organization)
            uow.commit()

    # ------------------------------------------------------------------
    # Runtime read operations — all tenant-scoped, fail-fast.
    # ------------------------------------------------------------------

    def list_organizations(self, *, enabled_only: bool | None = None) -> list[Organization]:
        require_permission(self._user_session, "settings.manage", operation_label="list organizations")
        tenant_id = self._require_current_tenant_id(operation_label="list organizations")
        return self._organization_repo.list_for_tenant(tenant_id, enabled_only=enabled_only)

    def get_organization_count(self) -> int:
        require_permission(self._user_session, "settings.manage", operation_label="view organization count")
        tenant_id = self._require_current_tenant_id(operation_label="view organization count")
        if self._overview_rollup_reader is None:
            raise RuntimeError("Platform overview rollup reader is not configured.")
        return self._overview_rollup_reader.get_organization_count(tenant_id=tenant_id)

    # ------------------------------------------------------------------
    # Runtime write operations — all tenant-scoped, fail-fast.
    # tenant_id is always re-pinned on the domain object before write
    # so the service layer is the authority, not the object's field.
    # ------------------------------------------------------------------

    def create_organization(
        self,
        *,
        organization_code: str,
        display_name: str,
        timezone_name: str = DEFAULT_ORGANIZATION_TIMEZONE,
        base_currency: str = DEFAULT_ORGANIZATION_CURRENCY,
        is_enabled: bool = True,
    ) -> Organization:
        require_permission(self._user_session, "settings.manage", operation_label="create organization")
        tenant_id = self._require_current_tenant_id(operation_label="create organization")
        with self._uow_factory.create(context=self._new_context()) as uow:
            organization = self._create_organization_using(
                uow.organizations,
                uow,
                organization_code=organization_code,
                display_name=display_name,
                timezone_name=timezone_name,
                base_currency=base_currency,
                is_enabled=is_enabled,
                tenant_id=tenant_id,
            )
            try:
                uow.commit()
            except IntegrityError as exc:
                raise ValidationError(
                    "Organization code already exists.", code="ORGANIZATION_CODE_EXISTS"
                ) from exc
        return organization

    def update_organization(
        self,
        organization_id: str,
        *,
        organization_code: str | None = None,
        display_name: str | None = None,
        timezone_name: str | None = None,
        base_currency: str | None = None,
        is_enabled: bool | None = None,
        expected_version: int | None = None,
    ) -> Organization:
        require_permission(self._user_session, "settings.manage", operation_label="update organization")
        tenant_id = self._require_current_tenant_id(operation_label="update organization")
        with self._uow_factory.create(context=self._new_context()) as uow:
            organization = uow.organizations.get_for_tenant(organization_id, tenant_id)
            if organization is None:
                raise NotFoundError("Organization not found.", code="ORGANIZATION_NOT_FOUND")
            if expected_version is not None and organization.version != expected_version:
                raise ConcurrencyError(
                    "Organization changed since you opened it. Refresh and try again.",
                    code="STALE_WRITE",
                )

            candidate = replace(
                organization,
                organization_code=(
                    organization.organization_code
                    if organization_code is None
                    else organization_code
                ),
                display_name=organization.display_name if display_name is None else display_name,
                timezone_name=organization.timezone_name if timezone_name is None else timezone_name,
                base_currency=organization.base_currency if base_currency is None else base_currency,
                is_enabled=organization.is_enabled if is_enabled is None else is_enabled,
                tenant_id=tenant_id,
            )
            existing = uow.organizations.get_by_code_for_tenant(
                candidate.organization_code,
                tenant_id,
            )
            if existing is not None and existing.id != organization.id:
                raise ValidationError("Organization code already exists.", code="ORGANIZATION_CODE_EXISTS")
            try:
                uow.organizations.update(candidate)

                record_audit_entry(
                    uow,
                    operation="update",
                    entity_type="organization",
                    entity_id=candidate.id,
                    module="platform",
                    severity="low",
                    metadata={
                        "action": "organization.update",
                        "organization_code": candidate.organization_code,
                        "display_name": candidate.display_name,
                        "timezone_name": candidate.timezone_name,
                        "base_currency": candidate.base_currency,
                        "is_enabled": str(candidate.is_enabled),
                    },
                    commit=False,
                    fail_closed=True,
                )
                uow.commit()
            except IntegrityError as exc:
                raise ValidationError(
                    "Organization code already exists.", code="ORGANIZATION_CODE_EXISTS"
                ) from exc

        domain_events.organizations_changed.emit(candidate.id)
        return candidate

    def enable_organization(self, organization_id: str) -> Organization:
        return self._set_organization_enabled(organization_id, is_enabled=True, action="organization.enable")

    def disable_organization(self, organization_id: str) -> Organization:
        """Availability mutation only -- flips `is_enabled` False for exactly this organization.
        Symmetric with `enable_organization`; see its docstring."""
        return self._set_organization_enabled(organization_id, is_enabled=False, action="organization.disable")

    def _set_organization_enabled(
        self, organization_id: str, *, is_enabled: bool, action: str
    ) -> Organization:
        require_permission(
            self._user_session, "settings.manage", operation_label="change organization availability"
        )
        tenant_id = self._require_current_tenant_id(operation_label="change organization availability")
        with self._uow_factory.create(context=self._new_context()) as uow:
            organization = uow.organizations.get_for_tenant(organization_id, tenant_id)
            if organization is None:
                raise NotFoundError("Organization not found.", code="ORGANIZATION_NOT_FOUND")
            if organization.is_enabled == is_enabled:
                # No-op: nothing actually changes, so no write, no audit, no signal -- a
                # past-tense state-transition write must represent an actual transition
                # (P9A-R/P9B decision, applied here for the first time it's implementable).
                return organization
            candidate = replace(organization, is_enabled=is_enabled, tenant_id=tenant_id)
            uow.organizations.update(candidate)
            record_audit_entry(
                uow,
                operation="update",
                entity_type="organization",
                entity_id=candidate.id,
                module="platform",
                severity="low",
                metadata={
                    "action": action,
                    "organization_code": candidate.organization_code,
                    "display_name": candidate.display_name,
                    "is_enabled": str(candidate.is_enabled),
                },
                commit=False,
                fail_closed=True,
            )
            uow.commit()
        domain_events.organizations_changed.emit(candidate.id)
        if (
            not is_enabled
            and self._user_session is not None
            and self._user_session.active_organization_id() == candidate.id
        ):
            self._user_session.set_active_organization_id(None)
        return candidate


    def _create_organization_using(
        self,
        organization_repo: OrganizationRepository,
        uow: object,
        *,
        organization_code: str,
        display_name: str,
        timezone_name: str,
        base_currency: str,
        is_enabled: bool,
        tenant_id: str,
    ) -> Organization:
        organization = Organization.create(
            organization_code=organization_code,
            display_name=display_name,
            timezone_name=timezone_name,
            base_currency=base_currency,
            is_enabled=is_enabled,
            tenant_id=tenant_id,
        )
        if organization_repo.get_by_code_for_tenant(organization.organization_code, tenant_id) is not None:
            raise ValidationError("Organization code already exists.", code="ORGANIZATION_CODE_EXISTS")
        organization_repo.add(organization)
        record_audit_entry(
            uow,
            operation="create",
            entity_type="organization",
            entity_id=organization.id,
            module="platform",
            severity="low",
            metadata={
                "action": "organization.create",
                "organization_code": organization.organization_code,
                "display_name": organization.display_name,
                "timezone_name": organization.timezone_name,
                "base_currency": organization.base_currency,
                "is_enabled": str(organization.is_enabled),
            },
            commit=False,
            fail_closed=True,
        )
        uow.record_event(
            OrganizationCreated(
                tenant_id=tenant_id,
                organization_id=organization.id,
                name=organization.display_name,
                code=organization.organization_code,
                occurred_at=self._clock.now(),
            )
        )
        return organization

    def _enable_organization_using(
        self,
        organization_repo: OrganizationRepository,
        audit_owner: object,
        *,
        organization_id: str,
        tenant_id: str,
    ) -> Organization:
        organization = organization_repo.get_for_tenant(organization_id, tenant_id)
        if organization is None:
            raise NotFoundError("Organization not found.", code="ORGANIZATION_NOT_FOUND")
        candidate = replace(organization, is_enabled=True, tenant_id=tenant_id)
        organization_repo.update(candidate)
        record_audit_entry(
            audit_owner,
            operation="update",
            entity_type="organization",
            entity_id=candidate.id,
            module="platform",
            severity="low",
            metadata={
                "action": "organization.enable",
                "organization_code": candidate.organization_code,
                "display_name": candidate.display_name,
            },
            commit=False,
            fail_closed=True,
        )
        return candidate


__all__ = ["OrganizationService"]

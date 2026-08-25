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
from src.core.platform.domain.master_data.org.support import (
    DEFAULT_ORGANIZATION_CODE,
    DEFAULT_ORGANIZATION_CURRENCY,
    DEFAULT_ORGANIZATION_NAME,
    DEFAULT_ORGANIZATION_TIMEZONE,
)

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
        user_session: UserSessionContext | None = None,
        enterprise_audit_service: EnterpriseAuditService | None = None,
        tenant_context_service: TenantContextService | None = None,
        overview_rollup_reader: PlatformOverviewRollupReader | None = None,
    ):
        self._session = session
        self._organization_repo = organization_repo
        self._uow_factory = uow_factory
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
            is_active=True,
            tenant_id=bootstrap_tenant_id,
        )
        with self._uow_factory.create(context=self._new_context()) as uow:
            uow.organizations.add(organization)
            uow.commit()

    # ------------------------------------------------------------------
    # Runtime read operations — all tenant-scoped, fail-fast.
    # ------------------------------------------------------------------

    def list_organizations(self, *, active_only: bool | None = None) -> list[Organization]:
        require_permission(self._user_session, "settings.manage", operation_label="list organizations")
        tenant_id = self._require_current_tenant_id(operation_label="list organizations")
        return self._organization_repo.list_for_tenant(tenant_id, active_only=active_only)

    def get_organization_count(self) -> int:
        require_permission(self._user_session, "settings.manage", operation_label="view organization count")
        tenant_id = self._require_current_tenant_id(operation_label="view organization count")
        if self._overview_rollup_reader is None:
            raise RuntimeError("Platform overview rollup reader is not configured.")
        return self._overview_rollup_reader.get_organization_count(tenant_id=tenant_id)

    def get_active_organization(self) -> Organization:
        require_permission(self._user_session, "settings.manage", operation_label="view active organization")
        tenant_id = self._require_current_tenant_id(operation_label="view active organization")
        organization = self._organization_repo.get_active_for_tenant(tenant_id)
        if organization is None:
            self.bootstrap_defaults()
            organization = self._organization_repo.get_active_for_tenant(tenant_id)
        if organization is None:
            raise NotFoundError("Active organization not found.", code="ORGANIZATION_NOT_FOUND")
        return organization

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
        is_active: bool = True,
        commit: bool = True,
    ) -> Organization:
        require_permission(self._user_session, "settings.manage", operation_label="create organization")
        tenant_id = self._require_current_tenant_id(operation_label="create organization")
        organization = Organization.create(
            organization_code=organization_code,
            display_name=display_name,
            timezone_name=timezone_name,
            base_currency=base_currency,
            is_active=is_active,
            tenant_id=tenant_id,
        )
        if commit:
            # Transaction-owning path (P4B): a fresh `OrganizationUnitOfWork` per call. Any
            # exception raised inside the `with` block is rolled back and the Session closed by
            # the UoW's own `__exit__` (src/infra/persistence/db/unit_of_work.py) -- no manual
            # rollback/close needed here, unlike the grandfathered `commit=False` branch below.
            with self._uow_factory.create(context=self._new_context()) as uow:
                if uow.organizations.get_by_code_for_tenant(organization.organization_code, tenant_id) is not None:
                    raise ValidationError("Organization code already exists.", code="ORGANIZATION_CODE_EXISTS")
                try:
                    if organization.is_active:
                        self._deactivate_other_organizations_using(
                            uow.organizations, tenant_id=tenant_id, exclude_id=None
                        )
                    uow.organizations.add(organization)
                    # Audit is staged in the same transaction as the business write (ADR-003:
                    # "the business mutation and successful security audit intent commit
                    # atomically" for platform provisioning) — never a second, separate commit.
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
                            "is_active": str(organization.is_active),
                        },
                        commit=False,
                        fail_closed=True,
                    )
                    uow.commit()
                except IntegrityError as exc:
                    raise ValidationError(
                        "Organization code already exists.", code="ORGANIZATION_CODE_EXISTS"
                    ) from exc
            domain_events.organizations_changed.emit(organization.id)
            return organization
        # Grandfathered caller-owned path (P4B, mirrors ADR-005 Section 24 Round 8's
        # `request_change(commit=False)` precedent): the sole real caller,
        # `PlatformRuntimeService.provision_organization`, composes this create with module
        # entitlement provisioning and (optionally) activation into one outer transaction on the
        # shared, process-lifetime Session, committed once by that caller. Forcing this branch
        # onto an independent fresh UoW would break that real cross-capability atomicity
        # requirement, so it is preserved byte-for-byte on `self._session`/`self._organization_repo`.
        if self._organization_repo.get_by_code_for_tenant(organization.organization_code, tenant_id) is not None:
            raise ValidationError("Organization code already exists.", code="ORGANIZATION_CODE_EXISTS")
        try:
            if organization.is_active:
                self._deactivate_other_organizations(tenant_id=tenant_id, exclude_id=None)
            self._organization_repo.add(organization)
            record_audit_entry(
                self,
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
                    "is_active": str(organization.is_active),
                },
                commit=False,
                fail_closed=True,
            )
            self._session.flush()
        except IntegrityError as exc:
            self._session.rollback()
            raise ValidationError("Organization code already exists.", code="ORGANIZATION_CODE_EXISTS") from exc
        except Exception:
            self._session.rollback()
            raise
        return organization

    def update_organization(
        self,
        organization_id: str,
        *,
        organization_code: str | None = None,
        display_name: str | None = None,
        timezone_name: str | None = None,
        base_currency: str | None = None,
        is_active: bool | None = None,
        expected_version: int | None = None,
    ) -> Organization:
        require_permission(self._user_session, "settings.manage", operation_label="update organization")
        tenant_id = self._require_current_tenant_id(operation_label="update organization")
        # No real caller composes `update_organization` into a larger caller-owned transaction
        # (searched: `platform_runtime_service.py`, desktop `runtime.py`, the QML presenter, and
        # every test caller -- each invokes it standalone) -- unlike `create_organization`/
        # `set_active_organization`, this method needs no `commit: bool` bifurcation and always
        # owns a fresh `OrganizationUnitOfWork`.
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
                is_active=organization.is_active if is_active is None else is_active,
                tenant_id=tenant_id,
            )
            existing = uow.organizations.get_by_code_for_tenant(
                candidate.organization_code,
                tenant_id,
            )
            if existing is not None and existing.id != organization.id:
                raise ValidationError("Organization code already exists.", code="ORGANIZATION_CODE_EXISTS")
            if not candidate.is_active and organization.is_active and not self._has_other_active_organizations_using(
                    uow.organizations, organization.id, tenant_id=tenant_id
                ):
                    raise ValidationError(
                        "At least one active organization is required.",
                        code="ORGANIZATION_ACTIVE_REQUIRED",
                    )
            try:
                if candidate.is_active:
                    self._deactivate_other_organizations_using(
                        uow.organizations, tenant_id=tenant_id, exclude_id=organization.id
                    )
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
                        "is_active": str(candidate.is_active),
                    },
                    commit=False,
                )
                uow.commit()
            except IntegrityError as exc:
                raise ValidationError(
                    "Organization code already exists.", code="ORGANIZATION_CODE_EXISTS"
                ) from exc
        domain_events.organizations_changed.emit(candidate.id)
        return candidate

    def set_active_organization(self, organization_id: str, *, commit: bool = True) -> Organization:
        require_permission(self._user_session, "settings.manage", operation_label="set active organization")
        tenant_id = self._require_current_tenant_id(operation_label="set active organization")
        if commit:
            # Transaction-owning path (P4B): a fresh `OrganizationUnitOfWork` per call.
            with self._uow_factory.create(context=self._new_context()) as uow:
                organization = uow.organizations.get_for_tenant(organization_id, tenant_id)
                if organization is None:
                    raise NotFoundError("Organization not found.", code="ORGANIZATION_NOT_FOUND")
                candidate = replace(
                    organization,
                    is_active=True,
                    tenant_id=tenant_id,
                )
                self._deactivate_other_organizations_using(
                    uow.organizations, tenant_id=tenant_id, exclude_id=organization.id
                )
                uow.organizations.update(candidate)
                record_audit_entry(
                    uow,
                    operation="update",
                    entity_type="organization",
                    entity_id=candidate.id,
                    module="platform",
                    severity="low",
                    metadata={
                        "action": "organization.set_active",
                        "organization_code": candidate.organization_code,
                        "display_name": candidate.display_name,
                    },
                    commit=False,
                    fail_closed=True,
                )
                uow.commit()
            if self._tenant_context_service is not None:
                self._tenant_context_service.set_active_organization(candidate.id)
            elif self._user_session is not None:
                self._user_session.set_active_organization_id(candidate.id)
            domain_events.organizations_changed.emit(candidate.id)
            return candidate
        # Grandfathered caller-owned path (P4B, mirrors ADR-005 Section 24 Round 8's
        # `request_change(commit=False)` precedent): the sole real caller,
        # `PlatformRuntimeService.provision_organization`, folds this activation into the same
        # outer transaction as organization creation and module entitlement provisioning,
        # committed once by that caller on the shared, process-lifetime Session. Preserved
        # byte-for-byte on `self._session`/`self._organization_repo`.
        organization = self._organization_repo.get_for_tenant(organization_id, tenant_id)
        if organization is None:
            raise NotFoundError("Organization not found.", code="ORGANIZATION_NOT_FOUND")
        candidate = replace(
            organization,
            is_active=True,
            tenant_id=tenant_id,
        )
        try:
            self._deactivate_other_organizations(tenant_id=tenant_id, exclude_id=organization.id)
            self._organization_repo.update(candidate)
            record_audit_entry(
                self,
                operation="update",
                entity_type="organization",
                entity_id=candidate.id,
                module="platform",
                severity="low",
                metadata={
                    "action": "organization.set_active",
                    "organization_code": candidate.organization_code,
                    "display_name": candidate.display_name,
                },
                commit=False,
                fail_closed=True,
            )
            self._session.flush()
        except Exception:
            self._session.rollback()
            raise
        # The caller deferred commit() to fold this into a larger transaction. It must call
        # tenant_context_service.set_active_organization(...) itself, only after its own commit
        # succeeds — this row isn't durable yet.
        return candidate

    # ------------------------------------------------------------------
    # Private helpers — tenant_id passed explicitly by every caller.
    # Orgs from list_for_tenant() already carry the correct tenant_id;
    # the pin below is defense-in-depth before any repo.update() call.
    # `_using` variants (P4B) are parameterized by repository so transaction-owning callers can
    # pass the active UoW's fresh-Session-bound repository instead of the legacy
    # `self._organization_repo`; the original names remain as thin wrappers over
    # `self._organization_repo` for the grandfathered `commit=False` paths.
    # ------------------------------------------------------------------

    def _deactivate_other_organizations_using(
        self, organization_repo: OrganizationRepository, *, tenant_id: str, exclude_id: str | None
    ) -> None:
        for organization in organization_repo.list_for_tenant(tenant_id, active_only=True):
            if exclude_id and organization.id == exclude_id:
                continue
            organization.is_active = False
            organization.tenant_id = tenant_id  # pin: tenant ownership is immutable
            organization_repo.update(organization)

    def _deactivate_other_organizations(self, *, tenant_id: str, exclude_id: str | None) -> None:
        self._deactivate_other_organizations_using(
            self._organization_repo, tenant_id=tenant_id, exclude_id=exclude_id
        )

    def _has_other_active_organizations_using(
        self, organization_repo: OrganizationRepository, organization_id: str, *, tenant_id: str
    ) -> bool:
        return any(
            org.id != organization_id
            for org in organization_repo.list_for_tenant(tenant_id, active_only=True)
        )


__all__ = ["OrganizationService"]

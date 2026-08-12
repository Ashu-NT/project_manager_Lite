from __future__ import annotations

import json
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from src.core.modules.project_management.access.scope_permissions import require_project_permission
from src.core.modules.project_management.application.common.clock import Clock
from src.core.modules.project_management.application.common.module_guard import ProjectManagementModuleGuardMixin
from src.core.modules.project_management.contracts.repositories.billing import ProjectBillingRepository
from src.core.modules.project_management.contracts.repositories.financial_configuration import ProjectFinancialProfileRepository
from src.core.modules.project_management.contracts.repositories.project import ProjectRepository
from src.core.modules.project_management.domain.financials.billing_profile import (
    BillingProfileStatus,
    ProjectBillingProfile,
    ProjectBillingScheduleLine,
)
from src.core.modules.project_management.domain.financials.configuration import BillingMethod
from src.core.platform.application.security.authorization.enforcement.permission_checks import require_permission
from src.core.platform.application.tenant.tenancy.tenant_context import TenantContextService
from src.core.platform.common.exceptions import BusinessRuleError, NotFoundError
from src.core.shared.audit import record_audit_entry
from src.core.shared.events.domain_events import domain_events


class ProjectBillingProfileService(ProjectManagementModuleGuardMixin):
    """Owns PM commercial terms and fixed-price billing schedules."""

    def __init__(
        self,
        *,
        session: Session,
        billing_repo: ProjectBillingRepository,
        financial_profile_repo: ProjectFinancialProfileRepository,
        project_repo: ProjectRepository,
        tenant_context_service: TenantContextService,
        clock: Clock,
        user_session=None,
        enterprise_audit_service=None,
        module_catalog_service=None,
    ) -> None:
        self._session = session
        self._billing_repo = billing_repo
        self._financial_profile_repo = financial_profile_repo
        self._project_repo = project_repo
        self._tenant_context_service = tenant_context_service
        self._clock = clock
        self._user_session = user_session
        self._enterprise_audit_service = enterprise_audit_service
        self._module_catalog_service = module_catalog_service

    def get_profile(self, project_id: str) -> ProjectBillingProfile | None:
        self._require(project_id, "finance.read", "view project billing profile")
        return self._billing_repo.get_profile(project_id)

    def list_schedule(self, project_id: str) -> list[ProjectBillingScheduleLine]:
        self._require(project_id, "finance.read", "view project billing schedule")
        return self._billing_repo.list_schedule_lines(project_id)

    def create_profile(
        self,
        project_id: str,
        *,
        contract_reference: str,
        contract_value: Decimal,
        customer_party_id: str | None = None,
        external_customer_reference: str | None = None,
        purchase_order_reference: str | None = None,
        cost_plus_markup_percent: Decimal = Decimal("0"),
        payment_terms_days: int = 30,
        retention_years: int = 7,
    ) -> ProjectBillingProfile:
        self._require(project_id, "finance.manage", "create project billing profile")
        if self._project_repo.get(project_id) is None:
            raise NotFoundError("Project not found.", code="PROJECT_NOT_FOUND")
        if self._billing_repo.get_profile(project_id) is not None:
            raise BusinessRuleError(
                "A billing profile already exists for this Project.",
                code="BILLING_PROFILE_ALREADY_EXISTS",
            )
        financial_profile = self._require_billable_financial_profile(project_id)
        context = self._tenant_context_service.require_active_scope_ids(
            operation_label="create project billing profile"
        )
        actor_id = self._actor_id()
        profile = ProjectBillingProfile.create(
            tenant_id=context.tenant_id,
            organization_id=context.organization_id,
            project_id=project_id,
            currency_code=financial_profile.currency_code,
            contract_reference=contract_reference,
            contract_value=contract_value,
            customer_party_id=customer_party_id,
            external_customer_reference=external_customer_reference,
            purchase_order_reference=purchase_order_reference,
            cost_plus_markup_percent=cost_plus_markup_percent,
            payment_terms_days=payment_terms_days,
            retention_years=retention_years,
            created_by=actor_id,
            created_at=self._clock.now(),
        )
        return self._persist("create", profile, lambda: self._billing_repo.add_profile(profile))

    def activate_profile(
        self, project_id: str, *, expected_row_version: int
    ) -> ProjectBillingProfile:
        self._require(project_id, "finance.manage", "activate project billing profile")
        profile = self._require_profile(project_id)
        financial_profile = self._require_billable_financial_profile(project_id)
        if profile.currency_code != financial_profile.currency_code:
            raise BusinessRuleError(
                "Billing and Project financial currencies must match.",
                code="BILLING_PROFILE_CURRENCY_MISMATCH",
            )
        profile.activate(actor_id=self._actor_id(), occurred_at=self._clock.now())
        return self._persist(
            "activate",
            profile,
            lambda: self._billing_repo.update_profile(
                profile, expected_row_version=expected_row_version
            ),
        )

    def add_schedule_line(
        self,
        project_id: str,
        *,
        name: str,
        amount: Decimal,
        due_date: date,
        task_id: str | None = None,
        acceptance_reference: str | None = None,
    ) -> ProjectBillingScheduleLine:
        self._require(project_id, "finance.manage", "add billing schedule line")
        profile = self._require_profile(project_id)
        if profile.status is BillingProfileStatus.CLOSED:
            raise BusinessRuleError(
                "A closed billing profile cannot accept schedule lines.",
                code="BILLING_PROFILE_CLOSED",
            )
        actor_id = self._actor_id()
        line = ProjectBillingScheduleLine.create(
            tenant_id=profile.tenant_id,
            organization_id=profile.organization_id,
            project_id=project_id,
            billing_profile_id=profile.id,
            name=name,
            amount=amount,
            currency_code=profile.currency_code,
            due_date=due_date,
            task_id=task_id,
            acceptance_reference=acceptance_reference,
            created_by=actor_id,
            created_at=self._clock.now(),
        )
        return self._persist(
            "schedule_line.create", line, lambda: self._billing_repo.add_schedule_line(line)
        )

    def mark_schedule_line_ready(
        self, line_id: str, *, expected_row_version: int
    ) -> ProjectBillingScheduleLine:
        line = self._require_schedule_line(line_id)
        self._require(line.project_id, "finance.manage", "mark billing schedule line ready")
        line.mark_ready(actor_id=self._actor_id(), occurred_at=self._clock.now())
        return self._persist(
            "schedule_line.ready",
            line,
            lambda: self._billing_repo.update_schedule_line(
                line, expected_row_version=expected_row_version
            ),
        )

    def _require_billable_financial_profile(self, project_id: str):
        profile = self._financial_profile_repo.get_by_project(project_id)
        if profile is None:
            raise NotFoundError(
                "Project financial profile not found.",
                code="PROJECT_FINANCIAL_PROFILE_NOT_FOUND",
            )
        if not profile.is_billable or profile.billing_method is BillingMethod.NON_BILLABLE:
            raise BusinessRuleError(
                "The Project financial profile is not billable.",
                code="PROJECT_NOT_BILLABLE",
            )
        return profile

    def _require_profile(self, project_id: str) -> ProjectBillingProfile:
        profile = self._billing_repo.get_profile(project_id)
        if profile is None:
            raise NotFoundError(
                "Project billing profile not found.", code="BILLING_PROFILE_NOT_FOUND"
            )
        return profile

    def _require_schedule_line(self, line_id: str) -> ProjectBillingScheduleLine:
        line = self._billing_repo.get_schedule_line(line_id)
        if line is None:
            raise NotFoundError(
                "Billing schedule line not found.", code="BILLING_SCHEDULE_LINE_NOT_FOUND"
            )
        return line

    def _require(self, project_id: str, permission: str, operation: str) -> None:
        require_permission(self._user_session, permission, operation_label=operation)
        require_project_permission(
            self._user_session, project_id, permission, operation_label=operation
        )

    def _actor_id(self) -> str:
        actor_id = getattr(getattr(self._user_session, "principal", None), "user_id", None)
        if not actor_id:
            raise BusinessRuleError(
                "An authenticated actor is required for billing changes.",
                code="BILLING_ACTOR_REQUIRED",
            )
        return str(actor_id)

    def _persist(self, operation: str, entity, write):
        try:
            write()
            self._billing_repo.flush()
            record_audit_entry(
                self,
                operation=f"project_billing.{operation}",
                entity_type=type(entity).__name__,
                entity_id=entity.id,
                entity_parent_id=entity.project_id,
                module="project_management",
                old_value=None,
                new_value=json.dumps({"project_id": entity.project_id}, sort_keys=True),
                workspace_id=entity.project_id,
                source="application",
                severity="high",
                compliance_tag="financial",
                metadata={"action": operation},
                commit=False,
                fail_closed=True,
            )
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise
        domain_events.billing_preparations_changed.emit(entity.project_id)
        return entity


__all__ = ["ProjectBillingProfileService"]

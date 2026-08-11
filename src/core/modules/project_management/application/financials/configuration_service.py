from __future__ import annotations

import json
from dataclasses import replace
from datetime import date, datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.core.modules.project_management.application.common.module_guard import (
    ProjectManagementModuleGuardMixin,
)
from src.core.modules.project_management.contracts.repositories.financial_configuration import (
    ProjectCostCodeRepository,
    ProjectFinancialProfileRepository,
)
from src.core.modules.project_management.contracts.repositories.project import ProjectRepository
from src.core.modules.project_management.domain.financials.configuration import (
    BillingMethod,
    BudgetControlMode,
    CostCodePolicy,
    FinancialProfileStatus,
    ProjectCostCode,
    ProjectCostCodeRestriction,
    ProjectFinancialProfile,
)
from src.core.modules.project_management.access.scope_permissions import require_project_permission
from src.core.platform.application.security.authorization.enforcement.permission_checks import require_permission
from src.core.platform.common.exceptions import (
    BusinessRuleError,
    ConcurrencyError,
    NotFoundError,
    ValidationError,
)
from src.core.platform.application.tenant.tenancy.tenant_context import TenantContextService
from src.core.shared.audit import record_audit_entry


_UNSET = object()


class FinancialConfigurationService(ProjectManagementModuleGuardMixin):
    """Governed Project Finance profile and cost-code configuration."""

    def __init__(
        self,
        *,
        session: Session,
        profile_repo: ProjectFinancialProfileRepository,
        cost_code_repo: ProjectCostCodeRepository,
        project_repo: ProjectRepository,
        user_session=None,
        enterprise_audit_service=None,
        module_catalog_service=None,
        tenant_context_service: TenantContextService | None = None,
    ) -> None:
        self._session = session
        self._profile_repo = profile_repo
        self._cost_code_repo = cost_code_repo
        self._project_repo = project_repo
        self._user_session = user_session
        self._enterprise_audit_service = enterprise_audit_service
        self._module_catalog_service = module_catalog_service
        self._tenant_context_service = tenant_context_service

    def get_profile(self, project_id: str) -> ProjectFinancialProfile:
        self._require_project(project_id, "finance.read", "view financial profile")
        profile = self._profile_repo.get_by_project(project_id)
        if profile is None:
            raise NotFoundError(
                "Project financial profile not found.",
                code="FINANCIAL_PROFILE_NOT_FOUND",
            )
        return profile

    def configure_profile(
        self,
        project_id: str,
        *,
        expected_version: int,
        currency_code: str | object = _UNSET,
        billing_method: BillingMethod | str | object = _UNSET,
        budget_control_mode: BudgetControlMode | str | object = _UNSET,
        cost_code_policy: CostCodePolicy | str | object = _UNSET,
        financial_start_date: date | None | object = _UNSET,
        financial_end_date: date | None | object = _UNSET,
        is_funded: bool | object = _UNSET,
        is_billable: bool | object = _UNSET,
        default_cost_code_id: str | None | object = _UNSET,
    ) -> ProjectFinancialProfile:
        self._require_project(project_id, "finance.manage", "configure financial profile")
        current = self._require_profile(project_id)
        self._require_expected_version(current.version, expected_version, "Financial profile")
        values = {
            "updated_at": datetime.now(timezone.utc),
            "currency_code": current.currency_code if currency_code is _UNSET else currency_code,
            "billing_method": current.billing_method if billing_method is _UNSET else billing_method,
            "budget_control_mode": (
                current.budget_control_mode
                if budget_control_mode is _UNSET
                else budget_control_mode
            ),
            "cost_code_policy": (
                current.cost_code_policy if cost_code_policy is _UNSET else cost_code_policy
            ),
            "financial_start_date": (
                current.financial_start_date
                if financial_start_date is _UNSET
                else financial_start_date
            ),
            "financial_end_date": (
                current.financial_end_date
                if financial_end_date is _UNSET
                else financial_end_date
            ),
            "is_funded": current.is_funded if is_funded is _UNSET else is_funded,
            "is_billable": current.is_billable if is_billable is _UNSET else is_billable,
            "default_cost_code_id": (
                current.default_cost_code_id
                if default_cost_code_id is _UNSET
                else default_cost_code_id
            ),
        }
        candidate = replace(current, **values)
        if (
            candidate.cost_code_policy == CostCodePolicy.RESTRICTED
            and candidate.default_cost_code_id
            and candidate.default_cost_code_id
            not in {
                row.cost_code_id
                for row in self._cost_code_repo.list_restrictions(project_id)
            }
        ):
            raise BusinessRuleError(
                "The default cost code must be in the project's restricted allow-list.",
                code="PROJECT_DEFAULT_COST_CODE_NOT_ALLOWED",
            )
        self._profile_repo.update(candidate)
        self._record_profile_audit("update", candidate, old=current)
        self._commit()
        return candidate

    def transition_profile(
        self,
        project_id: str,
        *,
        target: FinancialProfileStatus | str,
        expected_version: int,
    ) -> ProjectFinancialProfile:
        self._require_project(project_id, "finance.manage", "transition financial profile")
        current = self._require_profile(project_id)
        self._require_expected_version(current.version, expected_version, "Financial profile")
        resolved_target = FinancialProfileStatus(target)
        if resolved_target == current.status:
            return current
        candidate = replace(current)
        candidate.transition_to(resolved_target)
        self._profile_repo.update(candidate)
        self._record_profile_audit("transition", candidate, old=current)
        self._commit()
        return candidate

    def list_cost_codes(self, *, include_inactive: bool = False) -> list[ProjectCostCode]:
        require_permission(
            self._user_session,
            "finance.read",
            operation_label="list project cost codes",
        )
        return self._cost_code_repo.list(include_inactive=include_inactive)

    def list_available_cost_codes(
        self,
        project_id: str,
        *,
        effective_on: date | None = None,
    ) -> list[ProjectCostCode]:
        self._require_project(project_id, "finance.read", "list available project cost codes")
        profile = self._require_profile(project_id)
        rows = self._cost_code_repo.list(include_inactive=False)
        if profile.cost_code_policy == CostCodePolicy.RESTRICTED:
            allowed_ids = {
                row.cost_code_id for row in self._cost_code_repo.list_restrictions(project_id)
            }
            rows = [row for row in rows if row.id in allowed_ids]
        as_of = effective_on or date.today()
        return [row for row in rows if row.is_effective_on(as_of)]

    def create_cost_code(
        self,
        *,
        code: str,
        name: str,
        description: str = "",
        parent_id: str | None = None,
        external_system: str | None = None,
        external_reference: str | None = None,
        effective_from: date | None = None,
        effective_to: date | None = None,
    ) -> ProjectCostCode:
        require_permission(
            self._user_session,
            "finance.manage",
            operation_label="create project cost code",
        )
        context = self._require_context("create project cost code")
        cost_code = ProjectCostCode.create(
            tenant_id=context.tenant_id,
            organization_id=context.organization_id,
            code=code,
            name=name,
            description=description,
            parent_id=parent_id,
            external_system=external_system,
            external_reference=external_reference,
            effective_from=effective_from,
            effective_to=effective_to,
        )
        self._ensure_parent_is_acyclic(cost_code.id, cost_code.parent_id)
        self._cost_code_repo.add(cost_code)
        self._record_cost_code_audit("create", cost_code)
        self._commit(duplicate_message=f"Cost code '{cost_code.code}' already exists.")
        return cost_code

    def update_cost_code(
        self,
        cost_code_id: str,
        *,
        expected_version: int,
        code: str | object = _UNSET,
        name: str | object = _UNSET,
        description: str | object = _UNSET,
        parent_id: str | None | object = _UNSET,
        external_system: str | None | object = _UNSET,
        external_reference: str | None | object = _UNSET,
        effective_from: date | None | object = _UNSET,
        effective_to: date | None | object = _UNSET,
    ) -> ProjectCostCode:
        require_permission(
            self._user_session,
            "finance.manage",
            operation_label="update project cost code",
        )
        current = self._require_cost_code(cost_code_id)
        self._require_expected_version(current.version, expected_version, "Cost code")
        candidate = replace(
            current,
            code=current.code if code is _UNSET else code,
            name=current.name if name is _UNSET else name,
            description=current.description if description is _UNSET else description,
            parent_id=current.parent_id if parent_id is _UNSET else parent_id,
            external_system=(
                current.external_system if external_system is _UNSET else external_system
            ),
            external_reference=(
                current.external_reference
                if external_reference is _UNSET
                else external_reference
            ),
            effective_from=(
                current.effective_from if effective_from is _UNSET else effective_from
            ),
            effective_to=current.effective_to if effective_to is _UNSET else effective_to,
            updated_at=datetime.now(timezone.utc),
        )
        self._ensure_parent_is_acyclic(
            candidate.id,
            candidate.parent_id,
            require_active_ancestors=candidate.is_active,
        )
        self._cost_code_repo.update(candidate)
        self._record_cost_code_audit("update", candidate, old=current)
        self._commit(duplicate_message=f"Cost code '{candidate.code}' already exists.")
        return candidate

    def deactivate_cost_code(
        self,
        cost_code_id: str,
        *,
        expected_version: int,
    ) -> ProjectCostCode:
        require_permission(
            self._user_session,
            "finance.manage",
            operation_label="deactivate project cost code",
        )
        current = self._require_cost_code(cost_code_id)
        self._require_expected_version(current.version, expected_version, "Cost code")
        if not current.is_active:
            return current
        if any(
            row.is_active and row.parent_id == current.id
            for row in self._cost_code_repo.list(include_inactive=True)
        ):
            raise BusinessRuleError(
                "Deactivate active child cost codes first.",
                code="PROJECT_COST_CODE_HAS_ACTIVE_CHILDREN",
            )
        if self._cost_code_repo.is_default_for_any_profile(current.id):
            raise BusinessRuleError(
                "Cost code is a project default and cannot be deactivated.",
                code="PROJECT_COST_CODE_IS_DEFAULT",
            )
        candidate = replace(
            current,
            is_active=False,
            updated_at=datetime.now(timezone.utc),
        )
        self._cost_code_repo.update(candidate)
        self._record_cost_code_audit("deactivate", candidate, old=current)
        self._commit()
        return candidate

    def activate_cost_code(
        self,
        cost_code_id: str,
        *,
        expected_version: int,
    ) -> ProjectCostCode:
        require_permission(
            self._user_session,
            "finance.manage",
            operation_label="activate project cost code",
        )
        current = self._require_cost_code(cost_code_id)
        self._require_expected_version(current.version, expected_version, "Cost code")
        if current.is_active:
            return current
        self._ensure_parent_is_acyclic(current.id, current.parent_id)
        candidate = replace(
            current,
            is_active=True,
            updated_at=datetime.now(timezone.utc),
        )
        self._cost_code_repo.update(candidate)
        self._record_cost_code_audit("activate", candidate, old=current)
        self._commit()
        return candidate

    def add_project_cost_code(
        self,
        *,
        project_id: str,
        cost_code_id: str,
    ) -> ProjectCostCodeRestriction:
        self._require_project(project_id, "finance.manage", "restrict project cost codes")
        existing = {
            row.cost_code_id: row
            for row in self._cost_code_repo.list_restrictions(project_id)
        }
        if cost_code_id in existing:
            return existing[cost_code_id]
        context = self._require_context("restrict project cost codes")
        restriction = ProjectCostCodeRestriction.create(
            tenant_id=context.tenant_id,
            organization_id=context.organization_id,
            project_id=project_id,
            cost_code_id=cost_code_id,
        )
        self._cost_code_repo.add_restriction(restriction)
        self._record_restriction_audit("create", restriction)
        self._commit(duplicate_message="Cost code is already assigned to this project.")
        return restriction

    def remove_project_cost_code(self, *, project_id: str, cost_code_id: str) -> bool:
        self._require_project(
            project_id,
            "finance.manage",
            "remove project cost-code restriction",
        )
        restrictions = self._cost_code_repo.list_restrictions(project_id)
        current = next((row for row in restrictions if row.cost_code_id == cost_code_id), None)
        if current is None:
            return False
        profile = self._require_profile(project_id)
        if profile.default_cost_code_id == cost_code_id:
            raise BusinessRuleError(
                "The project default cost code cannot be removed.",
                code="PROJECT_COST_CODE_IS_DEFAULT",
            )
        self._cost_code_repo.remove_restriction(
            project_id=project_id,
            cost_code_id=cost_code_id,
        )
        self._record_restriction_audit("delete", current)
        self._commit()
        return True

    def _require_project(self, project_id: str, permission: str, operation: str):
        require_permission(self._user_session, permission, operation_label=operation)
        project = self._project_repo.get(project_id)
        if project is None:
            raise NotFoundError("Project not found.")
        require_project_permission(
            self._user_session,
            project_id,
            permission,
            operation_label=operation,
        )
        return project

    def _require_profile(self, project_id: str) -> ProjectFinancialProfile:
        profile = self._profile_repo.get_by_project(project_id)
        if profile is None:
            raise NotFoundError(
                "Project financial profile not found.",
                code="FINANCIAL_PROFILE_NOT_FOUND",
            )
        return profile

    def _require_cost_code(self, cost_code_id: str) -> ProjectCostCode:
        cost_code = self._cost_code_repo.get(cost_code_id)
        if cost_code is None:
            raise NotFoundError("Project cost code not found.")
        return cost_code

    def _require_context(self, operation: str):
        if self._tenant_context_service is None:
            raise BusinessRuleError(
                f"Active organization context is required to {operation}.",
                code="TENANT_CONTEXT_REQUIRED",
            )
        return self._tenant_context_service.require_organization_context(
            operation_label=operation
        )

    @staticmethod
    def _require_expected_version(actual: int, expected: int, label: str) -> None:
        if actual != expected:
            raise ConcurrencyError(
                f"{label} changed since you opened it. Refresh and try again.",
                code="STALE_WRITE",
            )

    def _ensure_parent_is_acyclic(
        self,
        cost_code_id: str,
        parent_id: str | None,
        *,
        require_active_ancestors: bool = True,
    ) -> None:
        visited = {cost_code_id}
        cursor = parent_id
        while cursor:
            if cursor in visited:
                raise BusinessRuleError(
                    "Cost-code hierarchy cannot contain a cycle.",
                    code="PROJECT_COST_CODE_HIERARCHY_CYCLE",
                )
            visited.add(cursor)
            parent = self._cost_code_repo.get(cursor)
            if parent is None:
                raise NotFoundError("Parent project cost code not found.")
            if require_active_ancestors and not parent.is_active:
                raise BusinessRuleError(
                    "An active cost code requires active ancestors.",
                    code="PROJECT_COST_CODE_PARENT_INACTIVE",
                )
            cursor = parent.parent_id

    def _record_profile_audit(
        self,
        operation: str,
        profile: ProjectFinancialProfile,
        *,
        old: ProjectFinancialProfile | None = None,
    ) -> None:
        self._record_audit(
            operation=f"financial_profile.{operation}",
            entity_type="project_financial_profile",
            entity_id=profile.id,
            project_id=profile.project_id,
            old_value=self._profile_audit_value(old),
            new_value=self._profile_audit_value(profile),
        )

    def _record_cost_code_audit(
        self,
        operation: str,
        cost_code: ProjectCostCode,
        *,
        old: ProjectCostCode | None = None,
    ) -> None:
        self._record_audit(
            operation=f"project_cost_code.{operation}",
            entity_type="project_cost_code",
            entity_id=cost_code.id,
            project_id=None,
            old_value=self._cost_code_audit_value(old),
            new_value=self._cost_code_audit_value(cost_code),
        )

    def _record_restriction_audit(
        self,
        operation: str,
        restriction: ProjectCostCodeRestriction,
    ) -> None:
        self._record_audit(
            operation=f"project_cost_code_restriction.{operation}",
            entity_type="project_cost_code_restriction",
            entity_id=restriction.id,
            project_id=restriction.project_id,
            old_value=None,
            new_value=(
                None
                if operation == "delete"
                else json.dumps({"cost_code_id": restriction.cost_code_id}, sort_keys=True)
            ),
        )

    def _record_audit(
        self,
        *,
        operation: str,
        entity_type: str,
        entity_id: str,
        project_id: str | None,
        old_value: str | None,
        new_value: str | None,
    ) -> None:
        record_audit_entry(
            self,
            operation=operation,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_parent_id=project_id,
            module="project_management",
            old_value=old_value,
            new_value=new_value,
            workspace_id=project_id,
            source="application",
            severity="high",
            compliance_tag="financial",
            metadata={"action": operation},
            commit=False,
            fail_closed=True,
        )

    @staticmethod
    def _profile_audit_value(profile: ProjectFinancialProfile | None) -> str | None:
        if profile is None:
            return None
        return json.dumps(
            {
                "billing_method": profile.billing_method.value,
                "budget_control_mode": profile.budget_control_mode.value,
                "cost_code_policy": profile.cost_code_policy.value,
                "currency_code": profile.currency_code,
                "default_cost_code_id": profile.default_cost_code_id,
                "financial_end_date": (
                    profile.financial_end_date.isoformat()
                    if profile.financial_end_date
                    else None
                ),
                "financial_start_date": (
                    profile.financial_start_date.isoformat()
                    if profile.financial_start_date
                    else None
                ),
                "is_billable": profile.is_billable,
                "is_funded": profile.is_funded,
                "status": profile.status.value,
                "version": profile.version,
            },
            sort_keys=True,
        )

    @staticmethod
    def _cost_code_audit_value(cost_code: ProjectCostCode | None) -> str | None:
        if cost_code is None:
            return None
        return json.dumps(
            {
                "code": cost_code.code,
                "effective_from": (
                    cost_code.effective_from.isoformat() if cost_code.effective_from else None
                ),
                "effective_to": (
                    cost_code.effective_to.isoformat() if cost_code.effective_to else None
                ),
                "external_reference": cost_code.external_reference,
                "external_system": cost_code.external_system,
                "is_active": cost_code.is_active,
                "name": cost_code.name,
                "parent_id": cost_code.parent_id,
                "version": cost_code.version,
            },
            sort_keys=True,
        )

    def _commit(self, *, duplicate_message: str | None = None) -> None:
        try:
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            if duplicate_message:
                raise ValidationError(
                    duplicate_message,
                    code="PROJECT_FINANCE_CONFIGURATION_DUPLICATE",
                ) from exc
            raise
        except Exception:
            self._session.rollback()
            raise


__all__ = ["FinancialConfigurationService"]

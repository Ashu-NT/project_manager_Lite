from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.core.modules.project_management.access.scope_permissions import (
    require_project_permission,
)
from src.core.modules.project_management.application.common.module_guard import (
    ProjectManagementModuleGuardMixin,
)
from src.core.modules.project_management.application.financials.configuration._command_values import (
    PROFILE_FIELD_UNSET as _UNSET,
)
from src.core.modules.project_management.application.financials.configuration.dto.commands.financial_profile import (
    FinancialTransitionProfileCommand,
    FinancialUpdateProfileCommand,
)
from src.core.modules.project_management.application.financials.configuration.events import (
    ProjectFinancialProfileTransitioned,
    ProjectFinancialProfileUpdated,
)
from src.core.modules.project_management.contracts.repositories.finance.configuration.financial_configuration import (
    ProjectCostCodeRepository,
    ProjectFinancialProfileRepository,
)
from src.core.modules.project_management.contracts.repositories.projects.project import (
    ProjectRepository,
)
from src.core.modules.project_management.domain.financials.configuration import (
    CostCodePolicy,
    FinancialProfileStatus,
    ProjectCostCode,
    ProjectFinancialProfile,
)
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)
from src.core.platform.common.exceptions import (
    BusinessRuleError,
    ConcurrencyError,
    NotFoundError,
    ValidationError,
)
from src.core.shared.activity import record_activity
from src.core.shared.audit import record_audit_entry


class FinancialProfileCommandHandler(ProjectManagementModuleGuardMixin):
    """Governed profile mutations in the caller's transaction."""

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
        record_event: Callable[[object], None] | None = None,
    ) -> None:
        self._session = session
        self._profile_repo = profile_repo
        self._cost_code_repo = cost_code_repo
        self._project_repo = project_repo
        self._user_session = user_session
        self._enterprise_audit_service = enterprise_audit_service
        self._module_catalog_service = module_catalog_service
        self._record_event = record_event

    def _emit(self, event: object) -> None:
        if self._record_event is not None:
            self._record_event(event)

    def configure_profile(self, command: FinancialUpdateProfileCommand) -> ProjectFinancialProfile:
        project_id = command.project_id
        expected_version = command.expected_version
        currency_code = command.currency_code
        billing_method = command.billing_method
        budget_control_mode = command.budget_control_mode
        cost_code_policy = command.cost_code_policy
        financial_start_date = command.financial_start_date
        financial_end_date = command.financial_end_date
        is_funded = command.is_funded
        is_billable = command.is_billable
        default_cost_code_id = command.default_cost_code_id
        self._require_project(project_id, "finance.manage", "configure financial profile")
        current = self._require_profile(project_id)
        self._require_expected_version(current.version, expected_version, "Financial profile")
        values: dict[str, Any] = {
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
        if candidate.default_cost_code_id:
            default_cost_code = self._require_cost_code(candidate.default_cost_code_id)
            if not default_cost_code.is_effective_on(date.today()):  # noqa: DTZ011 -- naive local business date by design
                raise BusinessRuleError(
                    "The default cost code must be active and effective today.",
                    code="PROJECT_DEFAULT_COST_CODE_NOT_EFFECTIVE",
                )
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
        if candidate == current:
            # True no-op: no write, audit, event, or version bump.
            return current
        now = datetime.now(UTC)
        candidate = replace(candidate, updated_at=now)
        self._profile_repo.update(candidate)
        self._record_profile_audit("update", candidate, old=current)
        self._flush()
        self._emit(
            ProjectFinancialProfileUpdated(
                tenant_id=candidate.tenant_id,
                organization_id=candidate.organization_id,
                project_id=candidate.project_id,
                occurred_at=now,
            )
        )
        return candidate

    def transition_profile(self, command: FinancialTransitionProfileCommand) -> ProjectFinancialProfile:
        project_id = command.project_id
        target = command.target_status
        expected_version = command.expected_version
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
        self._flush()
        self._emit(
            ProjectFinancialProfileTransitioned(
                tenant_id=candidate.tenant_id,
                organization_id=candidate.organization_id,
                project_id=candidate.project_id,
                status=candidate.status.value,
                occurred_at=datetime.now(UTC),
            )
        )
        return candidate

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

    @staticmethod
    def _require_expected_version(actual: int, expected: int, label: str) -> None:
        if actual != expected:
            raise ConcurrencyError(
                f"{label} changed since you opened it. Refresh and try again.",
                code="STALE_WRITE",
            )

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
            before_data=self._profile_audit_value(old),
            after_data=self._profile_audit_value(profile),
        )

    def _record_audit(
        self,
        *,
        operation: str,
        entity_type: str,
        entity_id: str,
        project_id: str | None,
        before_data: dict[str, Any] | None,
        after_data: dict[str, Any] | None,
    ) -> None:
        record_audit_entry(
            self,
            operation=operation,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_parent_id=project_id,
            module="project_management",
            category="FINANCIAL",
            before_data=before_data,
            after_data=after_data,
            workspace_id=project_id,
            source="application",
            severity="high",
            metadata={"action": operation},
            commit=False,
            fail_closed=True,
        )
        record_activity(
            self,
            action=operation,
            entity_type=entity_type,
            entity_id=entity_id,
            parent_entity_id=project_id,
            module="project_management",
            workspace_id=project_id,
            details={"action": operation},
            commit=False,
        )

    @staticmethod
    def _profile_audit_value(profile: ProjectFinancialProfile | None) -> dict[str, Any] | None:
        if profile is None:
            return None
        return {
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
        }

    def _flush(self, *, duplicate_message: str | None = None) -> None:
        try:
            self._session.flush()
        except IntegrityError as exc:
            if duplicate_message:
                raise ValidationError(
                    duplicate_message,
                    code="PROJECT_FINANCE_CONFIGURATION_DUPLICATE",
                ) from exc
            raise


__all__ = ["FinancialProfileCommandHandler"]

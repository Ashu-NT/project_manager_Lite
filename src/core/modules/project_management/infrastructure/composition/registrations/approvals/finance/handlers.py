from __future__ import annotations

from src.core.modules.project_management.infrastructure.approval.billing_preparation_apply_participant import (
    BillingPreparationApprovalParticipant,
)
from src.core.modules.project_management.infrastructure.approval.budget_apply_participant import (
    BudgetApprovalParticipant,
)
from src.core.modules.project_management.infrastructure.approval.financial_change_apply_participant import (
    FinancialChangeApprovalParticipant,
)
from src.core.modules.project_management.infrastructure.approval.forecast_apply_participant import (
    ForecastApprovalParticipant,
)
from src.core.modules.project_management.infrastructure.approval.project_cost_apply_participant import (
    ProjectCostApprovalParticipant,
)
from src.core.modules.project_management.infrastructure.composition.registrations.approvals.finance.billing_preparation import (
    build_billing_preparation_approval_deps,
)
from src.core.modules.project_management.infrastructure.composition.registrations.approvals.finance.budget import (
    build_budget_approval_deps,
)
from src.core.modules.project_management.infrastructure.composition.registrations.approvals.finance.financial_change import (
    build_financial_change_approval_deps,
)
from src.core.modules.project_management.infrastructure.composition.registrations.approvals.finance.forecast import (
    build_forecast_approval_deps,
)
from src.core.modules.project_management.infrastructure.composition.registrations.approvals.finance.project_cost import (
    build_project_cost_approval_deps,
)


def register_finance_approval_handlers(
    *,
    register_apply,
    approval_service,
    user_session,
    tenant_context_service,
    module_catalog_service,
    work_calendar_engine,
    financial_period_service,
) -> None:
    budget_participant = BudgetApprovalParticipant()
    budget_dependencies_factory = lambda uow_session: build_budget_approval_deps(
        uow_session,
        user_session=user_session,
        tenant_context_service=tenant_context_service,
        module_catalog_service=module_catalog_service,
    )
    register_apply(
        "budget.approve",
        budget_participant.apply,
        dependencies_factory=budget_dependencies_factory,
    )
    approval_service.register_reject_handler(
        "budget.approve",
        budget_participant.reject,
        dependencies_factory=budget_dependencies_factory,
    )

    forecast_participant = ForecastApprovalParticipant()
    forecast_dependencies_factory = lambda uow_session: build_forecast_approval_deps(
        uow_session,
        user_session=user_session,
        tenant_context_service=tenant_context_service,
        module_catalog_service=module_catalog_service,
    )
    register_apply(
        "forecast.approve",
        forecast_participant.apply,
        dependencies_factory=forecast_dependencies_factory,
    )
    approval_service.register_reject_handler(
        "forecast.approve",
        forecast_participant.reject,
        dependencies_factory=forecast_dependencies_factory,
    )

    project_cost_participant = ProjectCostApprovalParticipant()
    project_cost_dependencies_factory = lambda uow_session: build_project_cost_approval_deps(
        uow_session,
        user_session=user_session,
        tenant_context_service=tenant_context_service,
        financial_period_service=financial_period_service,
        module_catalog_service=module_catalog_service,
    )
    register_apply(
        "project_cost.approve",
        project_cost_participant.apply,
        dependencies_factory=project_cost_dependencies_factory,
    )
    approval_service.register_reject_handler(
        "project_cost.approve",
        project_cost_participant.reject,
        dependencies_factory=project_cost_dependencies_factory,
    )

    financial_change_participant = FinancialChangeApprovalParticipant()
    financial_change_dependencies_factory = lambda uow_session: build_financial_change_approval_deps(
        uow_session,
        user_session=user_session,
        tenant_context_service=tenant_context_service,
        work_calendar_engine=work_calendar_engine,
        module_catalog_service=module_catalog_service,
    )
    register_apply(
        "financial_change.apply",
        financial_change_participant.apply,
        dependencies_factory=financial_change_dependencies_factory,
    )
    approval_service.register_reject_handler(
        "financial_change.apply",
        financial_change_participant.reject,
        dependencies_factory=financial_change_dependencies_factory,
    )

    billing_preparation_participant = BillingPreparationApprovalParticipant()
    billing_preparation_dependencies_factory = (
        lambda uow_session: build_billing_preparation_approval_deps(
            uow_session,
            user_session=user_session,
            tenant_context_service=tenant_context_service,
            module_catalog_service=module_catalog_service,
        )
    )
    register_apply(
        "project_billing_preparation.approve",
        billing_preparation_participant.apply,
        dependencies_factory=billing_preparation_dependencies_factory,
    )
    approval_service.register_reject_handler(
        "project_billing_preparation.approve",
        billing_preparation_participant.reject,
        dependencies_factory=billing_preparation_dependencies_factory,
    )


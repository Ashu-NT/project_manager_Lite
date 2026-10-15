from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from src.core.modules.project_management.api.desktop.financials.api import (
    ProjectManagementFinancialsDesktopApi,
)
from src.core.modules.project_management.contracts.reads.financials.commercial_metric_availability import (
    CommercialMetricAvailability,
)
from src.core.modules.project_management.domain.financials.billing_preparation import (
    BillingExternalEventType,
    BillingPreparationStatus,
)
from src.core.platform.common.exceptions import BusinessRuleError
from src.tests.project_management.application.test_p39_finance_billing_full_modernization import (
    _login,
    _ready_schedule_line,
    _setup_billable_project,
    _submitted_preparation,
)
from src.tests.project_management.application.test_project_finance_profitability_projection import (
    _approve_forecast_with_etc,
    _create_billing_profile,
)
from src.tests.project_management.application.test_project_finance_profitability_projection import (
    _setup_billable_project as _setup_other_project,
)


def test_governed_golden_project_keeps_preparation_progress_separate_from_revenue(
    accounting_services, accounting_outcome):
    services = accounting_services
    _, project, cost_code = _setup_billable_project(services)
    profile, schedule = _ready_schedule_line(services, project, amount=Decimal(24000))
    _approve_forecast_with_etc(services, project.id, cost_code, etc_amount="30000")
    services['billing_preparation_query']
    reporting = services["profitability_report"]
    cutoff = date(2026, 8, 31)
    original = _submitted_preparation(services, project, schedule)
    request = services["approval_queries"].list_pending(project_id=project.id)[0]
    with pytest.raises(BusinessRuleError):
        services["approval_commands"].approve_and_apply(request.id)
    services["user_registration"].register_user(
        "golden-independent-reviewer", "StrongPass123", role_names=["approver"]
    )

    def approve(preparation_id):
        request = services["approval_queries"].list_pending(project_id=project.id)[0]
        _login(services, "golden-independent-reviewer", "StrongPass123")
        services["approval_commands"].approve_and_apply(
            request.id, note="Independent review"
        )
        _login(services, "admin", "ChangeMe123!")
        value = services['billing_preparation_query'].get_preparation(preparation_id)
        assert value.status is BillingPreparationStatus.APPROVED
        assert value.approved_by != value.created_by
        return value

    approved = approve(original.id)
    saved_lines = services['billing_preparation_query'].list_lines(approved.id)
    with pytest.raises(BusinessRuleError):
        services['finance_governance_commands'].billing_source(lambda handler: handler.remove_draft_line(
            approved.id,
            line_id=saved_lines[0].id,
            expected_row_version=approved.row_version,
        ))
    initial = services["profitability_report"].get_project_commercial_projection(project.id, as_of_date=cutoff)
    assert initial.approved_preparation_amount == Decimal(24000)
    assert (
        initial.forecast_revenue_at_completion
        == profile.contract_value
        == Decimal(50000)
    )
    assert initial.projected_margin_amount == Decimal(20000)
    assert initial.projected_margin_percent == Decimal(40)

    services['finance_governance_commands'].accounting_handoff(lambda handler: handler.request(approved.id, expected_row_version=approved.row_version))
    pending = services['billing_preparation_query'].get_preparation(approved.id)
    assert pending.status is BillingPreparationStatus.DELIVERY_PENDING
    assert pending.delivered_at is None
    # External evidence is injected at the existing gateway, not manufactured by PM.
    for event_type in (
        BillingExternalEventType.DELIVERY_ACCEPTED,
        BillingExternalEventType.RECONCILED,
    ):
        accounting_outcome(
            approved.id,
            outcome={"delivery_accepted": "acknowledged", "reconciled": "reconciled"}[event_type.value],
            event_id=f"golden-{event_type.value}",
            occurred_at=datetime(2026, 8, 25, tzinfo=UTC),
            reconciliation_reference="external-confirmation",
        )
    parent = services['billing_preparation_query'].get_preparation(approved.id)
    correction = services['finance_governance_commands'].billing_preparation(lambda handler: handler.create_preparation(
        project.id,
        preparation_number="GOLDEN-CORRECTION",
        period_start=date(2026, 8, 1),
        period_end=cutoff,
        idempotency_key="golden-correction",
        correction_of_preparation_id=parent.id,
    ))
    assert services['billing_preparation_query'].list_external_events(correction.id) == []
    _, other_project, _ = _setup_other_project(
        services, name="Other commercial scope", create_period=False
    )
    _create_billing_profile(services, other_project.id, contract_value=Decimal(1000))
    other = services['finance_governance_commands'].billing_preparation(lambda handler: handler.create_preparation(
        other_project.id,
        preparation_number="OTHER-PROJECT",
        period_start=date(2026, 8, 1),
        period_end=cutoff,
        idempotency_key="other-project-preparation",
    ))
    assert services['billing_preparation_query'].list_external_events(other.id) == []
    with pytest.raises(BusinessRuleError):
        services['finance_governance_commands'].billing_source(lambda handler: handler.add_fixed_price_source(
            correction.id,
            schedule_line_id=schedule.id,
            expected_row_version=correction.row_version,
        ))
    services['billing_profile_query']
    delta = services['finance_governance_commands'].billing_schedule(lambda handler: handler.add_schedule_line(
        project.id,
        name="Additional governed milestone",
        amount=Decimal(1000),
        due_date=cutoff,
    ))
    delta = services['finance_governance_commands'].billing_schedule(lambda handler: handler.mark_schedule_line_ready(
        delta.id, expected_row_version=delta.row_version
    ))
    services['finance_governance_commands'].billing_source(lambda handler: handler.add_fixed_price_source(
        correction.id,
        schedule_line_id=delta.id,
        expected_row_version=correction.row_version,
    ))
    correction = services['billing_preparation_query'].get_preparation(correction.id)
    services['finance_governance_commands'].billing_submission(lambda handler: handler.submit_preparation(
        correction.id, expected_row_version=correction.row_version
    ))
    approve(correction.id)
    assert services['billing_preparation_query'].get_preparation(parent.id) == parent
    assert services['billing_preparation_query'].list_lines(parent.id) == saved_lines
    result = services["profitability_report"].get_project_commercial_projection(project.id, as_of_date=cutoff)
    assert result.approved_preparation_amount == Decimal(25000)
    assert (
        result.forecast_revenue_at_completion == initial.forecast_revenue_at_completion
    )
    assert result.projected_margin_amount == initial.projected_margin_amount
    assert result.projected_margin_percent == initial.projected_margin_percent
    assert result.revenue_availability is CommercialMetricAvailability.AVAILABLE
    dto = ProjectManagementFinancialsDesktopApi(
        profitability_report=reporting
    ).get_commercial_projection(project.id, as_of_date=cutoff)
    assert (
        Decimal(dto.forecast_revenue_at_completion)
        == result.forecast_revenue_at_completion
    )
    assert (
        Decimal(dto.approved_preparation_amount) == result.approved_preparation_amount
    )
    assert Decimal(dto.projected_margin_amount) == result.projected_margin_amount
    assert not hasattr(dto, "externally_paid_amount")
    assert not hasattr(dto, "externally_invoiced_amount")

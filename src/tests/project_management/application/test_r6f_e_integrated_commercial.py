from datetime import date, datetime, timezone
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
    services,
):
    _, project, cost_code = _setup_billable_project(services)
    profile, schedule = _ready_schedule_line(services, project, amount=Decimal("24000"))
    _approve_forecast_with_etc(services, project.id, cost_code, etc_amount="30000")
    billing = services["billing_preparation_service"]
    reporting = services["reporting_service"]
    cutoff = date(2026, 8, 31)
    original = _submitted_preparation(services, project, schedule)
    request = services["approval_service"].list_pending(project_id=project.id)[0]
    with pytest.raises(BusinessRuleError):
        services["approval_service"].approve_and_apply(request.id)
    services["auth_service"].register_user(
        "golden-independent-reviewer", "StrongPass123", role_names=["approver"]
    )

    def approve(preparation_id):
        request = services["approval_service"].list_pending(project_id=project.id)[0]
        _login(services, "golden-independent-reviewer", "StrongPass123")
        services["approval_service"].approve_and_apply(
            request.id, note="Independent review"
        )
        _login(services, "admin", "ChangeMe123!")
        value = billing.get_preparation(preparation_id)
        assert value.status is BillingPreparationStatus.APPROVED
        assert value.approved_by != value.created_by
        return value

    approved = approve(original.id)
    saved_lines = billing.list_lines(approved.id)
    with pytest.raises(BusinessRuleError):
        billing.remove_draft_line(
            approved.id,
            line_id=saved_lines[0].id,
            expected_row_version=approved.row_version,
        )
    initial = reporting.get_project_commercial_projection(project.id, as_of_date=cutoff)
    assert initial.approved_preparation_amount == Decimal("24000")
    assert (
        initial.forecast_revenue_at_completion
        == profile.contract_value
        == Decimal("50000")
    )
    assert initial.projected_margin_amount == Decimal("20000")
    assert initial.projected_margin_percent == Decimal("40")

    billing.request_delivery(approved.id, expected_row_version=approved.row_version)
    pending = billing.get_preparation(approved.id)
    assert pending.status is BillingPreparationStatus.DELIVERY_PENDING
    assert pending.delivered_at is None
    # External evidence is injected at the existing gateway, not manufactured by PM.
    for event_type in (
        BillingExternalEventType.DELIVERY_ACCEPTED,
        BillingExternalEventType.RECONCILED,
    ):
        billing.record_external_outcome(
            approved.id,
            event_type=event_type,
            external_system="test-authoritative-accounting",
            external_status=event_type.value,
            idempotency_key=f"golden-{event_type.value}",
            occurred_at=datetime(2026, 8, 25, tzinfo=timezone.utc),
            reconciliation_reference="external-confirmation",
        )
    parent = billing.get_preparation(approved.id)
    correction = billing.create_preparation(
        project.id,
        preparation_number="GOLDEN-CORRECTION",
        period_start=date(2026, 8, 1),
        period_end=cutoff,
        idempotency_key="golden-correction",
        correction_of_preparation_id=parent.id,
    )
    with pytest.raises(BusinessRuleError) as replay_error:
        billing.record_external_outcome(
            correction.id,
            event_type=BillingExternalEventType.RECONCILED,
            external_system="test-authoritative-accounting",
            external_status="reconciled",
            idempotency_key="golden-reconciled",
            occurred_at=datetime(2026, 8, 25, tzinfo=timezone.utc),
        )
    assert replay_error.value.code == "BILLING_EXTERNAL_OUTCOME_SCOPE_MISMATCH"
    assert billing.list_external_events(correction.id) == []
    _, other_project, _ = _setup_other_project(
        services, name="Other commercial scope", create_period=False
    )
    _create_billing_profile(services, other_project.id, contract_value=Decimal("1000"))
    other = billing.create_preparation(
        other_project.id,
        preparation_number="OTHER-PROJECT",
        period_start=date(2026, 8, 1),
        period_end=cutoff,
        idempotency_key="other-project-preparation",
    )
    with pytest.raises(BusinessRuleError) as project_replay_error:
        billing.record_external_outcome(
            other.id,
            event_type=BillingExternalEventType.RECONCILED,
            external_system="test-authoritative-accounting",
            external_status="reconciled",
            idempotency_key="golden-reconciled",
            occurred_at=datetime(2026, 8, 25, tzinfo=timezone.utc),
        )
    assert project_replay_error.value.code == "BILLING_EXTERNAL_OUTCOME_SCOPE_MISMATCH"
    assert billing.list_external_events(other.id) == []
    with pytest.raises(BusinessRuleError):
        billing.add_fixed_price_source(
            correction.id,
            schedule_line_id=schedule.id,
            expected_row_version=correction.row_version,
        )
    schedule_service = services["billing_profile_service"]
    delta = schedule_service.add_schedule_line(
        project.id,
        name="Additional governed milestone",
        amount=Decimal("1000"),
        due_date=cutoff,
    )
    delta = schedule_service.mark_schedule_line_ready(
        delta.id, expected_row_version=delta.row_version
    )
    billing.add_fixed_price_source(
        correction.id,
        schedule_line_id=delta.id,
        expected_row_version=correction.row_version,
    )
    correction = billing.get_preparation(correction.id)
    billing.submit_preparation(
        correction.id, expected_row_version=correction.row_version
    )
    approve(correction.id)
    assert billing.get_preparation(parent.id) == parent
    assert billing.list_lines(parent.id) == saved_lines
    result = reporting.get_project_commercial_projection(project.id, as_of_date=cutoff)
    assert result.approved_preparation_amount == Decimal("25000")
    assert (
        result.forecast_revenue_at_completion == initial.forecast_revenue_at_completion
    )
    assert result.projected_margin_amount == initial.projected_margin_amount
    assert result.projected_margin_percent == initial.projected_margin_percent
    assert result.revenue_availability is CommercialMetricAvailability.AVAILABLE
    dto = ProjectManagementFinancialsDesktopApi(
        reporting_service=reporting
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

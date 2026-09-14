from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import event

from src.core.modules.project_management.api.desktop.financials.api import (
    ProjectManagementFinancialsDesktopApi,
)
from src.core.modules.project_management.api.desktop.financials.serializers.billing_workspace_serializer import (
    serialize_finance_billing_workspace,
)
from src.core.modules.project_management.domain.financials.billing_preparation import (
    BillingExternalEventType,
)
from src.core.modules.project_management.domain.financials.configuration import (
    BillingMethod,
)
from src.core.modules.project_management.domain.financials.forecast import (
    ForecastGenerationMode,
    ForecastLineSourceKind,
    ForecastLineSourceType,
)
from src.core.modules.project_management.infrastructure.persistence.orm.billing import (
    ProjectBillingPreparationORM,
)
from src.core.platform.common.exceptions import BusinessRuleError
from src.core.platform.domain.security.auth.session import UserSessionPrincipal


def _setup_billable_project(
    services,
    *,
    name: str = "Profitability Project",
    billing_method: BillingMethod = BillingMethod.FIXED_PRICE,
    create_period: bool = True,
):
    organization = services["tenant_context_service"].get_active_organization()
    project = services["project_service"].create_project(
        name, financial_currency_code=organization.base_currency
    )
    cost_code = services["financial_configuration_service"].create_cost_code(
        code=f"PROF-{project.id[-4:].upper()}", name="Profitability cost code"
    )
    if create_period:
        services["financial_period_service"].create_period(
            code="FY26-PROF",
            name="August 2026",
            fiscal_year=2026,
            period_number=8,
            start_date=date(2026, 8, 1),
            end_date=date(2026, 8, 31),
        )
    profile = services["financial_configuration_service"].get_profile(project.id)
    services["financial_configuration_service"].configure_profile(
        project.id,
        expected_version=profile.version,
        default_cost_code_id=cost_code.id,
        billing_method=billing_method,
        is_billable=True,
    )
    return organization, project, cost_code


def _create_billing_profile(
    services, project_id: str, *, contract_value: Decimal, activate: bool = True
):
    billing_profile_service = services["billing_profile_service"]
    profile = billing_profile_service.create_profile(
        project_id,
        contract_reference="CONTRACT-PROFIT",
        contract_value=contract_value,
        customer_party_id="party-1" if contract_value > 0 else None,
    )
    if activate:
        profile = billing_profile_service.activate_profile(
            project_id, expected_row_version=profile.row_version
        )
    return profile


def _approve_forecast_with_etc(services, project_id: str, cost_code, *, etc_amount: str):
    forecast_service = services["forecast_version_service"]
    forecast = forecast_service.create_forecast(
        project_id,
        name="Profitability forecast",
        as_of_date=date(2026, 8, 11),
        generation_mode=ForecastGenerationMode.MANUAL,
        created_by="admin",
    )
    forecast_service.add_line(
        forecast.id,
        cost_code_id=cost_code.id,
        description="Remaining cost estimate",
        amount=Decimal(etc_amount),
        source_kind=ForecastLineSourceKind.MANUAL,
        source_type=ForecastLineSourceType.MANUAL_ESTIMATE,
        created_by="admin",
        expected_forecast_version=forecast.row_version,
    )
    current = forecast_service.get_forecast(forecast.id)
    submitted = forecast_service.submit_forecast(
        forecast.id, submitted_by="admin", expected_version=current.row_version
    )
    return forecast_service.approve_forecast(
        forecast.id, approved_by="admin", expected_version=submitted.row_version
    )


def _register_and_login(services, username: str, *, role_names: list[str]) -> None:
    auth = services["auth_service"]
    auth.register_user(username, "StrongPass123", role_names=role_names)
    user = auth.authenticate(username, "StrongPass123")
    services["user_session"].set_principal(auth.build_principal(user))


def test_fixed_price_projected_margin_and_percent(services) -> None:
    _organization, project, cost_code = _setup_billable_project(
        services, billing_method=BillingMethod.FIXED_PRICE
    )
    _create_billing_profile(services, project.id, contract_value=Decimal("1000000"))
    _approve_forecast_with_etc(services, project.id, cost_code, etc_amount="720000")

    reporting = services["reporting_service"]
    projection = reporting.get_project_commercial_projection(project.id)

    assert projection.profitability_detail_included is True
    assert projection.revenue_basis == "contract_value"
    assert projection.forecast_revenue_at_completion == Decimal("1000000")
    assert projection.projected_margin_amount == Decimal("280000")
    assert projection.projected_margin_percent == pytest.approx(Decimal("28"))


def test_desktop_api_get_commercial_projection_serializes_service_result(services) -> None:
    _organization, project, cost_code = _setup_billable_project(
        services, billing_method=BillingMethod.FIXED_PRICE
    )
    _create_billing_profile(services, project.id, contract_value=Decimal("1000000"))
    _approve_forecast_with_etc(services, project.id, cost_code, etc_amount="720000")

    api = ProjectManagementFinancialsDesktopApi(reporting_service=services["reporting_service"])
    dto = api.get_commercial_projection(project.id)

    assert dto.project_id == project.id
    assert dto.profitability_detail_included is True
    assert dto.revenue_basis == "contract_value"
    assert Decimal(dto.contract_value) == Decimal("1000000")
    assert Decimal(dto.forecast_revenue_at_completion) == Decimal("1000000")
    assert Decimal(dto.projected_margin_amount) == Decimal("280000")
    assert Decimal(dto.projected_margin_percent) == pytest.approx(Decimal("28"))


def test_desktop_api_get_commercial_projection_without_reporting_service_returns_empty_dto() -> None:
    api = ProjectManagementFinancialsDesktopApi()

    dto = api.get_commercial_projection("any-project-id")

    assert dto.project_id == ""
    assert dto.contract_value == ""
    assert dto.approved_preparation_amount == "0"


def test_fixed_price_negative_margin_on_cost_overrun(services) -> None:
    _organization, project, cost_code = _setup_billable_project(
        services, billing_method=BillingMethod.FIXED_PRICE
    )
    _create_billing_profile(services, project.id, contract_value=Decimal("100000"))
    _approve_forecast_with_etc(services, project.id, cost_code, etc_amount="150000")

    reporting = services["reporting_service"]
    projection = reporting.get_project_commercial_projection(project.id)

    assert projection.projected_margin_amount == Decimal("-50000")
    assert projection.projected_margin_percent == pytest.approx(Decimal("-50"))


def test_commercial_as_of_and_zero_margin_are_explicit(services) -> None:
    _organization, project, cost_code = _setup_billable_project(services)
    _create_billing_profile(services, project.id, contract_value=Decimal("100"))
    _approve_forecast_with_etc(services, project.id, cost_code, etc_amount="100")
    api = ProjectManagementFinancialsDesktopApi(reporting_service=services["reporting_service"])

    before = api.get_commercial_projection(project.id, as_of_date=date(2026, 8, 10))
    after = api.get_commercial_projection(project.id, as_of_date=date(2026, 8, 31))
    repeated = api.get_commercial_projection(project.id, as_of_date=date(2026, 8, 31))

    assert Decimal(before.forecast_revenue_at_completion) == Decimal(100)
    assert before.projected_margin_amount == ""
    assert Decimal(after.forecast_revenue_at_completion) == Decimal(100)
    assert Decimal(after.projected_margin_amount) == Decimal(0)
    assert Decimal(after.projected_margin_percent) == Decimal(0)
    assert repeated == after


def test_zero_contract_value_gives_none_percent_not_divide_by_zero(services) -> None:
    _organization, project, cost_code = _setup_billable_project(
        services, billing_method=BillingMethod.FIXED_PRICE
    )
    _create_billing_profile(
        services, project.id, contract_value=Decimal("0"), activate=False
    )
    _approve_forecast_with_etc(services, project.id, cost_code, etc_amount="10000")

    reporting = services["reporting_service"]
    projection = reporting.get_project_commercial_projection(project.id)

    assert projection.forecast_revenue_at_completion == Decimal("0")
    assert projection.projected_margin_amount == Decimal("-10000")
    assert projection.projected_margin_percent is None


def test_time_and_materials_profitability_explicitly_unavailable(services) -> None:
    _organization, project, cost_code = _setup_billable_project(
        services, billing_method=BillingMethod.TIME_AND_MATERIALS
    )
    _create_billing_profile(services, project.id, contract_value=Decimal("500000"))
    _approve_forecast_with_etc(services, project.id, cost_code, etc_amount="300000")

    reporting = services["reporting_service"]
    projection = reporting.get_project_commercial_projection(project.id)

    assert projection.profitability_detail_included is True
    assert projection.revenue_basis == "unavailable_time_and_materials_forecast_billing"
    assert projection.forecast_revenue_at_completion is None
    assert projection.projected_margin_amount is None
    assert projection.projected_margin_percent is None
    # contract_value itself remains visible -- only repurposing it as revenue is withheld.
    assert projection.contract_value == Decimal("500000")


def test_cost_plus_profitability_explicitly_unavailable(services) -> None:
    _organization, project, cost_code = _setup_billable_project(
        services, billing_method=BillingMethod.COST_PLUS
    )
    _create_billing_profile(services, project.id, contract_value=Decimal("500000"))
    _approve_forecast_with_etc(services, project.id, cost_code, etc_amount="300000")

    reporting = services["reporting_service"]
    projection = reporting.get_project_commercial_projection(project.id)

    assert projection.revenue_basis == "unavailable_cost_plus_recoverability"
    assert projection.forecast_revenue_at_completion is None
    assert projection.projected_margin_amount is None
    assert projection.projected_margin_percent is None


def test_profitability_redacted_without_finance_read_profitability_permission(
    services,
) -> None:
    _organization, project, cost_code = _setup_billable_project(
        services, billing_method=BillingMethod.FIXED_PRICE
    )
    _create_billing_profile(services, project.id, contract_value=Decimal("1000000"))
    _approve_forecast_with_etc(services, project.id, cost_code, etc_amount="720000")

    _register_and_login(services, "profit-reader-nonsensitive", role_names=["project_manager"])
    reporting = services["reporting_service"]
    projection = reporting.get_project_commercial_projection(project.id)

    assert projection.profitability_detail_included is False
    assert projection.forecast_revenue_at_completion is None
    assert projection.revenue_basis == ""
    assert projection.projected_margin_amount is None
    assert projection.projected_margin_percent is None
    # Ordinary billing-progress figures remain visible under finance.read alone.
    assert projection.contract_value == Decimal("1000000")


def test_finance_read_profitability_allows_margin_detail(services) -> None:
    _organization, project, cost_code = _setup_billable_project(
        services, billing_method=BillingMethod.FIXED_PRICE
    )
    _create_billing_profile(services, project.id, contract_value=Decimal("1000000"))
    _approve_forecast_with_etc(services, project.id, cost_code, etc_amount="720000")

    _register_and_login(services, "profit-reader-sensitive", role_names=["finance_controller"])
    reporting = services["reporting_service"]
    projection = reporting.get_project_commercial_projection(project.id)

    assert projection.profitability_detail_included is True
    assert projection.projected_margin_amount == Decimal("280000")


def test_no_billing_profile_returns_empty_projection_without_error(services) -> None:
    organization = services["tenant_context_service"].get_active_organization()
    project = services["project_service"].create_project(
        "No Billing Profile", financial_currency_code=organization.base_currency
    )

    reporting = services["reporting_service"]
    projection = reporting.get_project_commercial_projection(project.id)

    assert projection.contract_value is None
    assert projection.approved_preparation_amount == Decimal("0")
    assert projection.projected_margin_amount is None


def test_project_scope_is_enforced(services) -> None:
    _organization, project_a, _cost_code = _setup_billable_project(
        services, name="Profitability Scope A"
    )
    _organization2, project_b, _cost_code_b = _setup_billable_project(
        services, name="Profitability Scope B", create_period=False
    )
    reporting = services["reporting_service"]

    tenant_id = services["user_session"].stored_active_tenant_id()
    organization_id = services["user_session"].stored_active_organization_id()
    from src.core.platform.domain.security.auth.session import UserSessionPrincipal

    services["auth_service"].register_user(
        "profit-scoped-to-a", "StrongPass123", role_names=["viewer"]
    )
    user = services["auth_service"].authenticate("profit-scoped-to-a", "StrongPass123")
    principal = services["auth_service"].build_principal(user)
    services["user_session"].set_principal(
        UserSessionPrincipal(
            user_id=principal.user_id,
            username=principal.username,
            display_name=principal.display_name,
            role_names=principal.role_names,
            permissions=frozenset({"finance.read"}),
            project_access={project_a.id: frozenset({"finance.read"})},
            active_tenant_id=tenant_id,
            active_organization_id=organization_id,
        )
    )

    assert reporting.get_project_commercial_projection(project_a.id) is not None
    with pytest.raises(BusinessRuleError, match="finance.read"):
        reporting.get_project_commercial_projection(project_b.id)


def test_external_events_do_not_manufacture_invoice_or_payment_amounts(services) -> None:
    _organization, project, cost_code = _setup_billable_project(
        services, billing_method=BillingMethod.FIXED_PRICE
    )
    _create_billing_profile(services, project.id, contract_value=Decimal("24000"))
    api_profile_service = services["billing_profile_service"]
    line = api_profile_service.add_schedule_line(
        project.id, name="Milestone 1", amount=Decimal("24000"), due_date=date(2026, 8, 20)
    )
    line = api_profile_service.mark_schedule_line_ready(
        line.id, expected_row_version=line.row_version
    )

    preparation_service = services["billing_preparation_service"]
    preparation = preparation_service.create_preparation(
        project.id,
        preparation_number="BP-PROFIT-0001",
        period_start=date(2026, 8, 1),
        period_end=date(2026, 8, 31),
        idempotency_key="billing-run-profitability",
    )
    preparation_service.add_fixed_price_source(
        preparation.id, schedule_line_id=line.id, expected_row_version=preparation.row_version
    )
    preparation = preparation_service.get_preparation(preparation.id)

    # Submit as a distinct requester, then decide as the default admin
    # session -- approve_and_apply forbids a principal deciding its own
    # governance request.
    _register_and_login(services, "profit-billing-requester", role_names=["finance_controller"])
    preparation_service.submit_preparation(
        preparation.id, expected_row_version=preparation.row_version
    )
    auth = services["auth_service"]
    admin = auth.authenticate("admin", "ChangeMe123!")
    services["user_session"].set_principal(auth.build_principal(admin))
    request = services["approval_service"].list_pending(project_id=project.id)[0]
    services["approval_service"].approve_and_apply(request.id, note="Approved for delivery")

    approved = preparation_service.get_preparation(preparation.id)
    preparation_service.request_delivery(
        approved.id, expected_row_version=approved.row_version
    )
    delivery_pending = preparation_service.get_preparation(approved.id)

    reporting = services["reporting_service"]
    before_events = reporting.get_project_commercial_projection(project.id)
    assert before_events.approved_preparation_amount == Decimal("24000")
    assert not hasattr(before_events, "externally_invoiced_amount")
    assert not hasattr(before_events, "externally_paid_amount")

    now = datetime(2026, 8, 21, tzinfo=timezone.utc)
    preparation_service.record_external_outcome(
        delivery_pending.id,
        event_type=BillingExternalEventType.DELIVERY_ACCEPTED,
        external_system="test-erp",
        external_status="accepted",
        idempotency_key="ext-evt-1",
        occurred_at=now,
        external_invoice_reference="INV-0001",
    )
    acknowledged = preparation_service.get_preparation(delivery_pending.id)

    after_invoice = reporting.get_project_commercial_projection(project.id)
    assert after_invoice.approved_preparation_amount == Decimal("24000")
    assert not hasattr(after_invoice, "externally_invoiced_amount")

    preparation_service.record_external_outcome(
        acknowledged.id,
        event_type=BillingExternalEventType.RECONCILED,
        external_system="test-erp",
        external_status="reconciled",
        idempotency_key="ext-evt-2",
        occurred_at=now,
        reconciliation_reference="RECON-0001",
    )

    after_reconciliation = reporting.get_project_commercial_projection(project.id)
    assert after_reconciliation.approved_preparation_amount == Decimal("24000")
    assert not hasattr(after_reconciliation, "externally_paid_amount")


def test_approved_preparation_amount_sums_distinct_governed_sources(services) -> None:
    _organization, project, cost_code = _setup_billable_project(
        services, billing_method=BillingMethod.FIXED_PRICE
    )
    _create_billing_profile(services, project.id, contract_value=Decimal("48000"))
    profile_service = services["billing_profile_service"]
    line_a = profile_service.add_schedule_line(
        project.id, name="Milestone A", amount=Decimal("24000"), due_date=date(2026, 8, 15)
    )
    line_a = profile_service.mark_schedule_line_ready(
        line_a.id, expected_row_version=line_a.row_version
    )
    line_b = profile_service.add_schedule_line(
        project.id, name="Milestone B", amount=Decimal("24000"), due_date=date(2026, 8, 25)
    )
    line_b = profile_service.mark_schedule_line_ready(
        line_b.id, expected_row_version=line_b.row_version
    )

    preparation_service = services["billing_preparation_service"]
    auth = services["auth_service"]
    auth.register_user(
        "profit-multi-requester", "StrongPass123", role_names=["finance_controller"]
    )

    def _govern(preparation_number, line, idempotency_key):
        # Create/add-source/submit as a distinct requester, then decide as
        # the default admin session -- approve_and_apply forbids a
        # principal deciding its own governance request.
        requester = auth.authenticate("profit-multi-requester", "StrongPass123")
        services["user_session"].set_principal(auth.build_principal(requester))
        preparation = preparation_service.create_preparation(
            project.id,
            preparation_number=preparation_number,
            period_start=date(2026, 8, 1),
            period_end=date(2026, 8, 31),
            idempotency_key=idempotency_key,
        )
        preparation_service.add_fixed_price_source(
            preparation.id, schedule_line_id=line.id, expected_row_version=preparation.row_version
        )
        preparation = preparation_service.get_preparation(preparation.id)
        preparation_service.submit_preparation(
            preparation.id, expected_row_version=preparation.row_version
        )
        admin = auth.authenticate("admin", "ChangeMe123!")
        services["user_session"].set_principal(auth.build_principal(admin))
        request = services["approval_service"].list_pending(project_id=project.id)[-1]
        services["approval_service"].approve_and_apply(request.id, note="Approved")
        return preparation_service.get_preparation(preparation.id)

    _govern("BP-PROFIT-A", line_a, "billing-run-a")
    _govern("BP-PROFIT-B", line_b, "billing-run-b")

    reporting = services["reporting_service"]
    projection = reporting.get_project_commercial_projection(project.id)
    assert projection.approved_preparation_amount == Decimal("48000")


def test_commercial_aggregate_is_bounded_and_nets_correction_history(services) -> None:
    _organization, project, _code = _setup_billable_project(services)
    _create_billing_profile(services, project.id, contract_value=Decimal("100"))
    preparation = services["billing_preparation_service"].create_preparation(
        project.id,
        preparation_number="BP-AGG-BASE",
        period_start=date(2026, 8, 1),
        period_end=date(2026, 8, 31),
        idempotency_key="bp-aggregate-base",
    )
    session = services["session"]
    original = session.get(ProjectBillingPreparationORM, preparation.id)
    original.status = "reconciled"
    original.total_amount = Decimal(100)
    original.line_count = 1
    session.flush()
    source = {
        column.key: getattr(original, column.key)
        for column in ProjectBillingPreparationORM.__table__.columns
    }

    def add_row(number: int, *, status: str, amount: str, correction: bool = False) -> None:
        values = dict(source)
        values.update(
            id=str(uuid4()),
            preparation_number=f"BP-AGG-{number}",
            idempotency_key=f"bp-aggregate-{number}",
            status=status,
            total_amount=Decimal(amount),
            correction_of_preparation_id=original.id if correction else None,
            approval_request_id=None,
        )
        session.add(ProjectBillingPreparationORM(**values))

    add_row(1, status="approved", amount="-20", correction=True)
    add_row(2, status="rejected", amount="50")
    add_row(3, status="cancelled", amount="50")
    session.commit()
    reporting = services["reporting_service"]

    def measured_projection():
        statements = []

        def count(_conn, _cursor, statement, _params, _context, _many):
            statements.append(statement)

        event.listen(session.bind, "before_cursor_execute", count)
        try:
            result = reporting.get_project_commercial_projection(
                project.id, as_of_date=date(2026, 8, 31)
            )
        finally:
            event.remove(session.bind, "before_cursor_execute", count)
        return result, len(statements)

    small, small_count = measured_projection()
    assert small.approved_preparation_amount == Decimal(80)
    for number in range(4, 124):
        add_row(number, status="approved", amount="1")
    session.commit()
    large, large_count = measured_projection()
    assert large.approved_preparation_amount == Decimal(200)
    assert large_count == small_count
    assert large_count <= 15


def test_billing_line_rate_evidence_is_redacted_without_sensitive_read(services) -> None:
    _organization, project, _code = _setup_billable_project(services)
    _create_billing_profile(services, project.id, contract_value=Decimal(100))
    schedule = services["billing_profile_service"].add_schedule_line(
        project.id, name="Accepted milestone", amount=Decimal(100), due_date=date(2026, 8, 20)
    )
    schedule = services["billing_profile_service"].mark_schedule_line_ready(
        schedule.id, expected_row_version=schedule.row_version
    )
    preparation = services["billing_preparation_service"].create_preparation(
        project.id, preparation_number="BP-REDACT", period_start=date(2026, 8, 1),
        period_end=date(2026, 8, 31), idempotency_key="bp-redaction",
    )
    services["billing_preparation_service"].add_fixed_price_source(
        preparation.id, schedule_line_id=schedule.id,
        expected_row_version=preparation.row_version,
    )
    query = services["finance_workspace_query"]
    visible = query.get_billing_read_workspace(project.id, selected_preparation_id=preparation.id)
    assert visible.lines.items[0].unit_rate == Decimal(100)

    auth = services["auth_service"]
    auth.register_user("commercial-reader", "StrongPass123", role_names=["viewer"])
    user = auth.authenticate("commercial-reader", "StrongPass123")
    principal = auth.build_principal(user)
    scope = services["tenant_context_service"].require_active_scope_ids(
        operation_label="billing redaction test"
    )
    services["user_session"].set_principal(UserSessionPrincipal(
        user_id=principal.user_id, username=principal.username,
        display_name=principal.display_name, role_names=principal.role_names,
        permissions=frozenset({"finance.read"}),
        project_access={project.id: frozenset({"finance.read"})},
        active_tenant_id=scope.tenant_id, active_organization_id=scope.organization_id,
    ))
    redacted = query.get_billing_read_workspace(project.id, selected_preparation_id=preparation.id)
    line = redacted.lines.items[0]
    assert line.net_amount == Decimal(100)
    assert line.unit_rate is None
    assert line.rate_line_id is None
    assert line.source_amount is None
    row = serialize_finance_billing_workspace(redacted).lines[0]
    assert row.state["unitRate"] == ""
    assert row.state["rateLineId"] == ""

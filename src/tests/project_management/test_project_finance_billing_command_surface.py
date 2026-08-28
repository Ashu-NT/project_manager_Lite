from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from src.core.platform.domain.security.auth.session import UserSessionPrincipal
from src.core.modules.project_management.api.desktop.financials.api import (
    ProjectManagementFinancialsDesktopApi,
)
from src.core.modules.project_management.api.desktop.financials.commands.billing import (
    FinancialActivateBillingProfileCommand,
    FinancialAddApprovedTimeBillingSourceCommand,
    FinancialAddBillingScheduleLineCommand,
    FinancialAddFixedPriceBillingSourceCommand,
    FinancialCreateBillingPreparationCommand,
    FinancialCreateBillingProfileCommand,
    FinancialMarkBillingScheduleLineReadyCommand,
    FinancialVersionedBillingPreparationCommand,
)
from src.core.modules.project_management.domain.financials.configuration import BillingMethod
from src.core.platform.common.exceptions import BusinessRuleError


def _build_api(services) -> ProjectManagementFinancialsDesktopApi:
    return ProjectManagementFinancialsDesktopApi(
        billing_profile_service=services["billing_profile_service"],
        billing_preparation_service=services["billing_preparation_service"],
    )


def _register_and_login(services, username: str, *, role_names: list[str]) -> None:
    auth = services["auth_service"]
    auth.register_user(username, "StrongPass123", role_names=role_names)
    user = auth.authenticate(username, "StrongPass123")
    services["user_session"].set_principal(auth.build_principal(user))


def _setup_billable_project(services, *, name: str = "Billing Command Surface", create_period: bool = True):
    organization = services["tenant_context_service"].get_active_organization()
    project = services["project_service"].create_project(
        name, financial_currency_code=organization.base_currency
    )
    cost_code = services["financial_configuration_service"].create_cost_code(
        code=f"BILL-{project.id[-4:].upper()}", name="Billing cost code"
    )
    if create_period:
        services["financial_period_service"].create_period(
            code="FY26-BILL",
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
        billing_method=BillingMethod.FIXED_PRICE,
        is_billable=True,
    )
    return organization, project, cost_code


def test_desktop_billing_profile_and_schedule_lifecycle(services) -> None:
    organization, project, _cost_code = _setup_billable_project(services)
    api = _build_api(services)

    profile = api.create_billing_profile(
        FinancialCreateBillingProfileCommand(
            project_id=project.id,
            contract_reference="CONTRACT-1",
            contract_value=Decimal("50000"),
            customer_party_id="party-1",
        )
    )
    assert profile.status == "draft"
    assert profile.customer_party_id == "party-1"
    assert profile.currency_code == organization.base_currency
    assert profile.row_version >= 1

    activated = api.activate_billing_profile(
        FinancialActivateBillingProfileCommand(
            project_id=project.id, expected_version=profile.row_version
        )
    )
    assert activated.status == "active"

    line = api.add_billing_schedule_line(
        FinancialAddBillingScheduleLineCommand(
            project_id=project.id,
            name="Milestone 1",
            amount=Decimal("24000"),
            due_date=date(2026, 8, 20),
        )
    )
    assert line.status == "planned"
    assert Decimal(line.amount) == Decimal("24000")

    ready = api.mark_billing_schedule_line_ready(
        FinancialMarkBillingScheduleLineReadyCommand(
            line_id=line.id, expected_version=line.row_version
        )
    )
    assert ready.status == "ready"


def test_desktop_billing_preparation_fixed_price_lifecycle_through_delivery_request(
    services,
) -> None:
    _organization, project, _cost_code = _setup_billable_project(services)
    api = _build_api(services)

    profile = api.create_billing_profile(
        FinancialCreateBillingProfileCommand(
            project_id=project.id,
            contract_reference="CONTRACT-2",
            contract_value=Decimal("24000"),
            customer_party_id="party-1",
        )
    )
    api.activate_billing_profile(
        FinancialActivateBillingProfileCommand(
            project_id=project.id, expected_version=profile.row_version
        )
    )
    line = api.add_billing_schedule_line(
        FinancialAddBillingScheduleLineCommand(
            project_id=project.id,
            name="Milestone 1",
            amount=Decimal("24000"),
            due_date=date(2026, 8, 20),
        )
    )
    line = api.mark_billing_schedule_line_ready(
        FinancialMarkBillingScheduleLineReadyCommand(
            line_id=line.id, expected_version=line.row_version
        )
    )

    preparation = api.create_billing_preparation(
        FinancialCreateBillingPreparationCommand(
            project_id=project.id,
            preparation_number="BP-2026-0001",
            period_start=date(2026, 8, 1),
            period_end=date(2026, 8, 31),
            idempotency_key="billing-run-2026-08",
        )
    )
    assert preparation.status == "draft"
    assert preparation.line_count == 0

    source_line = api.add_fixed_price_billing_source(
        FinancialAddFixedPriceBillingSourceCommand(
            preparation_id=preparation.id,
            expected_version=preparation.row_version,
            schedule_line_id=line.id,
        )
    )
    assert source_line.preparation_id == preparation.id
    assert Decimal(source_line.net_amount) == Decimal("24000")

    # Submit as a distinct requester, then decide as the default admin
    # session -- approve_and_apply forbids a principal deciding its own
    # governance request.
    _register_and_login(services, "billing-requester", role_names=["finance_controller"])
    submitted = api.submit_billing_preparation(
        FinancialVersionedBillingPreparationCommand(
            preparation_id=preparation.id, expected_version=preparation.row_version + 1
        )
    )
    assert submitted.status == "submitted"
    assert Decimal(submitted.total_amount) == Decimal("24000")

    auth = services["auth_service"]
    admin = auth.authenticate("admin", "ChangeMe123!")
    services["user_session"].set_principal(auth.build_principal(admin))
    request = services["approval_service"].list_pending(project_id=project.id)[0]
    services["approval_service"].approve_and_apply(request.id, note="Approved for delivery")

    delivered_request = api.request_billing_delivery(
        FinancialVersionedBillingPreparationCommand(
            preparation_id=preparation.id, expected_version=submitted.row_version + 1
        )
    )
    assert delivered_request.status == "delivery_pending"


def test_desktop_billing_preparation_creation_is_idempotent(services) -> None:
    _organization, project, _cost_code = _setup_billable_project(services)
    api = _build_api(services)
    profile = api.create_billing_profile(
        FinancialCreateBillingProfileCommand(
            project_id=project.id,
            contract_reference="CONTRACT-3",
            contract_value=Decimal("1000"),
            customer_party_id="party-1",
        )
    )
    api.activate_billing_profile(
        FinancialActivateBillingProfileCommand(
            project_id=project.id, expected_version=profile.row_version
        )
    )
    command = FinancialCreateBillingPreparationCommand(
        project_id=project.id,
        preparation_number="BP-2026-0002",
        period_start=date(2026, 8, 1),
        period_end=date(2026, 8, 31),
        idempotency_key="billing-run-2026-08-idempotent",
    )

    first = api.create_billing_preparation(command)
    second = api.create_billing_preparation(command)

    assert first.id == second.id


def test_desktop_billing_source_does_not_bypass_service_method_validation(services) -> None:
    """The desktop adapter must not weaken or duplicate domain/service
    validation: adding a mismatched source type still fails through the
    existing BILLING_SOURCE_METHOD_MISMATCH rule, unchanged."""
    _organization, project, _cost_code = _setup_billable_project(services)
    api = _build_api(services)
    profile = api.create_billing_profile(
        FinancialCreateBillingProfileCommand(
            project_id=project.id,
            contract_reference="CONTRACT-4",
            contract_value=Decimal("1000"),
            customer_party_id="party-1",
        )
    )
    api.activate_billing_profile(
        FinancialActivateBillingProfileCommand(
            project_id=project.id, expected_version=profile.row_version
        )
    )
    preparation = api.create_billing_preparation(
        FinancialCreateBillingPreparationCommand(
            project_id=project.id,
            preparation_number="BP-2026-0003",
            period_start=date(2026, 8, 1),
            period_end=date(2026, 8, 31),
            idempotency_key="billing-run-2026-08-mismatch",
        )
    )

    with pytest.raises(BusinessRuleError) as exc:
        api.add_approved_time_billing_source(
            FinancialAddApprovedTimeBillingSourceCommand(
                preparation_id=preparation.id,
                expected_version=preparation.row_version,
                time_entry_id="does-not-matter",
            )
        )
    assert exc.value.code == "BILLING_SOURCE_METHOD_MISMATCH"


def test_desktop_billing_commands_require_finance_manage_permission(services) -> None:
    _organization, project, _cost_code = _setup_billable_project(services)
    api = _build_api(services)
    _register_and_login(services, "billing-report-only", role_names=["viewer"])

    with pytest.raises(BusinessRuleError, match="finance.manage") as exc:
        api.create_billing_profile(
            FinancialCreateBillingProfileCommand(
                project_id=project.id,
                contract_reference="CONTRACT-5",
                contract_value=Decimal("1000"),
            )
        )
    assert exc.value.code == "PERMISSION_DENIED"


def test_desktop_billing_project_scope_is_enforced(services) -> None:
    _organization, project_a, _cost_code = _setup_billable_project(
        services, name="Billing Scope A"
    )
    _organization2, project_b, _cost_code_b = _setup_billable_project(
        services, name="Billing Scope B", create_period=False
    )
    api = _build_api(services)
    tenant_id = services["user_session"].stored_active_tenant_id()
    organization_id = services["user_session"].stored_active_organization_id()
    services["auth_service"].register_user(
        "billing-scoped-to-a", "StrongPass123", role_names=["viewer"]
    )
    user = services["auth_service"].authenticate("billing-scoped-to-a", "StrongPass123")
    principal = services["auth_service"].build_principal(user)
    services["user_session"].set_principal(
        UserSessionPrincipal(
            user_id=principal.user_id,
            username=principal.username,
            display_name=principal.display_name,
            role_names=principal.role_names,
            permissions=frozenset({"finance.manage", "finance.read"}),
            project_access={project_a.id: frozenset({"finance.manage", "finance.read"})},
            active_tenant_id=tenant_id,
            active_organization_id=organization_id,
        )
    )

    profile_a = api.create_billing_profile(
        FinancialCreateBillingProfileCommand(
            project_id=project_a.id,
            contract_reference="CONTRACT-A",
            contract_value=Decimal("1000"),
        )
    )
    assert profile_a.contract_reference == "CONTRACT-A"

    with pytest.raises(BusinessRuleError, match="finance.manage"):
        api.create_billing_profile(
            FinancialCreateBillingProfileCommand(
                project_id=project_b.id,
                contract_reference="CONTRACT-B",
                contract_value=Decimal("1000"),
            )
        )


def test_desktop_does_not_expose_external_outcome_or_accounting_authority() -> None:
    """Accounting-boundary regression: record_external_outcome (and any
    authoritative invoice/receivable/payment/tax/GL action) must never be
    reachable through the interactive desktop surface -- only PM-authored
    preparation/profile/schedule/delivery-request actions are."""
    public_methods = {
        name
        for name in dir(ProjectManagementFinancialsDesktopApi)
        if not name.startswith("_")
    }
    forbidden_substrings = (
        "external_outcome",
        "externaloutcome",
        "issue_invoice",
        "create_receivable",
        "post_payment",
        "record_tax",
        "general_ledger",
    )
    for method_name in public_methods:
        lowered = method_name.lower()
        for token in forbidden_substrings:
            assert token not in lowered, (
                f"Desktop API method '{method_name}' looks like it exposes an "
                f"authoritative accounting action ('{token}')."
            )
    # request_delivery IS present at the service layer (PM requesting
    # transmission of its own evidence is legitimate) but the desktop
    # surface only exposes it as "request_billing_delivery", returning PM's
    # own preparation-state DTO -- never the raw external outcome/record.
    assert "request_billing_delivery" in public_methods

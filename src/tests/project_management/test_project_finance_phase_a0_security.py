from __future__ import annotations

import json
from datetime import date
from decimal import Decimal

import pytest

from src.core.platform.domain.security.auth.session import UserSessionPrincipal
from src.core.platform.domain.security.authorization.roles.role_permission_catalog import (
    DEFAULT_PERMISSIONS,
    DEFAULT_ROLE_PERMISSIONS,
)
from src.core.platform.common.exceptions import BusinessRuleError, NotFoundError
from src.core.modules.project_management.access.policy import (
    PROJECT_SCOPE_ROLE_PERMISSIONS,
)


def _login(services, username: str, password: str) -> None:
    auth = services["auth_service"]
    user = auth.authenticate(username, password)
    services["user_session"].set_principal(auth.build_principal(user))


def _seed_labor_finance_project(services) -> str:
    project = services["project_service"].create_project(
        "Phase A0 Finance",
        start_date=date(2026, 1, 5),
        financial_currency_code="EUR",
    )
    task = services["task_service"].create_task(
        project.id,
        "Restricted labor",
        start_date=date(2026, 1, 5),
        duration_days=2,
    )
    resource = services["resource_service"].create_resource(
        "Sensitive Engineer",
        "Engineer",
        hourly_rate=125.0,
        currency_code="EUR",
        rate_effective_on=date(2026, 1, 5),
    )
    project_resource = services["project_resource_service"].add_to_project(
        project_id=project.id,
        resource_id=resource.id,
        planned_hours=16.0,
        hourly_rate=125.0,
        currency_code="EUR",
    )
    assignment = services["task_service"].assign_project_resource(
        task_id=task.id,
        project_resource_id=project_resource.id,
        allocation_percent=100.0,
    )
    cost_code = services["financial_configuration_service"].create_cost_code(
        code="SEC-LABOR",
        name="Sensitive labor",
    )
    profile = services["financial_configuration_service"].get_profile(project.id)
    services["financial_configuration_service"].configure_profile(
        project.id,
        expected_version=profile.version,
        default_cost_code_id=cost_code.id,
    )
    services["task_service"].update_assignment_planned_hours(
        assignment.id,
        allocated_planned_hours=Decimal("16"),
        expected_assignment_version=assignment.version,
        expected_project_resource_version=project_resource.version,
    )
    services["planned_cost_service"].calculate_snapshot(
        project.id,
        calculated_by="admin",
        as_of=date(2026, 1, 5),
    )
    return project.id


def test_finance_permissions_are_registered_and_granted_only_to_intended_roles():
    assert "finance.read" in DEFAULT_PERMISSIONS
    assert "finance.read_sensitive" in DEFAULT_PERMISSIONS
    assert "finance.read_sensitive" in DEFAULT_ROLE_PERMISSIONS["finance_controller"]
    assert "finance.read_sensitive" in DEFAULT_ROLE_PERMISSIONS["auditor"]
    assert "finance.read_sensitive" not in DEFAULT_ROLE_PERMISSIONS["project_manager"]
    assert "finance.read" in DEFAULT_ROLE_PERMISSIONS["project_lead"]
    assert "finance.export" in PROJECT_SCOPE_ROLE_PERMISSIONS["owner"]


def test_finance_export_requires_distinct_export_permission(services):
    tenant_id = services["user_session"].stored_active_tenant_id()
    organization_id = services["user_session"].stored_active_organization_id()
    services["module_catalog_service"].set_module_state(
        organization_id,
        "project_management",
        licensed=True,
        enabled=True,
    )
    user_session = services["user_session"]
    user_session.set_principal(
        UserSessionPrincipal(
            user_id="finance-reader",
            username="finance-reader",
            display_name="Finance Reader",
            role_names=frozenset({"viewer"}),
            permissions=frozenset({"finance.read", "report.export"}),
            active_tenant_id=tenant_id,
            active_organization_id=organization_id,
        )
    )

    with pytest.raises(BusinessRuleError, match="finance.export") as exc:
        services["finance_service"].get_finance_export_snapshot("project-1")

    assert exc.value.code == "PERMISSION_DENIED"


def test_report_view_without_finance_read_cannot_view_finance_snapshot(services):
    project_id = _seed_labor_finance_project(services)
    services["auth_service"].register_user(
        "report-only-finance",
        "StrongPass123",
        role_names=["viewer"],
    )
    _login(services, "report-only-finance", "StrongPass123")

    with pytest.raises(BusinessRuleError, match="finance.read"):
        services["finance_service"].get_finance_snapshot(project_id)


def test_sensitive_labor_detail_is_redacted_without_sensitive_permission(services):
    project_id = _seed_labor_finance_project(services)
    auth = services["auth_service"]
    auth.register_user(
        "project-finance-reader",
        "StrongPass123",
        role_names=["project_manager"],
    )
    _login(services, "project-finance-reader", "StrongPass123")

    snapshot = services["finance_service"].get_finance_snapshot(project_id)

    assert snapshot.sensitive_detail_included is False
    assert snapshot.by_resource == []
    labor_rows = [row for row in snapshot.ledger if row.cost_type == "LABOR"]
    assert labor_rows
    assert all(row.reference_type == "restricted_finance" for row in labor_rows)
    assert all(row.resource_id is None and row.resource_name is None for row in labor_rows)


def test_finance_controller_can_view_sensitive_labor_detail(services):
    project_id = _seed_labor_finance_project(services)
    auth = services["auth_service"]
    auth.register_user(
        "sensitive-finance-reader",
        "StrongPass123",
        role_names=["finance_controller"],
    )
    _login(services, "sensitive-finance-reader", "StrongPass123")

    snapshot = services["finance_service"].get_finance_snapshot(project_id)

    assert snapshot.sensitive_detail_included is True
    assert snapshot.by_resource
    labor_rows = [row for row in snapshot.ledger if row.cost_type == "LABOR"]
    assert any(row.reference_type != "restricted_finance" for row in labor_rows)
    assert any(row.resource_id is not None for row in labor_rows)


def test_global_sensitive_grant_does_not_bypass_project_scope(services):
    project_id = _seed_labor_finance_project(services)
    user_session = services["user_session"]
    tenant_id = user_session.stored_active_tenant_id()
    organization_id = user_session.stored_active_organization_id()
    user_session.set_principal(
        UserSessionPrincipal(
            user_id="scoped-finance-reader",
            username="scoped-finance-reader",
            display_name="Scoped Finance Reader",
            role_names=frozenset({"viewer"}),
            permissions=frozenset({"finance.read", "finance.read_sensitive"}),
            project_access={project_id: frozenset({"finance.read"})},
            active_tenant_id=tenant_id,
            active_organization_id=organization_id,
        )
    )

    snapshot = services["finance_service"].get_finance_snapshot(project_id)

    assert snapshot.by_resource == []
    labor_rows = [row for row in snapshot.ledger if row.cost_type == "LABOR"]
    assert labor_rows
    assert all(row.reference_type == "restricted_finance" for row in labor_rows)


def _create_audited_cost_entry(services, *, command_id: str):
    organization = services["organization_service"].get_active_organization()
    project = services["project_service"].create_project(
        "Audited canonical cost",
        financial_currency_code=organization.base_currency,
    )
    cost_code = services["financial_configuration_service"].create_cost_code(
        code=f"AUD-{command_id[-4:].upper()}",
        name="Audit evidence",
    )
    entry = services["cost_entry_service"].create_manual_entry(
        project_id=project.id,
        command_id=command_id,
        description="Audit evidence",
        amount=Decimal("25.00"),
        currency_code=organization.base_currency,
        transaction_date=date(2026, 1, 12),
        cost_code_id=cost_code.id,
    )
    return project, entry


def test_cost_entry_mutation_records_scoped_enterprise_audit(services):
    project, entry = _create_audited_cost_entry(services, command_id="audit-create-1")

    entries = services["enterprise_audit_service"].list_recent(
        entity_type="project_cost_entry",
        operation="project_cost_entry.create",
    )
    audit = next(candidate for candidate in entries if candidate.entity_id == entry.id)
    payload = json.loads(audit.new_value)

    assert audit.tenant_id
    assert audit.organization_id
    assert audit.entity_parent_id == project.id
    assert audit.compliance_tag == "financial"
    assert audit.old_value is None
    assert Decimal(payload["amount"]) == Decimal("25.00")
    assert payload["currency_code"] == entry.currency_code


def test_cost_entry_mutation_rolls_back_when_required_audit_fails(services, monkeypatch):
    organization = services["organization_service"].get_active_organization()
    project = services["project_service"].create_project(
        "Fail-closed canonical cost audit",
        financial_currency_code=organization.base_currency,
    )
    cost_code = services["financial_configuration_service"].create_cost_code(
        code="AUD-FAIL",
        name="Fail-closed audit",
    )
    audit_service = services["enterprise_audit_service"]
    original_record = audit_service.record

    def _fail_cost_audit(**kwargs):
        if kwargs.get("entity_type") == "project_cost_entry":
            raise RuntimeError("simulated cost audit failure")
        return original_record(**kwargs)

    monkeypatch.setattr(audit_service, "record", _fail_cost_audit)

    with pytest.raises(RuntimeError, match="simulated cost audit failure"):
        services["cost_entry_service"].create_manual_entry(
            project_id=project.id,
            command_id="audit-failure-1",
            description="Must roll back",
            amount=Decimal("25.00"),
            currency_code=organization.base_currency,
            transaction_date=date(2026, 1, 12),
            cost_code_id=cost_code.id,
        )

    entries, total = services["cost_entry_service"].list_for_project(project.id)
    assert entries == []
    assert total == 0


# ---------------------------------------------------------------------------
# F0 — ReportingService / DashboardService authorization boundary closure
#
# report.view is a general reporting permission. It must never, by itself,
# expose Project Finance authority data (EVM, cost breakdown, cost source
# breakdown, labor cost, or the financial fields inside a mixed KPI/dashboard
# payload). finance.read governs that data; finance.read_sensitive governs
# the individually resource-identified labor detail tier within it.
# ---------------------------------------------------------------------------


def _register_and_login(services, username: str, *, role_names: list[str]) -> None:
    services["auth_service"].register_user(username, "StrongPass123", role_names=role_names)
    _login(services, username, "StrongPass123")


def test_report_view_alone_allows_non_financial_reporting(services):
    """Case A (allow half): report.view without finance.read must keep
    working for legitimate non-financial project reporting."""
    project_id = _seed_labor_finance_project(services)
    _register_and_login(services, "report-only-general", role_names=["viewer"])

    reporting = services["reporting_service"]
    assert reporting.get_gantt_data(project_id) is not None
    assert reporting.get_resource_load_summary(project_id) is not None
    assert reporting.get_critical_path(project_id) is not None


def test_report_view_alone_cannot_obtain_finance_authority_reports(services):
    """Case A (deny half): report.view without finance.read must not return
    EVM, cost breakdown, cost source breakdown, or labor cost data through
    ReportingService, regardless of caller."""
    project_id = _seed_labor_finance_project(services)
    _register_and_login(services, "report-only-finance-2", role_names=["viewer"])
    reporting = services["reporting_service"]

    with pytest.raises(BusinessRuleError, match="finance.read") as exc:
        reporting.get_cost_breakdown(project_id)
    assert exc.value.code == "PERMISSION_DENIED"

    with pytest.raises(BusinessRuleError, match="finance.read"):
        reporting.get_project_cost_source_breakdown(project_id)

    with pytest.raises(BusinessRuleError, match="finance.read"):
        reporting.get_project_cost_control_totals(project_id)

    with pytest.raises(BusinessRuleError, match="finance.read"):
        reporting.get_earned_value(project_id)

    with pytest.raises(BusinessRuleError, match="finance.read"):
        reporting.get_evm_series(project_id)

    with pytest.raises(BusinessRuleError, match="finance.read"):
        reporting.get_project_labor_details(project_id)

    with pytest.raises(BusinessRuleError, match="finance.read"):
        reporting.calculate_project_labor_details(project_id)


def test_report_view_alone_gets_redacted_kpis_not_a_denial(services):
    """Case A: get_project_kpis mixes schedule (non-financial) and cost
    (financial) facts in one DTO. report.view without finance.read must
    still return the schedule facts — the financial fields are redacted
    (None), not a denial of the whole call."""
    project_id = _seed_labor_finance_project(services)
    _register_and_login(services, "report-only-kpi", role_names=["viewer"])
    reporting = services["reporting_service"]

    kpi = reporting.get_project_kpis(project_id)

    assert kpi.financial_detail_included is False
    assert kpi.total_planned_cost is None
    assert kpi.total_actual_cost is None
    assert kpi.cost_variance is None
    assert kpi.total_committed_cost is None
    assert kpi.committment_variance is None
    # Non-financial facts remain intact.
    assert kpi.project_id == project_id
    assert kpi.tasks_total >= 1


def test_report_view_alone_gets_redacted_baseline_comparison_not_a_denial(services):
    """Case A: compare_baselines mixes schedule (non-financial) facts with
    Project Finance authority data (planned cost) per row. report.view
    without finance.read must still return the schedule comparison — the
    planned-cost fields are redacted (None), not a denial of the whole
    call. Regression test for the F0 gap where this method authorized on
    report.view alone with no redaction."""
    project_id = _seed_labor_finance_project(services)
    baseline_service = services["baseline_service"]
    baseline_1 = baseline_service.create_baseline(project_id, "BL1", rate_as_of=date(2026, 1, 5))
    baseline_2 = baseline_service.create_baseline(project_id, "BL2", rate_as_of=date(2026, 1, 5))
    _register_and_login(services, "report-only-baseline", role_names=["viewer"])
    reporting = services["reporting_service"]

    comparison = reporting.compare_baselines(
        project_id=project_id,
        baseline_a_id=baseline_1.id,
        baseline_b_id=baseline_2.id,
        include_unchanged=True,
    )

    assert comparison.financial_detail_included is False
    assert comparison.total_tasks_compared >= 1
    for row in comparison.rows:
        assert row.baseline_a_planned_cost is None
        assert row.baseline_b_planned_cost is None
        assert row.planned_cost_delta is None


def test_finance_read_allows_baseline_comparison_cost_detail(services):
    """Case B: finance.read must allow the planned-cost fields in a
    baseline comparison to be visible."""
    project_id = _seed_labor_finance_project(services)
    baseline_service = services["baseline_service"]
    baseline_1 = baseline_service.create_baseline(project_id, "BL1", rate_as_of=date(2026, 1, 5))
    baseline_2 = baseline_service.create_baseline(project_id, "BL2", rate_as_of=date(2026, 1, 5))
    _register_and_login(services, "finance-reader-baseline", role_names=["project_manager"])
    reporting = services["reporting_service"]

    comparison = reporting.compare_baselines(
        project_id=project_id,
        baseline_a_id=baseline_1.id,
        baseline_b_id=baseline_2.id,
        include_unchanged=True,
    )

    assert comparison.financial_detail_included is True
    assert any(row.planned_cost_delta is not None for row in comparison.rows)


def test_dashboard_data_redacts_finance_without_failing_for_report_view_only(services):
    """DashboardService.get_dashboard_data must keep working for a
    report.view-only caller, with cost_sources/EVM/KPI-cost fields absent
    rather than the whole dashboard call failing."""
    project_id = _seed_labor_finance_project(services)
    _register_and_login(services, "report-only-dashboard", role_names=["viewer"])

    dashboard_data = services["dashboard_service"].get_dashboard_data(
        project_id, include_evm=True
    )

    assert dashboard_data.cost_sources is None
    assert dashboard_data.evm is None
    assert dashboard_data.kpi.financial_detail_included is False
    assert dashboard_data.kpi.total_planned_cost is None
    # Non-financial dashboard content is unaffected.
    assert dashboard_data.resource_load is not None


def test_finance_read_without_sensitive_allows_cost_breakdown_and_kpis(services):
    """Case B (allow half): finance.read without finance.read_sensitive must
    allow ordinary, non-sensitive Project Finance reads."""
    project_id = _seed_labor_finance_project(services)
    _register_and_login(services, "finance-reader-nonsensitive", role_names=["project_manager"])
    assert "finance.read_sensitive" not in DEFAULT_ROLE_PERMISSIONS["project_manager"]
    reporting = services["reporting_service"]

    breakdown = reporting.get_cost_breakdown(project_id)
    assert breakdown is not None

    kpi = reporting.get_project_kpis(project_id)
    assert kpi.financial_detail_included is True
    assert kpi.total_planned_cost is not None


def test_finance_read_without_sensitive_denies_identified_labor_detail(services):
    """Case B (redact/deny half): individually resource-identified labor
    rate/cost detail requires finance.read_sensitive, matching the existing
    FinanceService labor redaction convention. There is no non-sensitive
    aggregate variant of this ReportingService method, so the established
    convention is enforced as a denial rather than a silent redaction."""
    project_id = _seed_labor_finance_project(services)
    _register_and_login(services, "finance-reader-nonsensitive-2", role_names=["project_manager"])
    reporting = services["reporting_service"]

    with pytest.raises(BusinessRuleError, match="finance.read_sensitive") as exc:
        reporting.get_project_labor_details(project_id)
    assert exc.value.code == "PERMISSION_DENIED"


def test_finance_read_sensitive_allows_identified_labor_detail(services):
    """Case C: finance.read_sensitive grants access to resource-identified
    labor detail through ReportingService, matching FinanceService."""
    project_id = _seed_labor_finance_project(services)
    _register_and_login(services, "finance-reader-sensitive", role_names=["finance_controller"])
    reporting = services["reporting_service"]

    rows = reporting.get_project_labor_details(project_id)

    assert rows
    assert any(row.resource_id is not None for row in rows)


def test_finance_export_permission_alone_is_not_sufficient_without_finance_read(services):
    """Case E: finance.export must not substitute finance.read. This mirrors
    the existing FinanceService.get_finance_export_snapshot convention
    (export permission gates the export action; read permission still
    governs whether the underlying data may be produced at all)."""
    tenant_id = services["user_session"].stored_active_tenant_id()
    organization_id = services["user_session"].stored_active_organization_id()
    services["user_session"].set_principal(
        UserSessionPrincipal(
            user_id="export-only-finance",
            username="export-only-finance",
            display_name="Export Only",
            role_names=frozenset({"viewer"}),
            permissions=frozenset({"finance.export", "report.export"}),
            active_tenant_id=tenant_id,
            active_organization_id=organization_id,
        )
    )

    with pytest.raises(BusinessRuleError, match="finance.read") as exc:
        services["finance_service"].get_finance_export_snapshot("project-1")
    assert exc.value.code == "PERMISSION_DENIED"


def test_finance_project_scope_does_not_leak_across_projects(services):
    """Case F: a project-scoped finance.read grant for Project A must not
    authorize Project B."""
    project_a_id = _seed_labor_finance_project(services)
    project_b = services["project_service"].create_project(
        "F0 project scope isolation B",
        start_date=date(2026, 1, 5),
        financial_currency_code="EUR",
    )
    tenant_id = services["user_session"].stored_active_tenant_id()
    organization_id = services["user_session"].stored_active_organization_id()
    services["user_session"].set_principal(
        UserSessionPrincipal(
            user_id="scoped-to-project-a",
            username="scoped-to-project-a",
            display_name="Scoped To Project A",
            role_names=frozenset({"viewer"}),
            permissions=frozenset({"finance.read", "report.view"}),
            project_access={project_a_id: frozenset({"finance.read", "report.view"})},
            active_tenant_id=tenant_id,
            active_organization_id=organization_id,
        )
    )
    reporting = services["reporting_service"]

    assert reporting.get_cost_breakdown(project_a_id) is not None

    with pytest.raises(BusinessRuleError, match="finance.read"):
        reporting.get_cost_breakdown(project_b.id)


def test_finance_reporting_isolated_across_organizations(services):
    organization_service = services["organization_service"]
    original_organization = organization_service.get_active_organization()
    project_id = _seed_labor_finance_project(services)

    other_organization = organization_service.create_organization(
        organization_code="F0-REPORTING-ISOLATION",
        display_name="F0 Reporting Isolation Org",
        base_currency="USD",
        is_active=False,
    )
    organization_service.set_active_organization(other_organization.id)
    try:
        with pytest.raises(NotFoundError, match="not found"):
            services["reporting_service"].get_cost_breakdown(project_id)
    finally:
        organization_service.set_active_organization(original_organization.id)

    # Visibility (and finance authorization) returns once back in-scope.
    assert services["reporting_service"].get_cost_breakdown(project_id) is not None

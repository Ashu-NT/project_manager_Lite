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
from src.core.platform.common.exceptions import BusinessRuleError


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

from __future__ import annotations

import json
from datetime import date

import pytest

from src.core.modules.project_management.domain.financials.cost import CostItem
from src.core.platform.auth.domain.session import UserSessionPrincipal
from src.core.platform.auth.policy import DEFAULT_PERMISSIONS, DEFAULT_ROLE_PERMISSIONS
from src.core.platform.common.exceptions import BusinessRuleError, NotFoundError


def _login(services, username: str, password: str) -> None:
    auth = services["auth_service"]
    user = auth.authenticate(username, password)
    services["user_session"].set_principal(auth.build_principal(user))


def _seed_labor_finance_project(services) -> str:
    project = services["project_service"].create_project(
        "Phase A0 Finance",
        start_date=date(2026, 1, 5),
        currency="EUR",
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
    services["task_service"].set_assignment_hours(assignment.id, 4.0)
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

    assert snapshot.by_resource == []
    computed_labor = [row for row in snapshot.ledger if row.source_key == "COMPUTED_LABOR"]
    assert computed_labor
    assert all(row.reference_type == "restricted_finance" for row in computed_labor)
    assert all(row.resource_id is None and row.resource_name is None for row in computed_labor)


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

    assert snapshot.by_resource
    computed_labor = [row for row in snapshot.ledger if row.source_key == "COMPUTED_LABOR"]
    assert any(row.reference_type != "restricted_finance" for row in computed_labor)
    assert any(row.resource_id is not None for row in computed_labor)


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
    computed_labor = [row for row in snapshot.ledger if row.source_key == "COMPUTED_LABOR"]
    assert computed_labor
    assert all(row.reference_type == "restricted_finance" for row in computed_labor)


def test_cost_repository_rejects_cross_project_task_on_add_and_update(services):
    project_service = services["project_service"]
    task_service = services["task_service"]
    cost_service = services["cost_service"]
    cost_repo = cost_service._cost_repo

    project = project_service.create_project("Repository scoped cost")
    other_project = project_service.create_project("Foreign task project")
    project_task = task_service.create_task(project.id, "Scoped task", duration_days=1)
    foreign_task = task_service.create_task(other_project.id, "Foreign task", duration_days=1)

    with pytest.raises(NotFoundError, match="Task not found"):
        cost_repo.add(
            CostItem.create(
                project_id=project.id,
                task_id=foreign_task.id,
                description="Invalid direct insert",
                planned_amount=10.0,
                currency_code="EUR",
            )
        )

    existing = cost_service.add_cost_item(
        project_id=project.id,
        task_id=project_task.id,
        description="Valid scoped cost",
        planned_amount=10.0,
        currency_code="EUR",
    )
    existing.task_id = foreign_task.id

    with pytest.raises(NotFoundError, match="Task not found"):
        cost_repo.update(existing)


def test_cost_mutation_records_scoped_enterprise_audit(services):
    project = services["project_service"].create_project("Audited cost")

    item = services["cost_service"].add_cost_item(
        project_id=project.id,
        description="Audit evidence",
        planned_amount=25.0,
        currency_code="EUR",
    )

    entries = services["enterprise_audit_service"].list_recent(
        entity_type="cost_item",
        operation="create",
    )
    entry = next(candidate for candidate in entries if candidate.entity_id == item.id)
    payload = json.loads(entry.new_value)

    assert entry.tenant_id
    assert entry.organization_id
    assert entry.entity_parent_id == project.id
    assert entry.compliance_tag == "financial"
    assert entry.old_value is None
    assert payload["planned_amount"] == 25.0
    assert payload["currency_code"] == "EUR"


def test_cost_mutation_rolls_back_when_required_audit_fails(services, monkeypatch):
    project = services["project_service"].create_project("Fail-closed cost audit")
    audit_service = services["enterprise_audit_service"]
    original_record = audit_service.record

    def _fail_cost_audit(**kwargs):
        if kwargs.get("entity_type") == "cost_item":
            raise RuntimeError("simulated cost audit failure")
        return original_record(**kwargs)

    monkeypatch.setattr(audit_service, "record", _fail_cost_audit)

    with pytest.raises(RuntimeError, match="simulated cost audit failure"):
        services["cost_service"].add_cost_item(
            project_id=project.id,
            description="Must roll back",
            planned_amount=25.0,
            currency_code="EUR",
        )

    services["cost_service"]._session.expire_all()
    assert services["cost_service"].list_cost_items_for_project(project.id) == []

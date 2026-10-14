from __future__ import annotations

from dataclasses import replace
from datetime import date

import pytest

from src.core.modules.project_management.domain.financials.configuration import (
    BillingMethod,
    CostCodePolicy,
    FinancialProfileStatus,
    ProjectCostCode,
    ProjectFinancialProfile,
)
from src.core.platform.common.exceptions import (
    BusinessRuleError,
    ConcurrencyError,
    ValidationError,
)
from src.tests.ui_runtime_helpers import login_as


def test_financial_configuration_domain_enforces_currency_billing_and_hierarchy() -> None:
    with pytest.raises(ValidationError, match="not active in ISO 4217"):
        ProjectFinancialProfile.create(
            tenant_id="tenant-a",
            organization_id="org-a",
            project_id="project-a",
            currency_code="ZZZ",
        )

    with pytest.raises(ValidationError, match="requires a billing method"):
        ProjectFinancialProfile.create(
            tenant_id="tenant-a",
            organization_id="org-a",
            project_id="project-a",
            currency_code="EUR",
            is_billable=True,
        )

    code = ProjectCostCode.create(
        tenant_id="tenant-a",
        organization_id="org-a",
        code="lab.001",
        name="Engineering labor",
        effective_from=date(2026, 1, 1),
        effective_to=date(2026, 12, 31),
    )
    assert code.code == "LAB.001"
    assert code.is_effective_on(date(2026, 6, 1))
    assert not code.is_effective_on(date(2027, 1, 1))

    with pytest.raises(ValidationError, match="supplied together"):
        replace(code, external_system="SAP")


def test_project_creation_atomically_initializes_financial_profile_and_audit(services) -> None:
    project = services['project_create'].create_project(
        "Canonical financial profile",
        financial_currency_code="usd",
        start_date=date(2026, 2, 1),
        end_date=date(2026, 11, 30),
    )

    profile = services['financial_configuration_query'].get_profile(project.id)

    assert profile.currency_code == "USD"
    assert profile.financial_start_date == project.start_date
    assert profile.financial_end_date == project.end_date
    assert profile.status == FinancialProfileStatus.ACTIVE
    assert profile.version == 1
    entries = services["enterprise_audit_service"].list_recent(
        entity_type="project_financial_profile",
        operation="financial_profile.create",
    )
    assert any(entry.entity_id == profile.id for entry in entries)


def test_profile_configuration_requires_version_and_is_the_only_currency_authority(services) -> None:
    project = services['project_create'].create_project(
        "Profile concurrency",
        financial_currency_code="EUR",
    )
    service = services['financial_configuration_query']
    profile = services['financial_configuration_query'].get_profile(project.id)

    updated = services['finance_governance_commands'].financial_profile(lambda handler: handler.configure_profile(
        project.id,
        expected_version=profile.version,
        currency_code="GBP",
        is_funded=True,
        is_billable=True,
        billing_method=BillingMethod.TIME_AND_MATERIALS,
    ))

    assert updated.currency_code == "GBP"
    assert updated.version == 2
    operational_project = services['project_query'].get_project(project.id)
    assert not hasattr(operational_project, "currency")
    with pytest.raises(ConcurrencyError, match="changed since"):
        services['finance_governance_commands'].financial_profile(lambda handler: handler.configure_profile(
            project.id,
            expected_version=profile.version,
            is_funded=False,
        ))

    assert services['financial_configuration_query'].get_profile(project.id).currency_code == "GBP"


def test_cost_code_hierarchy_restrictions_and_profile_lifecycle(services) -> None:
    project = services['project_create'].create_project("Restricted cost catalog")
    service = services['financial_configuration_query']
    parent = services['finance_governance_commands'].cost_code(lambda handler: handler.create_cost_code(code="LAB", name="Labor"))
    child = services['finance_governance_commands'].cost_code(lambda handler: handler.create_cost_code(
        code="LAB.ENG",
        name="Engineering",
        parent_id=parent.id,
        effective_from=date(2026, 1, 1),
    ))
    other = services['finance_governance_commands'].cost_code(lambda handler: handler.create_cost_code(code="MAT", name="Materials"))

    with pytest.raises(BusinessRuleError, match="cycle"):
        services['finance_governance_commands'].cost_code(lambda handler: handler.update_cost_code(
            parent.id,
            expected_version=parent.version,
            parent_id=child.id,
        ))
    with pytest.raises(BusinessRuleError, match="active child"):
        services['finance_governance_commands'].cost_code(lambda handler: handler.deactivate_cost_code(parent.id, expected_version=parent.version))

    services['finance_governance_commands'].cost_code(lambda handler: handler.add_project_cost_code(project_id=project.id, cost_code_id=child.id))
    profile = services['financial_configuration_query'].get_profile(project.id)
    profile = services['finance_governance_commands'].financial_profile(lambda handler: handler.configure_profile(
        project.id,
        expected_version=profile.version,
        cost_code_policy=CostCodePolicy.RESTRICTED,
        default_cost_code_id=child.id,
    ))

    assert [row.id for row in services['financial_configuration_query'].list_available_cost_codes(project.id)] == [child.id]
    assert profile.default_cost_code_id == child.id
    assert other.id not in {row.id for row in services['financial_configuration_query'].list_available_cost_codes(project.id)}
    with pytest.raises(BusinessRuleError, match="default"):
        services['finance_governance_commands'].cost_code(lambda handler: handler.remove_project_cost_code(project_id=project.id, cost_code_id=child.id))

    held = services['finance_governance_commands'].financial_profile(lambda handler: handler.transition_profile(
        project.id,
        target=FinancialProfileStatus.ON_HOLD,
        expected_version=profile.version,
    ))
    closed = services['finance_governance_commands'].financial_profile(lambda handler: handler.transition_profile(
        project.id,
        target=FinancialProfileStatus.CLOSED,
        expected_version=held.version,
    ))
    with pytest.raises(BusinessRuleError, match="cannot transition"):
        services['finance_governance_commands'].financial_profile(lambda handler: handler.transition_profile(
            project.id,
            target=FinancialProfileStatus.ACTIVE,
            expected_version=closed.version,
        ))

    inactive = services['finance_governance_commands'].cost_code(lambda handler: handler.deactivate_cost_code(other.id, expected_version=other.version))
    assert inactive.is_active is False
    assert services['finance_governance_commands'].cost_code(lambda handler: handler.activate_cost_code(
        other.id,
        expected_version=inactive.version,
    )).is_active is True

    retired_parent = services['finance_governance_commands'].cost_code(lambda handler: handler.create_cost_code(code="OLD", name="Retired parent"))
    retired_child = services['finance_governance_commands'].cost_code(lambda handler: handler.create_cost_code(
        code="OLD.CHILD",
        name="Retired child",
        parent_id=retired_parent.id,
    ))
    retired_child = services['finance_governance_commands'].cost_code(lambda handler: handler.deactivate_cost_code(
        retired_child.id,
        expected_version=retired_child.version,
    ))
    services['finance_governance_commands'].cost_code(lambda handler: handler.deactivate_cost_code(
        retired_parent.id,
        expected_version=retired_parent.version,
    ))
    retired_child = services['finance_governance_commands'].cost_code(lambda handler: handler.update_cost_code(
        retired_child.id,
        expected_version=retired_child.version,
        name="Corrected retired child",
    ))
    with pytest.raises(BusinessRuleError, match="active ancestors"):
        services['finance_governance_commands'].cost_code(lambda handler: handler.activate_cost_code(
            retired_child.id,
            expected_version=retired_child.version,
        ))


def test_create_cost_code_for_restricted_project_is_immediately_available(services) -> None:
    project = services['project_create'].create_project("Restricted cost-code creation")
    service = services['financial_configuration_query']
    profile = services['financial_configuration_query'].get_profile(project.id)
    services['finance_governance_commands'].financial_profile(lambda handler: handler.configure_profile(
        project.id,
        expected_version=profile.version,
        cost_code_policy=CostCodePolicy.RESTRICTED,
    ))

    created = services['finance_governance_commands'].cost_code(lambda handler: handler.create_cost_code(
        code="FIELD.LABOR",
        name="Field labor",
        available_to_project_id=project.id,
    ))

    assert [row.id for row in services['financial_configuration_query'].list_available_cost_codes(project.id)] == [created.id]


def test_financial_configuration_repositories_isolate_active_organization(services) -> None:
    configuration_service = services['financial_configuration_query']
    original_organization = services["tenant_context_service"].get_active_organization()
    project = services['project_create'].create_project("Organization A finance")
    code = services['finance_governance_commands'].cost_code(lambda handler: handler.create_cost_code(code="ORG-A", name="Organization A"))
    other_organization = services["organization_commands"].create_organization(
        organization_code="PF-B1-OTHER",
        display_name="Project Finance Other",
        base_currency="USD",
    )

    services["tenant_context_service"].set_active_organization(other_organization.id)
    try:
        assert configuration_service._cost_code_repo.get(code.id) is None
        assert configuration_service._profile_repo.get_by_project(project.id) is None
    finally:
        services["tenant_context_service"].set_active_organization(original_organization.id)

    assert configuration_service._cost_code_repo.get(code.id).id == code.id
    assert configuration_service._profile_repo.get_by_project(project.id).project_id == project.id


def test_financial_configuration_requires_global_and_project_manage_permissions(services) -> None:
    project = services['project_create'].create_project("Finance scope guard")
    user = services["user_registration"].register_user(
        "phase-b1-project-manager",
        "StrongPass123",
        role_names=["project_manager"],
        tenant_id=services["user_session"].active_tenant_id(),
    )
    services["access_service"].assign_scope_grant(
        scope_type="project",
        scope_id=project.id,
        user_id=user.id,
        scope_role="owner",
    )
    login_as(services, "phase-b1-project-manager", "StrongPass123")

    assert services['financial_configuration_query'].get_profile(project.id)
    with pytest.raises(BusinessRuleError, match="finance.manage"):
        services['finance_governance_commands'].cost_code(lambda handler: handler.create_cost_code(
            code="DENIED",
            name="Denied",
        ))


def test_financial_configuration_mutation_rolls_back_when_audit_fails(
    services,
    monkeypatch,
) -> None:
    service = services['financial_configuration_query']
    from src.core.platform.application.history.audit.enterprise_audit_service import (
        EnterpriseAuditService,
    )

    original_record = EnterpriseAuditService.record

    def _fail_cost_code_audit(self, **kwargs):
        if kwargs.get("entity_type") == "project_cost_code":
            raise RuntimeError("simulated configuration audit failure")
        return original_record(self, **kwargs)

    monkeypatch.setattr(EnterpriseAuditService, "record", _fail_cost_code_audit)
    with pytest.raises(RuntimeError, match="simulated configuration audit failure"):
        services['finance_governance_commands'].cost_code(lambda handler: handler.create_cost_code(code="ROLLBACK", name="Must roll back"))

    service._session.expire_all()
    assert all(row.code != "ROLLBACK" for row in services['financial_configuration_query'].list_cost_codes())

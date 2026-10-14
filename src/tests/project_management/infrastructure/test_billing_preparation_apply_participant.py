"""`BillingPreparationApprovalParticipant` stages a billing preparation approval/rejection on a
caller-supplied Session without opening or completing its own transaction."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.core.modules.project_management.application.financials.invoicing.billing_events import (
    BillingPreparationStatusChanged,
    BillingPreparationStatusChangeType,
)
from src.core.modules.project_management.domain.financials.billing_preparation import (
    BillingPreparationStatus,
)
from src.core.modules.project_management.domain.financials.configuration import (
    BillingMethod,
)
from src.core.modules.project_management.infrastructure.approval.billing_preparation_apply_participant import (
    BillingPreparationApprovalParticipant,
)
from src.core.modules.project_management.infrastructure.composition.registrations.approvals.finance.billing_preparation import (
    build_billing_preparation_approval_deps,
)
from src.core.platform.common.exceptions import BusinessRuleError
from src.infra.persistence.orm.base import Base


def _login(services, username: str, password: str) -> None:
    user_session = services["user_session"]
    user = services["authentication"].authenticate(username, password)
    user_session.set_principal(services["principal_builder"].build(user))


def _login_independent_reviewer(services, suffix: str) -> None:
    username = f"billing-independent-reviewer-{suffix}"
    services["user_registration"].register_user(
        username, "StrongPass123", role_names=["approver"]
    )
    _login(services, username, "StrongPass123")


def _setup_billable_project(services, *, suffix: str):
    boundary = services["finance_governance_commands"]
    organization = services["tenant_context_service"].get_active_organization()
    project = services['project_create'].create_project(
        f"Billing Approval Project {suffix}", financial_currency_code=organization.base_currency
    )
    cost_code = boundary.cost_code(lambda commands: commands.create_cost_code(
        code=f"BILL-APPROVAL-{suffix}", name="Billing approval cost code"
    ))
    services["financial_period_commands"].create_period(
        code=f"FY26-BILLAPR-{suffix}",
        name=f"August 2026 Approval {suffix}",
        fiscal_year=2026,
        period_number=8,
        start_date=date(2026, 8, 1),
        end_date=date(2026, 8, 31),
    )
    profile = services["financial_configuration_query"].get_profile(project.id)
    boundary.financial_profile(lambda commands: commands.configure_profile(
        project.id,
        expected_version=profile.version,
        default_cost_code_id=cost_code.id,
        billing_method=BillingMethod.FIXED_PRICE,
        is_billable=True,
    ))
    return project


def _submitted_preparation(services, session, *, suffix: str):
    """Builds a real, submitted `ProjectBillingPreparation` and its `ApprovalRequest`."""
    project = _setup_billable_project(services, suffix=suffix)
    boundary = services["finance_governance_commands"]
    profile = boundary.billing_profile(lambda commands: commands.create_profile(
        project.id,
        contract_reference=f"CONTRACT-{suffix}",
        contract_value=Decimal(50000),
        customer_party_id="party-1",
    ))
    profile = boundary.billing_profile(lambda commands: commands.activate_profile(
        project.id, expected_row_version=profile.row_version
    ))
    line = boundary.billing_schedule(lambda commands: commands.add_schedule_line(
        project.id, name="Milestone 1", amount=Decimal(24000), due_date=date(2026, 8, 20)
    ))
    line = boundary.billing_schedule(lambda commands: commands.mark_schedule_line_ready(
        line.id, expected_row_version=line.row_version
    ))

    billing_preparation_query = services["billing_preparation_query"]
    preparation = boundary.billing_preparation(lambda commands: commands.create_preparation(
        project.id,
        preparation_number=f"BP-APPROVAL-{suffix}",
        period_start=date(2026, 8, 1),
        period_end=date(2026, 8, 31),
        idempotency_key=f"billing-approval-key-{suffix}",
    ))
    boundary.billing_source(lambda commands: commands.add_fixed_price_source(
        preparation.id, schedule_line_id=line.id, expected_row_version=preparation.row_version
    ))
    preparation = billing_preparation_query.get_preparation(preparation.id)
    preparation = boundary.billing_submission(lambda commands: commands.submit_preparation(
        preparation.id, expected_row_version=preparation.row_version
    ))
    request = services["approval_queries"].list_pending(project_id=project.id)[0]
    session.expire_all()
    return project, preparation, request


def _deps(services, session):
    return build_billing_preparation_approval_deps(
        session,
        user_session=services["user_session"],
        tenant_context_service=services["tenant_context_service"],
    )


def test_submit_preparation_uses_a_fresh_uow_session_shared_by_the_approval_request(
    services, monkeypatch
):
    """`submit_preparation` opens a fresh `FinanceGovernanceUnitOfWork` Session, distinct from the
    ambient shared Session, with the preparation update and the Approval request sharing that one
    Session/transaction."""
    _login(services, "admin", "ChangeMe123!")
    project = _setup_billable_project(services, suffix="UOW")
    boundary = services["finance_governance_commands"]
    profile = boundary.billing_profile(lambda commands: commands.create_profile(
        project.id,
        contract_reference="CONTRACT-UOW",
        contract_value=Decimal(50000),
        customer_party_id="party-1",
    ))
    profile = boundary.billing_profile(lambda commands: commands.activate_profile(
        project.id, expected_row_version=profile.row_version
    ))
    line = boundary.billing_schedule(lambda commands: commands.add_schedule_line(
        project.id, name="Milestone 1", amount=Decimal(24000), due_date=date(2026, 8, 20)
    ))
    line = boundary.billing_schedule(lambda commands: commands.mark_schedule_line_ready(
        line.id, expected_row_version=line.row_version
    ))
    billing_preparation_query = services["billing_preparation_query"]
    preparation = boundary.billing_preparation(lambda commands: commands.create_preparation(
        project.id,
        preparation_number="BP-APPROVAL-UOW",
        period_start=date(2026, 8, 1),
        period_end=date(2026, 8, 31),
        idempotency_key="billing-approval-key-uow",
    ))
    boundary.billing_source(lambda commands: commands.add_fixed_price_source(
        preparation.id, schedule_line_id=line.id, expected_row_version=preparation.row_version
    ))
    preparation = billing_preparation_query.get_preparation(preparation.id)

    uow_factory = services["finance_governance_commands"]._uow_factory
    seen_uows = []
    original_create = type(uow_factory).create

    def _spy_create(self, *, context):
        uow = original_create(self, context=context)
        seen_uows.append(uow)
        return uow

    monkeypatch.setattr(type(uow_factory), "create", _spy_create)
    submitted = boundary.billing_submission(lambda commands: commands.submit_preparation(
        preparation.id, expected_row_version=preparation.row_version
    ))

    assert len(seen_uows) == 1
    uow = seen_uows[0]
    assert uow._session is not billing_preparation_query._billing_repo.session
    assert uow.billing.session is uow._session
    assert uow.approvals.session is uow._session
    assert uow._enterprise_audit_service._session is uow._session
    assert submitted.status == BillingPreparationStatus.SUBMITTED


def test_submit_preparation_audit_failure_rolls_back_preparation_and_approval_request_together(
    services, monkeypatch
):
    from src.core.platform.application.history.audit.enterprise_audit_service import (
        EnterpriseAuditService,
    )

    _login(services, "admin", "ChangeMe123!")
    project = _setup_billable_project(services, suffix="AUDITFAIL")
    boundary = services["finance_governance_commands"]
    profile = boundary.billing_profile(lambda commands: commands.create_profile(
        project.id,
        contract_reference="CONTRACT-AUDITFAIL",
        contract_value=Decimal(50000),
        customer_party_id="party-1",
    ))
    profile = boundary.billing_profile(lambda commands: commands.activate_profile(
        project.id, expected_row_version=profile.row_version
    ))
    line = boundary.billing_schedule(lambda commands: commands.add_schedule_line(
        project.id, name="Milestone 1", amount=Decimal(24000), due_date=date(2026, 8, 20)
    ))
    line = boundary.billing_schedule(lambda commands: commands.mark_schedule_line_ready(
        line.id, expected_row_version=line.row_version
    ))
    billing_preparation_query = services["billing_preparation_query"]
    preparation = boundary.billing_preparation(lambda commands: commands.create_preparation(
        project.id,
        preparation_number="BP-APPROVAL-AUDITFAIL",
        period_start=date(2026, 8, 1),
        period_end=date(2026, 8, 31),
        idempotency_key="billing-approval-key-auditfail",
    ))
    boundary.billing_source(lambda commands: commands.add_fixed_price_source(
        preparation.id, schedule_line_id=line.id, expected_row_version=preparation.row_version
    ))
    preparation = billing_preparation_query.get_preparation(preparation.id)
    pending_count_before = len(services["approval_queries"].list_pending(project_id=project.id))

    call_count = {"n": 0}
    original_record = EnterpriseAuditService.record

    def _fail_on_second_call(self, **kwargs):
        call_count["n"] += 1
        if call_count["n"] >= 2:
            raise RuntimeError("simulated host audit failure after mutation and staging")
        return original_record(self, **kwargs)

    monkeypatch.setattr(EnterpriseAuditService, "record", _fail_on_second_call)

    with pytest.raises(RuntimeError, match="simulated host audit failure after mutation and staging"):
        boundary.billing_submission(lambda commands: commands.submit_preparation(
            preparation.id, expected_row_version=preparation.row_version
        ))

    assert call_count["n"] >= 2
    monkeypatch.undo()
    reloaded = billing_preparation_query.get_preparation(preparation.id)
    assert reloaded.status == BillingPreparationStatus.DRAFT
    assert reloaded.approval_request_id is None
    pending_after = services["approval_queries"].list_pending(project_id=project.id)
    assert len(pending_after) == pending_count_before


def test_participant_apply_approves_preparation_on_the_supplied_session(services, session):
    _login(services, "admin", "ChangeMe123!")
    _project, preparation, request = _submitted_preparation(services, session, suffix="A")
    _login_independent_reviewer(services, "A")

    deps = _deps(services, session)
    result = BillingPreparationApprovalParticipant().apply(request, deps)

    approved = deps.billing_preparation_commands._billing_repo.get_preparation(preparation.id)
    assert approved.status == BillingPreparationStatus.APPROVED
    assert approved.approved_by == services["user_session"].principal.user_id
    assert result.domain_events == (
        BillingPreparationStatusChanged(
            tenant_id=approved.tenant_id,
            organization_id=approved.organization_id,
            project_id=approved.project_id,
            billing_preparation_id=approved.id,
            change_type=BillingPreparationStatusChangeType.APPROVED,
            occurred_at=approved.approved_at,
        ),
    )


def test_participant_reject_rejects_preparation_on_the_supplied_session(services, session):
    _login(services, "admin", "ChangeMe123!")
    _project, preparation, request = _submitted_preparation(services, session, suffix="B")

    deps = _deps(services, session)
    result = BillingPreparationApprovalParticipant().reject(request, deps)

    rejected = deps.billing_preparation_commands._billing_repo.get_preparation(preparation.id)
    assert rejected.status == BillingPreparationStatus.REJECTED
    assert rejected.rejected_by == services["user_session"].principal.user_id
    assert result.domain_events == (
        BillingPreparationStatusChanged(
            tenant_id=rejected.tenant_id,
            organization_id=rejected.organization_id,
            project_id=rejected.project_id,
            billing_preparation_id=rejected.id,
            change_type=BillingPreparationStatusChangeType.REJECTED,
            occurred_at=rejected.rejected_at,
        ),
    )


def test_participant_never_calls_commit_or_rollback(services, session, monkeypatch):
    """The participant stages only; the caller owns transaction completion."""
    _login(services, "admin", "ChangeMe123!")
    _, _preparation, request = _submitted_preparation(services, session, suffix="C")
    _login_independent_reviewer(services, "C")
    deps = _deps(services, session)

    def _forbidden(*_args, **_kwargs):
        raise AssertionError("the participant must never commit or roll back its own Session")

    monkeypatch.setattr(type(session), "commit", _forbidden)
    monkeypatch.setattr(type(session), "rollback", _forbidden)

    BillingPreparationApprovalParticipant().apply(request, deps)


def test_participant_reject_requires_authenticated_actor(services, session):
    _login(services, "admin", "ChangeMe123!")
    _, _preparation, request = _submitted_preparation(services, session, suffix="D")
    deps = build_billing_preparation_approval_deps(
        session,
        user_session=_BlankUserSession(),
        tenant_context_service=services["tenant_context_service"],
    )

    with pytest.raises(BusinessRuleError, match="authenticated principal"):
        BillingPreparationApprovalParticipant().reject(request, deps)


class _BlankUserSession:
    principal = None


def test_dependencies_factory_binds_every_transaction_sensitive_field_to_the_supplied_session(
    tmp_path, services
):
    engine_a = create_engine(f"sqlite:///{tmp_path}/deps_a.db", future=True)
    engine_b = create_engine(f"sqlite:///{tmp_path}/deps_b.db", future=True)
    Base.metadata.create_all(engine_a)
    Base.metadata.create_all(engine_b)
    session_a = sessionmaker(bind=engine_a, future=True)()
    session_b = sessionmaker(bind=engine_b, future=True)()
    try:
        deps_a = _deps(services, session_a)
        deps_b = _deps(services, session_b)

        service_a = deps_a.billing_preparation_commands
        service_b = deps_b.billing_preparation_commands

        assert service_a._session is session_a
        assert service_b._session is session_b
        assert service_a is not service_b
        assert service_a._billing_repo.session is session_a
        assert service_b._billing_repo.session is session_b
        # Approval depends only on billing evidence, not source provisioning.
        for commands in (service_a, service_b):
            assert not hasattr(commands, "_financial_profile_repo")
            assert not hasattr(commands, "_cost_entry_repo")
            assert not hasattr(commands, "_labor_posting_repo")
            assert not hasattr(commands, "_rate_resolver")
            assert not hasattr(commands, "_financial_period_queries")
            assert commands._approval_repo is None

        assert service_a._enterprise_audit_service is not service_b._enterprise_audit_service
        assert service_a._enterprise_audit_service._session is session_a
        assert service_b._enterprise_audit_service._session is session_b

        assert not hasattr(service_a, "_approval_commands"), (
            "the apply path must never reach back into ApprovalCommandHandler"
        )
        assert not hasattr(service_b, "_approval_commands")
    finally:
        session_a.close()
        session_b.close()


def test_dependencies_factory_never_opens_its_own_session(services, session):
    deps = _deps(services, session)
    assert deps.billing_preparation_commands._session is session, (
        "the factory must use the supplied Session, never a fresh one"
    )

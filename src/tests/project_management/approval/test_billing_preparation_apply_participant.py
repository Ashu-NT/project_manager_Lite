"""P4-PRE Step 1 (ADR-005 Section 24, Round 8): `BillingPreparationApprovalParticipant` +
`build_billing_preparation_approval_deps` -- proves the participant is genuinely
session-parameterizable (the Step-2 readiness criterion) and behaves identically to
`ProjectBillingPreparationService`'s own `_apply_approval_decision`/`_apply_rejection_decision`
(kept unmodified -- they are this family's only callers of those two methods, confirmed by grep;
`project_registry.py`'s `_approve_billing_preparation`/`_reject_billing_preparation` closures are
reproduced here verbatim, including their `expected_version + 1` payload adjustment).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.core.modules.project_management.domain.financials.billing_preparation import (
    BillingPreparationStatus,
)
from src.core.modules.project_management.domain.financials.configuration import BillingMethod
from src.core.modules.project_management.infrastructure.approval.billing_preparation_apply_participant import (
    BillingPreparationApprovalParticipant,
)
from src.core.platform.common.exceptions import BusinessRuleError
from src.core.platform.contract.models.approval.contracts import ApprovalPostCommitEvent
from src.infra.composition.approval_apply_dependencies.billing_preparation import (
    build_billing_preparation_approval_deps,
)
from src.infra.persistence.orm.base import Base


def _login(services, username: str, password: str) -> None:
    auth = services["auth_service"]
    user_session = services["user_session"]
    user = auth.authenticate(username, password)
    user_session.set_principal(auth.build_principal(user))


def _setup_billable_project(services, *, suffix: str):
    organization = services["organization_service"].get_active_organization()
    project = services["project_service"].create_project(
        f"Billing Approval Project {suffix}", financial_currency_code=organization.base_currency
    )
    cost_code = services["financial_configuration_service"].create_cost_code(
        code=f"BILL-APPROVAL-{suffix}", name="Billing approval cost code"
    )
    services["financial_period_service"].create_period(
        code=f"FY26-BILLAPR-{suffix}",
        name=f"August 2026 Approval {suffix}",
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
    return project


def _submitted_preparation(services, session, *, suffix: str):
    """Builds a real, submitted `ProjectBillingPreparation` using the production, ambient
    `billing_preparation_service` (bound to the test's own `session` fixture) -- exactly the same
    setup path `test_project_finance_billing_command_surface.py` uses -- then hands back the real
    `ApprovalRequest` `submit_preparation()` created, exactly as `ApprovalService` would have.
    """
    project = _setup_billable_project(services, suffix=suffix)
    billing_profile_service = services["billing_profile_service"]
    profile = billing_profile_service.create_profile(
        project.id,
        contract_reference=f"CONTRACT-{suffix}",
        contract_value=Decimal("50000"),
        customer_party_id="party-1",
    )
    profile = billing_profile_service.activate_profile(
        project.id, expected_row_version=profile.row_version
    )
    line = billing_profile_service.add_schedule_line(
        project.id, name="Milestone 1", amount=Decimal("24000"), due_date=date(2026, 8, 20)
    )
    line = billing_profile_service.mark_schedule_line_ready(
        line.id, expected_row_version=line.row_version
    )

    billing_preparation_service = services["billing_preparation_service"]
    preparation = billing_preparation_service.create_preparation(
        project.id,
        preparation_number=f"BP-APPROVAL-{suffix}",
        period_start=date(2026, 8, 1),
        period_end=date(2026, 8, 31),
        idempotency_key=f"billing-approval-key-{suffix}",
    )
    billing_preparation_service.add_fixed_price_source(
        preparation.id, schedule_line_id=line.id, expected_row_version=preparation.row_version
    )
    preparation = billing_preparation_service.get_preparation(preparation.id)
    preparation = billing_preparation_service.submit_preparation(
        preparation.id, expected_row_version=preparation.row_version
    )
    request = services["approval_service"].list_pending(project_id=project.id)[0]
    session.expire_all()
    return project, preparation, request


def _deps(services, session):
    return build_billing_preparation_approval_deps(
        session,
        user_session=services["user_session"],
        tenant_context_service=services["tenant_context_service"],
    )


def test_participant_apply_approves_preparation_on_the_supplied_session(services, session):
    _login(services, "admin", "ChangeMe123!")
    project, preparation, request = _submitted_preparation(services, session, suffix="A")

    deps = _deps(services, session)
    result = BillingPreparationApprovalParticipant().apply(request, deps)

    approved = deps.billing_preparation_service._billing_repo.get_preparation(preparation.id)
    assert approved.status == BillingPreparationStatus.APPROVED
    assert approved.approved_by == services["user_session"].principal.user_id
    assert result.post_commit_events == (
        ApprovalPostCommitEvent("billing_preparations_changed", project.id),
    )


def test_participant_reject_rejects_preparation_on_the_supplied_session(services, session):
    _login(services, "admin", "ChangeMe123!")
    project, preparation, request = _submitted_preparation(services, session, suffix="B")

    deps = _deps(services, session)
    result = BillingPreparationApprovalParticipant().reject(request, deps)

    rejected = deps.billing_preparation_service._billing_repo.get_preparation(preparation.id)
    assert rejected.status == BillingPreparationStatus.REJECTED
    assert rejected.rejected_by == services["user_session"].principal.user_id
    assert result.post_commit_events == (
        ApprovalPostCommitEvent("billing_preparations_changed", project.id),
    )


def test_participant_never_calls_commit_or_rollback(services, session, monkeypatch):
    """The participant stages only -- the caller (today: ApprovalService on the shared Session;
    from Step 2 onward: its own PlatformUnitOfWork) owns transaction completion."""
    _login(services, "admin", "ChangeMe123!")
    _, _preparation, request = _submitted_preparation(services, session, suffix="C")
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

        service_a = deps_a.billing_preparation_service
        service_b = deps_b.billing_preparation_service

        assert service_a._session is session_a
        assert service_b._session is session_b
        assert service_a is not service_b
        assert service_a._billing_repo.session is session_a
        assert service_b._billing_repo.session is session_b
        assert service_a._financial_profile_repo.session is session_a
        assert service_b._financial_profile_repo.session is session_b
        assert service_a._cost_entry_repo.session is session_a
        assert service_b._cost_entry_repo.session is session_b
        assert service_a._labor_posting_repo.session is session_a
        assert service_b._labor_posting_repo.session is session_b

        # Nested fresh collaborators: RateCardResolver wraps a Session-bound reader, and
        # FinancialPeriodService is itself Session-bound -- both must follow the same Session
        # as the rest of this deps bundle, never the other engine's.
        assert service_a._rate_resolver is not service_b._rate_resolver
        assert service_a._rate_resolver._reader._session is session_a
        assert service_b._rate_resolver._reader._session is session_b
        assert service_a._financial_period_service is not service_b._financial_period_service
        assert service_a._financial_period_service._session is session_a
        assert service_b._financial_period_service._session is session_b
        assert service_a._financial_period_service._period_repo.session is session_a
        assert service_b._financial_period_service._period_repo.session is session_b

        assert service_a._enterprise_audit_service is not service_b._enterprise_audit_service
        assert service_a._enterprise_audit_service._session is session_a
        assert service_b._enterprise_audit_service._session is session_b
        assert service_a._financial_period_service._enterprise_audit_service is (
            service_a._enterprise_audit_service
        ), "the fresh FinancialPeriodService should share this factory's fresh audit service"

        assert service_a._approval_service is None, (
            "the apply path must never reach back into ApprovalService"
        )
        assert service_b._approval_service is None
    finally:
        session_a.close()
        session_b.close()


def test_dependencies_factory_never_opens_its_own_session(services, session):
    deps = _deps(services, session)
    assert deps.billing_preparation_service._session is session, (
        "the factory must use the supplied Session, never a fresh one"
    )

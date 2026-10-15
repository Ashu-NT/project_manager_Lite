"""`FinancialChangeApprovalParticipant` stages a financial change on a caller-supplied Session
without opening or completing its own transaction.

Scope: BUDGET and FORECAST successor authorities share the deciding Session;
the SCHEDULE branch is covered end-to-end by `test_project_finance_change_orders.py`.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.core.modules.project_management.application.financials.budgets.budget_events import (
    BudgetStatusChanged,
    BudgetStatusChangeType,
)
from src.core.modules.project_management.application.financials.budgets.commands import (
    BudgetApprovalCommands,
)
from src.core.modules.project_management.application.financials.financial_changes.commands.approval import (
    FinancialChangeApprovalCommandHandler,
)
from src.core.modules.project_management.application.financials.financial_changes.financial_change_events import (
    FinancialChangeChanged,
    FinancialChangeEventType,
)
from src.core.modules.project_management.application.financials.financial_changes.mutation_result import (
    FinancialChangeImpactMutationResult,
)
from src.core.modules.project_management.application.financials.forecasts.commands import (
    ForecastApprovalCommands,
)
from src.core.modules.project_management.application.financials.forecasts.forecast_events import (
    ForecastVersionChanged,
    ForecastVersionChangeType,
)
from src.core.modules.project_management.domain.financials.financial_change import (
    FinancialChangeImpactType,
    FinancialChangeStatus,
)
from src.core.modules.project_management.domain.financials.forecast import (
    ForecastGenerationMode,
    ForecastLineSourceKind,
    ForecastLineSourceType,
    ForecastStatus,
)
from src.core.modules.project_management.infrastructure.approval.financial_change_apply_participant import (
    FinancialChangeApprovalParticipant,
)
from src.core.modules.project_management.infrastructure.composition.registrations.approvals.finance.financial_change import (
    build_financial_change_approval_deps,
)
from src.core.platform.common.exceptions import BusinessRuleError
from src.infra.persistence.orm.base import Base


def _login(services, username: str, password: str) -> None:
    user_session = services["user_session"]
    user = services["authentication"].authenticate(username, password)
    user_session.set_principal(services["principal_builder"].build(user))


def _seed_approved_budget(services):
    project = services["project_create"].create_project(
        "FC Approval Test Project", financial_currency_code="USD"
    )
    boundary = services["finance_governance_commands"]
    code = boundary.cost_code(
        lambda commands: commands.create_cost_code(
            code="FC-APPROVAL-TEST", name="FC approval test cost code"
        )
    )
    budgets = services["budget_query"]
    budget = boundary.budget_lifecycle(
        lambda commands: commands.create_budget(project.id, "Approved control budget")
    )
    budget_line = boundary.budget_lines(
        lambda commands: commands.add_line(
            budget.id,
            cost_code_id=code.id,
            description="Approved scope",
            amount=Decimal(100),
            expected_budget_version=budget.row_version,
        )
    )
    budget = budgets.get_budget(budget.id)
    budget = boundary.budget_lifecycle(
        lambda commands: commands.submit_budget(
            budget.id, "admin", expected_version=budget.row_version
        )
    )
    result = boundary.budget_approval(
        lambda commands: commands.approve_budget(
            budget.id, approved_by="admin", expected_version=budget.row_version
        )
    )
    budget = budgets.get_budget(result.budget_id)
    return project, code, budget, budget_line


def _seed_approved_forecast(services, project, code):
    boundary = services["finance_governance_commands"]
    principal = services["user_session"].principal
    forecast = boundary.forecast_lifecycle(
        lambda commands: commands.create_forecast(
            project.id,
            name="Approved forecast",
            as_of_date=date(2026, 8, 11),
            generation_mode=ForecastGenerationMode.MANUAL,
            created_by=principal.user_id,
        )
    )
    line = boundary.forecast_lines(
        lambda commands: commands.add_line(
            forecast.id,
            cost_code_id=code.id,
            description="Approved ETC",
            amount=Decimal(80),
            source_kind=ForecastLineSourceKind.MANUAL,
            source_type=ForecastLineSourceType.MANUAL_ESTIMATE,
            created_by=principal.user_id,
            expected_forecast_version=forecast.row_version,
        )
    )
    forecast = services["forecast_version_query"].get_forecast(forecast.id)
    forecast = boundary.forecast_lifecycle(
        lambda commands: commands.submit_forecast(
            forecast.id,
            submitted_by=principal.user_id,
            expected_version=forecast.row_version,
        )
    )
    forecast = boundary.forecast_approval(
        lambda commands: commands.approve_forecast(
            forecast.id,
            approved_by=principal.user_id,
            expected_version=forecast.row_version,
        )
    )
    return forecast, line


def _submitted_change(services, session, *, include_forecast=False):
    project, code, _budget, budget_line = _seed_approved_budget(services)
    boundary = services["finance_governance_commands"]
    principal = services["user_session"].principal
    if include_forecast:
        _forecast, forecast_line = _seed_approved_forecast(services, project, code)
    change = boundary.financial_change(
        lambda commands: commands.create_change(
            project.id,
            title="Approved scope adjustment",
            reason="Customer-approved engineering change",
            effective_date=date(2026, 8, 11),
            created_by=principal.user_id,
        )
    )
    mutation = boundary.financial_change(
        lambda commands: commands.add_impact(
            change.id,
            impact_type=FinancialChangeImpactType.BUDGET,
            description="Increase approved scope",
            amount=Decimal(25),
            cost_code_id=code.id,
            target_line_id=budget_line.id,
            expected_change_version=change.row_version,
        )
    )
    change = mutation.change
    if include_forecast:
        mutation = boundary.financial_change(
            lambda commands: commands.add_impact(
                change.id,
                impact_type=FinancialChangeImpactType.FORECAST,
                description="Increase approved ETC",
                amount=Decimal("12.50"),
                cost_code_id=code.id,
                target_line_id=forecast_line.id,
                expected_change_version=change.row_version,
            )
        )
        change = mutation.change
    change = boundary.financial_change_submission(
        lambda commands: commands.submit_change(
            change.id,
            submitted_by=principal.user_id,
            expected_version=change.row_version,
        )
    )
    session.expire_all()
    request = services["approval_queries"].list_pending(project_id=project.id)[0]
    return project, change, request


def _deps(services, session):
    return build_financial_change_approval_deps(
        session,
        user_session=services["user_session"],
        tenant_context_service=services["tenant_context_service"],
        work_calendar_engine=services["work_calendar_engine"],
    )


def test_impact_mutations_return_parent_and_impact_from_the_command_transaction(services):
    _login(services, "admin", "ChangeMe123!")
    project, code, _, budget_line = _seed_approved_budget(services)
    boundary = services["finance_governance_commands"]
    change = boundary.financial_change(
        lambda commands: commands.create_change(
            project.id,
            title="Scope adjustment",
            reason="Customer request",
            effective_date=date(2026, 8, 11),
            created_by=services["user_session"].principal.user_id,
        )
    )
    version = change.row_version

    added = boundary.financial_change(
        lambda commands: commands.add_impact(
            change.id,
            impact_type=FinancialChangeImpactType.BUDGET,
            description="Additional scope",
            amount=Decimal("25.50"),
            cost_code_id=code.id,
            target_line_id=budget_line.id,
            expected_change_version=version,
        )
    )

    assert isinstance(added, FinancialChangeImpactMutationResult)
    assert added.change.id == added.impact.change_request_id == change.id
    assert added.change.row_version == version + 1
    assert added.impact.amount == Decimal("25.50")
    with pytest.raises(FrozenInstanceError):
        added.change = change

    updated = boundary.financial_change(
        lambda commands: commands.update_impact(
            added.impact.id,
            impact_type=FinancialChangeImpactType.BUDGET,
            description="Revised additional scope",
            amount=Decimal("30.75"),
            cost_code_id=code.id,
            target_line_id=budget_line.id,
            expected_change_version=added.change.row_version,
            expected_impact_version=added.impact.row_version,
        )
    )

    assert isinstance(updated, FinancialChangeImpactMutationResult)
    assert updated.change.id == updated.impact.change_request_id == change.id
    assert updated.change.row_version == version + 2
    assert updated.impact.row_version == added.impact.row_version + 1
    assert updated.impact.amount == Decimal("30.75")


def test_participant_apply_applies_change_on_the_supplied_session_with_budget_only_events(
    services, session
):
    _login(services, "admin", "ChangeMe123!")
    project, change, request = _submitted_change(services, session)
    deps = _deps(services, session)

    result = FinancialChangeApprovalParticipant().apply(request, deps)

    applied = deps.financial_change_commands._change_repo.get(change.id)
    assert applied.status is FinancialChangeStatus.APPLIED
    assert applied.applied_budget_id
    assert applied.applied_forecast_id is None
    assert not applied.applied_schedule_count
    change_event = next(
        event
        for event in result.domain_events
        if isinstance(event, FinancialChangeChanged)
    )
    assert change_event.change_type is FinancialChangeEventType.APPLIED
    assert change_event.applied_effects == ("budget",)

    budget_status_events = [
        event
        for event in result.domain_events
        if isinstance(event, BudgetStatusChanged)
    ]
    assert [event.change_type for event in budget_status_events] == [
        BudgetStatusChangeType.SUPERSEDED
    ]
    assert budget_status_events[0].project_id == project.id


def test_participant_reject_rejects_change_on_the_supplied_session(services, session):
    _login(services, "admin", "ChangeMe123!")
    _, change, request = _submitted_change(services, session)
    deps = _deps(services, session)

    result = FinancialChangeApprovalParticipant().reject(request, deps)

    rejected = deps.financial_change_commands._change_repo.get(change.id)
    assert rejected.status is FinancialChangeStatus.REJECTED
    assert result.domain_events == (
        FinancialChangeChanged(
            tenant_id=rejected.tenant_id,
            organization_id=rejected.organization_id,
            project_id=rejected.project_id,
            change_id=rejected.id,
            change_type=FinancialChangeEventType.REJECTED,
            occurred_at=rejected.rejected_at,
        ),
    )


def test_participant_applies_budget_and_forecast_successors_on_the_shared_session(
    services, session
):
    _login(services, "admin", "ChangeMe123!")
    _, change, request = _submitted_change(services, session, include_forecast=True)
    deps = _deps(services, session)
    commands = deps.financial_change_commands
    assert isinstance(commands, FinancialChangeApprovalCommandHandler)
    assert isinstance(commands._budget_authority, BudgetApprovalCommands)
    assert isinstance(commands._forecast_authority, ForecastApprovalCommands)
    assert commands._session is session
    assert commands._budget_authority._session is session
    assert commands._forecast_authority._session is session

    result = FinancialChangeApprovalParticipant().apply(request, deps)

    applied = commands._change_repo.get(change.id)
    assert applied.status is FinancialChangeStatus.APPLIED
    budget_lines = commands._budget_repo.list_lines(applied.applied_budget_id)
    forecast_lines = commands._forecast_repo.list_lines(applied.applied_forecast_id)
    assert [line.amount for line in budget_lines] == [Decimal(125)]
    assert [line.amount for line in forecast_lines] == [Decimal("92.50")]
    forecast = commands._forecast_repo.get(applied.applied_forecast_id)
    assert forecast.status is ForecastStatus.APPROVED
    assert next(
        event
        for event in result.domain_events
        if isinstance(event, FinancialChangeChanged)
    ).applied_effects == ("budget", "forecast")
    assert (
        next(
            event
            for event in result.domain_events
            if isinstance(event, ForecastVersionChanged)
        ).change_type
        is ForecastVersionChangeType.APPROVED
    )


@pytest.mark.parametrize("include_forecast", [False, True])
@pytest.mark.parametrize("decision", ["apply", "reject"])
def test_participant_never_calls_commit_or_rollback(
    services, session, monkeypatch, include_forecast, decision
):
    """The participant stages only; the caller owns transaction completion."""
    _login(services, "admin", "ChangeMe123!")
    _, _, request = _submitted_change(
        services, session, include_forecast=include_forecast
    )
    deps = _deps(services, session)

    def _forbidden(*_args, **_kwargs):
        raise AssertionError(
            "the participant must never commit or roll back its own Session"
        )

    monkeypatch.setattr(type(session), "commit", _forbidden)
    monkeypatch.setattr(type(session), "rollback", _forbidden)

    getattr(FinancialChangeApprovalParticipant(), decision)(request, deps)


@pytest.mark.parametrize("decision", ["apply", "reject"])
def test_participant_requires_authenticated_actor(services, session, decision):
    _login(services, "admin", "ChangeMe123!")
    _, _, request = _submitted_change(services, session)
    deps = build_financial_change_approval_deps(
        session,
        user_session=_BlankUserSession(),
        tenant_context_service=services["tenant_context_service"],
        work_calendar_engine=services["work_calendar_engine"],
    )

    with pytest.raises(BusinessRuleError, match="authenticated principal"):
        getattr(FinancialChangeApprovalParticipant(), decision)(request, deps)


@pytest.mark.parametrize("include_forecast", [False, True])
def test_caller_rollback_discards_change_and_successor_versions(
    services, session, include_forecast
):
    _login(services, "admin", "ChangeMe123!")
    _, change, request = _submitted_change(
        services, session, include_forecast=include_forecast
    )
    deps = _deps(services, session)
    commands = deps.financial_change_commands
    change_id = change.id
    base_budget_id = change.base_budget_id
    base_forecast_id = change.base_forecast_id

    FinancialChangeApprovalParticipant().apply(request, deps)

    applied = commands._change_repo.get(change_id)
    successor_budget_id = applied.applied_budget_id
    successor_forecast_id = applied.applied_forecast_id
    assert successor_budget_id != base_budget_id
    if include_forecast:
        assert successor_forecast_id != base_forecast_id

    session.rollback()

    restored = commands._change_repo.get(change_id)
    assert restored.status is FinancialChangeStatus.PENDING_APPROVAL
    assert restored.applied_budget_id is None
    assert restored.applied_forecast_id is None
    assert commands._budget_repo.get(successor_budget_id) is None
    assert (
        commands._budget_repo.get_approved_for_project(restored.project_id).id
        == base_budget_id
    )
    if include_forecast:
        assert commands._forecast_repo.get(successor_forecast_id) is None
        assert (
            commands._forecast_repo.get_approved_for_project(restored.project_id).id
            == base_forecast_id
        )


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

        change_service_a = deps_a.financial_change_commands
        change_service_b = deps_b.financial_change_commands

        assert change_service_a._session is session_a
        assert change_service_b._session is session_b
        assert change_service_a._change_repo.session is session_a
        assert change_service_b._change_repo.session is session_b
        assert change_service_a is not change_service_b
        assert change_service_a._enterprise_audit_service is not (
            change_service_b._enterprise_audit_service
        )
        assert change_service_a._enterprise_audit_service._session is session_a
        assert change_service_b._enterprise_audit_service._session is session_b
        assert not hasattr(change_service_a, "_approval_commands"), (
            "the apply path must never reach back into ApprovalCommandHandler"
        )
        for owner, supplied_session in (
            (change_service_a, session_a),
            (change_service_b, session_b),
        ):
            assert isinstance(owner, FinancialChangeApprovalCommandHandler)
            assert isinstance(owner._budget_authority, BudgetApprovalCommands)
            assert isinstance(owner._forecast_authority, ForecastApprovalCommands)
            for authority in (owner._budget_authority, owner._forecast_authority):
                assert authority._session is supplied_session
                assert authority._enterprise_audit_service._session is supplied_session
                assert authority._approval_commands is None
            assert owner._budget_authority._budget_repo.session is supplied_session
            assert owner._forecast_authority._forecast_repo.session is supplied_session

        task_service_a = change_service_a._task_service
        task_service_b = change_service_b._task_service
        assert task_service_a is not task_service_b
        assert task_service_a._uow_scope._tasks.session is session_a
        assert task_service_b._uow_scope._tasks.session is session_b
        assert task_service_a._uow_scope._enterprise_audit_service._session is session_a
        assert task_service_b._uow_scope._enterprise_audit_service._session is session_b
        assert not hasattr(task_service_a, "_approval_commands")
        scheduler_a = task_service_a._scheduling_engine
        scheduler_b = task_service_b._scheduling_engine
        assert scheduler_a is not scheduler_b
        assert scheduler_a._session is session_a
        assert scheduler_b._session is session_b
        activity_a = task_service_a._uow_scope._activity_service
        activity_b = task_service_b._uow_scope._activity_service
        assert activity_a is not activity_b
        assert activity_a._session is session_a
        assert activity_b._session is session_b
    finally:
        session_a.close()
        session_b.close()


def test_dependencies_factory_never_opens_its_own_session(services, session):
    deps = _deps(services, session)
    assert deps.financial_change_commands._session is session, (
        "the factory must use the supplied Session, never a fresh one"
    )

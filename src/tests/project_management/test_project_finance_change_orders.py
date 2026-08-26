from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config

from src.core.modules.project_management.domain.financials.budget import BudgetStatus
from src.core.modules.project_management.domain.financials.financial_change import (
    FinancialChangeImpact,
    FinancialChangeImpactType,
    FinancialChangeStatus,
)
from src.core.modules.project_management.domain.financials.forecast import (
    ForecastGenerationMode,
    ForecastLineSourceKind,
    ForecastLineSourceType,
    ForecastStatus,
)
from src.core.platform.common.exceptions import (
    BusinessRuleError,
    ConcurrencyError,
    ValidationError,
)


def _login(services, username: str, password: str) -> None:
    user = services["auth_service"].authenticate(username, password)
    services["user_session"].set_principal(
        services["auth_service"].build_principal(user)
    )


def _seed_approved_finance(services):
    project = services["project_service"].create_project(
        "Controlled Change Project", financial_currency_code="USD"
    )
    code = services["financial_configuration_service"].create_cost_code(
        code="CHG-001", name="Change control"
    )

    budgets = services["budget_service"]
    budget = budgets.create_budget(project.id, "Approved control budget")
    budget_line = budgets.add_line(
        budget.id,
        cost_code_id=code.id,
        description="Approved scope",
        amount=Decimal("100"),
        expected_budget_version=budget.row_version,
    )
    budget = budgets.get_budget(budget.id)
    budget = budgets.submit_budget(
        budget.id, "admin", expected_version=budget.row_version
    )
    result = budgets.approve_budget(
        budget.id, approved_by="admin", expected_version=budget.row_version
    )
    budget = budgets.get_budget(result.budget_id)

    forecasts = services["forecast_version_service"]
    forecast = forecasts.create_forecast(
        project.id,
        name="Approved forecast",
        as_of_date=date(2026, 8, 11),
        generation_mode=ForecastGenerationMode.MANUAL,
        created_by="admin",
    )
    forecast_line = forecasts.add_line(
        forecast.id,
        cost_code_id=code.id,
        description="Approved ETC",
        amount=Decimal("80"),
        source_kind=ForecastLineSourceKind.MANUAL,
        source_type=ForecastLineSourceType.MANUAL_ESTIMATE,
        created_by="admin",
        expected_forecast_version=forecast.row_version,
    )
    forecast = forecasts.get_forecast(forecast.id)
    forecast = forecasts.submit_forecast(
        forecast.id, submitted_by="admin", expected_version=forecast.row_version
    )
    forecast = forecasts.approve_forecast(
        forecast.id, approved_by="admin", expected_version=forecast.row_version
    )
    return project, code, budget, budget_line, forecast, forecast_line


def _draft_change(services, project):
    principal = services["user_session"].principal
    return services["financial_change_service"].create_change(
        project.id,
        title="Approved scope adjustment",
        reason="Customer-approved engineering change",
        effective_date=date(2026, 8, 11),
        created_by=principal.user_id,
    )


def test_submit_change_uses_a_fresh_uow_session_shared_by_the_approval_request(
    services, monkeypatch
) -> None:
    """Approval-P1: `submit_change` is converged onto `FinancialChangeSubmissionUnitOfWork` --
    a genuinely fresh Session per call, distinct from the shared legacy Session, with the
    financial change update and the Approval request sharing that one Session/transaction."""
    _login(services, "admin", "ChangeMe123!")
    project, code, budget, budget_line, _forecast, _forecast_line = _seed_approved_finance(
        services
    )
    changes = services["financial_change_service"]
    change = _draft_change(services, project)
    changes.add_impact(
        change.id,
        impact_type=FinancialChangeImpactType.BUDGET,
        description="Increase approved scope",
        amount=Decimal("10"),
        cost_code_id=code.id,
        target_line_id=budget_line.id,
        expected_change_version=change.row_version,
    )
    change = changes.get_change(change.id)

    seen_uows = []
    original_create = type(changes._submission_uow_factory).create

    def _spy_create(self, *, context):
        uow = original_create(self, context=context)
        seen_uows.append(uow)
        return uow

    monkeypatch.setattr(type(changes._submission_uow_factory), "create", _spy_create)
    submitted = changes.submit_change(
        change.id,
        submitted_by=services["user_session"].principal.user_id,
        expected_version=change.row_version,
    )

    assert len(seen_uows) == 1
    uow = seen_uows[0]
    assert uow._session is not changes._session
    assert uow.changes.session is uow._session
    assert uow.approvals.session is uow._session
    assert uow._enterprise_audit_service._session is uow._session
    assert submitted.status is FinancialChangeStatus.PENDING_APPROVAL


def test_submit_change_commit_failure_rolls_back_change_and_approval_request_together(
    services, monkeypatch
) -> None:
    """Approval-P1 (§23-26): a commit failure inside `submit_change`'s canonical UoW must roll
    back the WHOLE transaction -- the financial change must remain in its pre-submit state, and
    no `ApprovalRequest` may have been persisted independently of its host command."""
    from src.core.modules.project_management.infrastructure.persistence.financial_change_submission_unit_of_work import (
        SqlAlchemyFinancialChangeSubmissionUnitOfWork,
    )

    _login(services, "admin", "ChangeMe123!")
    project, code, budget, budget_line, _forecast, _forecast_line = _seed_approved_finance(
        services
    )
    changes = services["financial_change_service"]
    change = _draft_change(services, project)
    changes.add_impact(
        change.id,
        impact_type=FinancialChangeImpactType.BUDGET,
        description="Increase approved scope",
        amount=Decimal("10"),
        cost_code_id=code.id,
        target_line_id=budget_line.id,
        expected_change_version=change.row_version,
    )
    change = changes.get_change(change.id)
    pending_count_before = len(services["approval_service"].list_pending(project_id=project.id))

    def _fail_commit(self):
        raise RuntimeError("simulated financial change submission commit failure")

    monkeypatch.setattr(SqlAlchemyFinancialChangeSubmissionUnitOfWork, "commit", _fail_commit)

    with pytest.raises(RuntimeError, match="simulated financial change submission commit failure"):
        changes.submit_change(
            change.id,
            submitted_by=services["user_session"].principal.user_id,
            expected_version=change.row_version,
        )

    monkeypatch.undo()
    reloaded = changes.get_change(change.id)
    assert reloaded.status is FinancialChangeStatus.DRAFT
    pending_after = services["approval_service"].list_pending(project_id=project.id)
    assert len(pending_after) == pending_count_before


def test_negative_financial_delta_requires_an_exact_target() -> None:
    with pytest.raises(ValidationError):
        FinancialChangeImpact.create(
            tenant_id="tenant-a",
            organization_id="org-a",
            change_request_id="change-a",
            project_id="project-a",
            impact_type=FinancialChangeImpactType.BUDGET,
            description="Unscoped reduction",
            amount=Decimal("-10"),
            currency_code="USD",
            cost_code_id="code-a",
        )


def test_approved_change_atomically_creates_budget_and_forecast_successors(
    services,
) -> None:
    _login(services, "admin", "ChangeMe123!")
    project, code, budget, budget_line, forecast, forecast_line = (
        _seed_approved_finance(services)
    )
    services["auth_service"].register_user(
        "change-requester", "StrongPass123", role_names=["planner"]
    )
    _login(services, "change-requester", "StrongPass123")

    changes = services["financial_change_service"]
    change = _draft_change(services, project)
    budget_impact = changes.add_impact(
        change.id,
        impact_type=FinancialChangeImpactType.BUDGET,
        description="Increase approved scope",
        amount=Decimal("25"),
        cost_code_id=code.id,
        target_line_id=budget_line.id,
        expected_change_version=change.row_version,
    )
    change = changes.get_change(change.id)
    forecast_impact = changes.add_impact(
        change.id,
        impact_type=FinancialChangeImpactType.FORECAST,
        description="Reduce remaining ETC",
        amount=Decimal("-15"),
        cost_code_id=code.id,
        target_line_id=forecast_line.id,
        expected_change_version=change.row_version,
    )
    change = changes.get_change(change.id)
    change = changes.submit_change(
        change.id,
        submitted_by=services["user_session"].principal.user_id,
        expected_version=change.row_version,
    )
    assert change.status is FinancialChangeStatus.PENDING_APPROVAL
    request = services["approval_service"].list_pending(project_id=project.id)[0]
    assert request.request_type == "financial_change.apply"

    _login(services, "admin", "ChangeMe123!")
    admin_id = services["user_session"].principal.user_id
    services["approval_service"].approve_and_apply(
        request.id, note="Authorized change"
    )

    applied = changes.get_change(change.id)
    assert applied.status is FinancialChangeStatus.APPLIED
    assert applied.applied_by == admin_id
    assert applied.applied_budget_id and applied.applied_budget_id != budget.id
    assert applied.applied_forecast_id and applied.applied_forecast_id != forecast.id

    budgets = services["budget_service"]
    assert budgets.get_budget(budget.id).status is BudgetStatus.SUPERSEDED
    successor_budget = budgets.get_budget(applied.applied_budget_id)
    assert successor_budget.status is BudgetStatus.APPROVED
    assert budgets.list_lines(successor_budget.id)[0].amount == Decimal("125")

    forecasts = services["forecast_version_service"]
    assert forecasts.get_forecast(forecast.id).status is ForecastStatus.SUPERSEDED
    successor_forecast = forecasts.get_forecast(applied.applied_forecast_id)
    assert successor_forecast.status is ForecastStatus.APPROVED
    assert forecasts.list_lines(successor_forecast.id)[0].amount == Decimal("65")
    assert {
        row.source_type for row in forecasts.list_source_decisions(successor_forecast.id)
    } == {ForecastLineSourceType.FINANCIAL_CHANGE}

    impacts = {row.id: row for row in changes.list_impacts(applied.id)}
    assert impacts[budget_impact.id].applied_reference_type == "budget_line"
    assert impacts[budget_impact.id].applied_reference_id
    assert impacts[forecast_impact.id].applied_reference_type == "forecast_line"
    assert impacts[forecast_impact.id].applied_reference_id


def test_contract_placeholder_is_not_part_of_canonical_change_control() -> None:
    assert {item.value for item in FinancialChangeImpactType} == {
        "budget",
        "forecast",
        "schedule",
    }


def test_approved_schedule_change_uses_task_owner_command(services) -> None:
    _login(services, "admin", "ChangeMe123!")
    project = services["project_service"].create_project(
        "Schedule Change Project", financial_currency_code="USD"
    )
    task = services["task_service"].create_task(
        project.id,
        "Scheduled Delivery",
        start_date=date(2026, 8, 10),
        duration_days=4,
    )
    services["auth_service"].register_user(
        "schedule-requester", "StrongPass123", role_names=["planner"]
    )
    _login(services, "schedule-requester", "StrongPass123")
    changes = services["financial_change_service"]
    change = _draft_change(services, project)
    impact = changes.add_impact(
        change.id,
        impact_type=FinancialChangeImpactType.SCHEDULE,
        description="Move delivery window",
        task_id=task.id,
        schedule_start=date(2026, 8, 17),
        schedule_finish=date(2026, 8, 21),
        expected_change_version=change.row_version,
    )
    assert impact.target_task_version == task.version
    change = changes.get_change(change.id)
    changes.submit_change(
        change.id,
        submitted_by=services["user_session"].principal.user_id,
        expected_version=change.row_version,
    )
    request = services["approval_service"].list_pending(project_id=project.id)[0]

    _login(services, "admin", "ChangeMe123!")
    services["approval_service"].approve_and_apply(request.id)

    applied = changes.get_change(change.id)
    scheduled = services["task_service"].get_task(task.id)
    applied_impact = changes.list_impacts(change.id)[0]
    assert applied.status is FinancialChangeStatus.APPLIED
    assert applied.applied_schedule_count == 1
    assert scheduled.start_date == date(2026, 8, 17)
    assert scheduled.end_date == date(2026, 8, 21)
    assert scheduled.duration_days == 5
    assert applied_impact.applied_reference_type == "task"
    assert applied_impact.applied_reference_id == task.id


def test_schedule_submission_rejects_a_stale_task_snapshot(
    services,
) -> None:
    _login(services, "admin", "ChangeMe123!")
    project = services["project_service"].create_project(
        "Stale Schedule Project", financial_currency_code="USD"
    )
    task = services["task_service"].create_task(
        project.id,
        "Schedule Target",
        start_date=date(2026, 8, 10),
        duration_days=4,
    )
    changes = services["financial_change_service"]
    change = _draft_change(services, project)
    changes.add_impact(
        change.id,
        impact_type=FinancialChangeImpactType.SCHEDULE,
        description="Move stale target",
        task_id=task.id,
        schedule_start=date(2026, 8, 17),
        schedule_finish=date(2026, 8, 21),
        expected_change_version=change.row_version,
    )
    change = changes.get_change(change.id)
    services["task_service"].update_task(
        task.id,
        description="Changed after impact capture",
        expected_version=task.version,
    )

    with pytest.raises(ConcurrencyError):
        changes.submit_change(
            change.id, submitted_by="admin", expected_version=change.row_version
        )
    assert changes.get_change(change.id).status is FinancialChangeStatus.DRAFT


def test_schedule_impact_rejects_summary_task_at_draft_entry(services) -> None:
    _login(services, "admin", "ChangeMe123!")
    project = services["project_service"].create_project(
        "Summary Schedule Project", financial_currency_code="USD"
    )
    summary = services["task_service"].create_task(
        project.id, "Summary Delivery"
    )
    services["task_service"].create_task(
        project.id,
        "Execution Delivery",
        start_date=date(2026, 8, 10),
        duration_days=4,
        parent_task_id=summary.id,
    )
    change = _draft_change(services, project)

    with pytest.raises(BusinessRuleError) as exc_info:
        services["financial_change_service"].add_impact(
            change.id,
            impact_type=FinancialChangeImpactType.SCHEDULE,
            description="Invalid summary move",
            task_id=summary.id,
            schedule_start=date(2026, 8, 17),
            schedule_finish=date(2026, 8, 21),
            expected_change_version=change.row_version,
        )
    assert exc_info.value.code == "TASK_WBS_SUMMARY_EXECUTION_FORBIDDEN"
    assert services["financial_change_service"].list_impacts(change.id) == []


def test_impact_write_rolls_back_when_financial_audit_fails(
    services, monkeypatch
) -> None:
    _login(services, "admin", "ChangeMe123!")
    project, code, _, budget_line, *_ = _seed_approved_finance(services)
    changes = services["financial_change_service"]
    change = _draft_change(services, project)
    monkeypatch.setattr(
        changes,
        "_audit_impact",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            RuntimeError("audit unavailable")
        ),
    )

    with pytest.raises(RuntimeError, match="audit unavailable"):
        changes.add_impact(
            change.id,
            impact_type=FinancialChangeImpactType.BUDGET,
            description="Must be atomic",
            amount=Decimal("5"),
            cost_code_id=code.id,
            target_line_id=budget_line.id,
            expected_change_version=change.row_version,
        )

    assert changes.list_impacts(change.id) == []
    assert changes.get_change(change.id).row_version == change.row_version


def test_approval_rolls_back_all_successors_when_financial_audit_fails(
    services, monkeypatch
) -> None:
    _login(services, "admin", "ChangeMe123!")
    project, code, budget, budget_line, *_ = _seed_approved_finance(services)
    task = services["task_service"].create_task(
        project.id,
        "Atomic Schedule Target",
        start_date=date(2026, 8, 10),
        duration_days=4,
    )
    services["auth_service"].register_user(
        "rollback-requester", "StrongPass123", role_names=["planner"]
    )
    _login(services, "rollback-requester", "StrongPass123")
    changes = services["financial_change_service"]
    change = _draft_change(services, project)
    changes.add_impact(
        change.id,
        impact_type=FinancialChangeImpactType.BUDGET,
        description="Audited increase",
        amount=Decimal("5"),
        cost_code_id=code.id,
        target_line_id=budget_line.id,
        expected_change_version=change.row_version,
    )
    change = changes.get_change(change.id)
    changes.add_impact(
        change.id,
        impact_type=FinancialChangeImpactType.SCHEDULE,
        description="Atomic schedule move",
        task_id=task.id,
        schedule_start=date(2026, 8, 17),
        schedule_finish=date(2026, 8, 21),
        expected_change_version=change.row_version,
    )
    change = changes.get_change(change.id)
    changes.submit_change(
        change.id,
        submitted_by=services["user_session"].principal.user_id,
        expected_version=change.row_version,
    )
    request = services["approval_service"].list_pending(project_id=project.id)[0]

    _login(services, "admin", "ChangeMe123!")
    monkeypatch.setattr(
        type(changes),
        "_audit_change",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            RuntimeError("audit unavailable")
        ),
    )
    with pytest.raises(RuntimeError, match="audit unavailable"):
        services["approval_service"].approve_and_apply(request.id)

    assert changes.get_change(change.id).status is FinancialChangeStatus.PENDING_APPROVAL
    assert services["budget_service"].get_budget(budget.id).status is BudgetStatus.APPROVED
    assert len(services["budget_service"].list_budgets_for_project(project.id)) == 1
    rolled_back_task = services["task_service"].get_task(task.id)
    assert rolled_back_task.start_date == date(2026, 8, 10)
    assert rolled_back_task.end_date == date(2026, 8, 13)
    assert services["approval_service"].list_pending(project_id=project.id)[0].id == request.id


def test_financial_change_migration_is_reversible_and_constrained(tmp_path) -> None:
    database_path = tmp_path / "financial-change-migration.db"
    config = Config("src/infra/persistence/migrations/alembic.ini")
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path.as_posix()}")
    command.upgrade(config, "head")
    engine = sa.create_engine(config.get_main_option("sqlalchemy.url"), future=True)
    inspector = sa.inspect(engine)

    assert {
        "project_finance_change_requests",
        "project_finance_change_impacts",
    } <= set(inspector.get_table_names())
    request_checks = {
        row["name"] for row in inspector.get_check_constraints(
            "project_finance_change_requests"
        )
    }
    impact_checks = {
        row["name"] for row in inspector.get_check_constraints(
            "project_finance_change_impacts"
        )
    }
    request_constraints = {
        row["name"] for row in inspector.get_unique_constraints(
            "project_finance_change_requests"
        )
    }
    assert "ck_pf_changes_status" in request_checks
    assert "ck_pf_change_impacts_monetary_shape" in impact_checks
    assert "ck_pf_change_impacts_task_version" in impact_checks
    assert "ck_pf_change_impacts_applied_type" in impact_checks
    assert "uq_pf_change_project_revision" in request_constraints
    impact_columns = {
        row["name"] for row in inspector.get_columns("project_finance_change_impacts")
    }
    assert "target_task_version" in impact_columns
    assert "applied_reference_type" in impact_columns
    assert "planned_hours_delta" not in impact_columns
    assert "source_reference_type" not in impact_columns
    engine.dispose()

    command.downgrade(config, "base")
    engine = sa.create_engine(config.get_main_option("sqlalchemy.url"), future=True)
    tables = set(sa.inspect(engine).get_table_names())
    assert "project_finance_change_requests" not in tables
    assert "project_finance_change_impacts" not in tables
    engine.dispose()

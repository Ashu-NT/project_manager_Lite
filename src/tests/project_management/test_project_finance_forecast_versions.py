from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config

from src.core.modules.project_management.application.financials.forecasts import (
    ManualEtcEstimate,
    RiskContingencyEstimate,
)
from src.core.modules.project_management.domain.financials.commitment import (
    ProjectCommitmentLineState,
)
from src.core.modules.project_management.domain.financials.cost_entry import (
    ProjectCostEntryKind,
    ProjectCostEntryStatus,
)
from src.core.modules.project_management.domain.financials.forecast import (
    ForecastDecisionReason,
    ForecastGenerationMode,
    ForecastLine,
    ForecastLineSourceKind,
    ForecastLineSourceType,
    ForecastStatus,
    ProjectForecast,
)
from src.core.modules.project_management.domain.risk.register import (
    RegisterEntry,
    RegisterEntryType,
)
from src.core.platform.common.exceptions import BusinessRuleError, ValidationError


def _project(services, name: str = "Forecast Project"):
    return services["project_service"].create_project(
        name, financial_currency_code="USD"
    )


def _cost_code(services, code: str = "FC-001"):
    return services["financial_configuration_service"].create_cost_code(
        code=code, name=code
    )


def _manual_line(services, forecast, code, amount: str = "125.3750"):
    return services["forecast_version_service"].add_line(
        forecast.id,
        cost_code_id=code.id,
        description="Remaining engineering estimate",
        amount=Decimal(amount),
        source_kind=ForecastLineSourceKind.MANUAL,
        source_type=ForecastLineSourceType.MANUAL_ESTIMATE,
        created_by="admin",
        expected_forecast_version=forecast.row_version,
    )


def _forecast(**overrides) -> ProjectForecast:
    values = {
        "tenant_id": "tenant-a",
        "organization_id": "org-a",
        "project_id": "project-a",
        "name": "Forecast",
        "currency_code": "USD",
        "as_of_date": date(2026, 8, 11),
        "generation_mode": ForecastGenerationMode.MANUAL,
        "created_by": "user-a",
    }
    values.update(overrides)
    return ProjectForecast.create(**values)


def _wire_generation_sources(
    monkeypatch,
    service,
    *,
    project,
    cost_code,
    planned_amount: str | None = "100",
    actual_amounts: tuple[str, ...] = (),
    commitment_amount: str | None = None,
    matched_amount: str = "0",
) -> None:
    as_of = service._clock.today()
    now = service._clock.now()
    version = SimpleNamespace(
        id="planned-version",
        project_id=project.id,
        as_of=as_of,
        revision=1,
        calculated_at=now,
        rates_complete=True,
        allocations_complete=True,
        cost_codes_complete=True,
    )
    planned_lines = []
    if planned_amount is not None:
        planned_lines.append(SimpleNamespace(
            id="planned-line",
            cost_code_id=cost_code.id,
            task_id=None,
            amount=Decimal(planned_amount),
            currency_code="USD",
        ))
    monkeypatch.setattr(
        service._planned_cost_repo,
        "list_for_project",
        lambda _project_id: [version] if planned_lines else [],
    )
    monkeypatch.setattr(
        service._planned_cost_repo,
        "list_lines",
        lambda _version_id: planned_lines,
    )

    commitments = []
    if commitment_amount is not None:
        amount = Decimal(commitment_amount)
        commitments.append(SimpleNamespace(
            id="commitment-line",
            purchase_order_line_id="po-line",
            cost_code_id=cost_code.id,
            task_id=None,
            amount=amount,
            matched_amount=Decimal(matched_amount),
            currency_code="USD",
            base_amount=amount,
            base_currency_code="USD",
            exchange_rate=Decimal("1"),
            state=ProjectCommitmentLineState.SENT,
            updated_at=now,
        ))

    def list_commitments(_project_id, *, offset, limit):
        del limit
        return (commitments, len(commitments)) if offset == 0 else ([], len(commitments))

    monkeypatch.setattr(
        service._commitment_repo, "list_lines_for_project", list_commitments
    )

    actuals = [
        SimpleNamespace(
            id=f"actual-{index}",
            cost_code_id=cost_code.id,
            task_id=None,
            amount=Decimal(amount),
            currency_code="USD",
            base_amount=Decimal(amount),
            base_currency_code="USD",
            posting_date=as_of,
            posted_at=now,
            updated_at=now,
            status=ProjectCostEntryStatus.POSTED,
            entry_kind=(
                ProjectCostEntryKind.ACTUAL
                if Decimal(amount) >= 0
                else ProjectCostEntryKind.ADJUSTMENT
            ),
        )
        for index, amount in enumerate(actual_amounts)
    ]

    def list_actuals(_project_id, *, status, offset, limit):
        del limit
        rows = actuals if status is ProjectCostEntryStatus.POSTED and offset == 0 else []
        total = len(actuals) if status is ProjectCostEntryStatus.POSTED else 0
        return rows, total

    monkeypatch.setattr(service._cost_entry_repo, "list_for_project", list_actuals)


def test_forecast_domain_lifecycle_is_explicit_and_immutable_after_submit() -> None:
    forecast = _forecast()
    now = datetime.now(timezone.utc)

    with pytest.raises(BusinessRuleError):
        forecast.approve(approved_by="reviewer", approved_at=now)

    forecast.submit(submitted_by="author", submitted_at=now)
    assert forecast.status is ForecastStatus.SUBMITTED
    with pytest.raises(BusinessRuleError) as exc:
        forecast.ensure_mutable()
    assert exc.value.code == "PROJECT_FORECAST_IMMUTABLE"

    forecast.approve(approved_by="reviewer", approved_at=now)
    assert forecast.status is ForecastStatus.APPROVED


def test_automatic_line_requires_reproducible_source_metadata() -> None:
    with pytest.raises((ValidationError, ValueError)):
        ForecastLine.create(
            tenant_id="tenant-a",
            organization_id="org-a",
            forecast_id="forecast-a",
            project_id="project-a",
            cost_code_id="code-a",
            description="Open commitment",
            amount=Decimal("10"),
            currency_code="USD",
            source_kind=ForecastLineSourceKind.AUTOMATIC,
            source_type=ForecastLineSourceType.OPEN_COMMITMENT,
            created_by="user-a",
        )


def test_manual_line_cannot_masquerade_as_an_automatic_source() -> None:
    with pytest.raises((ValidationError, ValueError)):
        ForecastLine.create(
            tenant_id="tenant-a",
            organization_id="org-a",
            forecast_id="forecast-a",
            project_id="project-a",
            cost_code_id="code-a",
            description="Invalid",
            amount=Decimal("10"),
            currency_code="USD",
            source_kind=ForecastLineSourceKind.MANUAL,
            source_type=ForecastLineSourceType.REMAINING_PLAN,
            created_by="user-a",
        )


def test_service_persists_decimal_forecast_and_approves_it(services) -> None:
    project = _project(services)
    code = _cost_code(services)
    service = services["forecast_version_service"]
    forecast = service.create_forecast(
        project.id,
        name="August forecast",
        as_of_date=date(2026, 8, 11),
        generation_mode=ForecastGenerationMode.MANUAL,
        created_by="admin",
    )

    line = _manual_line(services, forecast, code)
    assert line.amount == Decimal("125.3750")
    current = service.get_forecast(forecast.id)
    submitted = service.submit_forecast(
        forecast.id,
        submitted_by="admin",
        expected_version=current.row_version,
    )
    approved = service.approve_forecast(
        forecast.id,
        approved_by="admin",
        expected_version=submitted.row_version,
    )

    assert approved.status is ForecastStatus.APPROVED
    assert service.get_approved_forecast(project.id).id == approved.id
    assert service.list_lines(approved.id)[0].amount == Decimal("125.3750")


def test_forecast_generation_mode_rejects_wrong_line_kind(services) -> None:
    project = _project(services, "Automatic Forecast")
    code = _cost_code(services, "FC-AUTO")
    service = services["forecast_version_service"]
    forecast = service.create_forecast(
        project.id,
        name="Automatic",
        as_of_date=date(2026, 8, 11),
        generation_mode=ForecastGenerationMode.AUTOMATIC,
        created_by="admin",
    )

    with pytest.raises(BusinessRuleError) as exc:
        _manual_line(services, forecast, code)
    assert exc.value.code == "PROJECT_FORECAST_GENERATION_MODE_MISMATCH"


def test_approving_successor_supersedes_previous_forecast(services) -> None:
    project = _project(services, "Forecast Revisions")
    code = _cost_code(services, "FC-REV")
    service = services["forecast_version_service"]

    first = service.create_forecast(
        project.id,
        name="v1",
        as_of_date=date(2026, 7, 31),
        generation_mode=ForecastGenerationMode.MANUAL,
        created_by="admin",
    )
    _manual_line(services, first, code, "100")
    first = service.get_forecast(first.id)
    first = service.submit_forecast(
        first.id, submitted_by="admin", expected_version=first.row_version
    )
    service.approve_forecast(
        first.id, approved_by="admin", expected_version=first.row_version
    )

    second = service.create_forecast(
        project.id,
        name="v2",
        as_of_date=date(2026, 8, 11),
        generation_mode=ForecastGenerationMode.MANUAL,
        created_by="admin",
    )
    assert second.revision == 2
    _manual_line(services, second, code, "120")
    second = service.get_forecast(second.id)
    second = service.submit_forecast(
        second.id, submitted_by="admin", expected_version=second.row_version
    )
    service.approve_forecast(
        second.id, approved_by="admin", expected_version=second.row_version
    )

    assert service.get_forecast(first.id).status is ForecastStatus.SUPERSEDED
    assert service.get_approved_forecast(project.id).id == second.id


def test_forecast_repository_is_isolated_by_active_organization(services) -> None:
    project = _project(services, "Forecast Isolation")
    service = services["forecast_version_service"]
    forecast = service.create_forecast(
        project.id,
        name="Scoped",
        as_of_date=date(2026, 8, 11),
        generation_mode=ForecastGenerationMode.MANUAL,
        created_by="admin",
    )
    organization_service = services["organization_service"]
    original = organization_service.get_active_organization()
    other = organization_service.create_organization(
        organization_code="PF-FORECAST-ISOLATION",
        display_name="Forecast Isolation Organization",
        timezone_name="UTC",
        base_currency="USD",
        is_enabled=False,
    )
    organization_service.enable_organization(other.id)
    services["tenant_context_service"].set_active_organization(other.id)
    try:
        assert service._forecast_repo.get(forecast.id) is None
        assert service._forecast_repo.list_for_project(project.id) == []
    finally:
        organization_service.enable_organization(original.id)
        services["tenant_context_service"].set_active_organization(original.id)

    assert service._forecast_repo.get(forecast.id).id == forecast.id


def test_generator_nets_actual_adjustments_and_does_not_double_count_commitments(
    services, monkeypatch
) -> None:
    project = _project(services, "Automatic ETC")
    code = _cost_code(services, "FC-GEN")
    service = services["forecast_generation_service"]
    _wire_generation_sources(
        monkeypatch,
        service,
        project=project,
        cost_code=code,
        planned_amount="100",
        actual_amounts=("20", "-5"),
        commitment_amount="50",
        matched_amount="20",
    )

    result = service.generate_draft(
        project.id,
        name="Generated ETC",
        as_of_date=service._clock.today(),
        generated_by="admin",
    )

    assert result.posted_actual_offset == Decimal("15")
    assert result.open_commitment_total == Decimal("30")
    assert result.remaining_plan_total == Decimal("55")
    assert result.etc_total == Decimal("85")
    assert sorted(line.amount for line in result.lines) == [Decimal("30"), Decimal("55")]
    assert {
        decision.reason for decision in result.decisions
    } >= {
        ForecastDecisionReason.ACTUAL_CREDIT,
        ForecastDecisionReason.OPEN_COMMITMENT,
        ForecastDecisionReason.POSTED_ACTUAL_OFFSET,
        ForecastDecisionReason.REMAINING_PLAN,
    }
    assert len(
        services["forecast_version_service"].list_source_decisions(result.forecast.id)
    ) == 4


def test_manual_etc_replaces_remaining_plan_but_keeps_open_commitments(
    services, monkeypatch
) -> None:
    project = _project(services, "Hybrid ETC")
    code = _cost_code(services, "FC-HYBRID")
    service = services["forecast_generation_service"]
    _wire_generation_sources(
        monkeypatch,
        service,
        project=project,
        cost_code=code,
        planned_amount="100",
        actual_amounts=("20",),
        commitment_amount="30",
    )

    result = service.generate_draft(
        project.id,
        name="Hybrid ETC",
        as_of_date=service._clock.today(),
        generated_by="admin",
        manual_estimates=(
            ManualEtcEstimate(
                cost_code_id=code.id,
                amount=Decimal("40"),
                description="Delivery team ETC",
            ),
        ),
    )

    assert result.remaining_plan_total == Decimal("0")
    assert result.open_commitment_total == Decimal("30")
    assert result.manual_etc_total == Decimal("40")
    assert result.etc_total == Decimal("70")
    assert sorted(line.amount for line in result.lines) == [Decimal("30"), Decimal("40")]


def test_generator_persists_evidence_backed_zero_etc_forecast(
    services, monkeypatch
) -> None:
    project = _project(services, "Complete ETC")
    code = _cost_code(services, "FC-ZERO")
    service = services["forecast_generation_service"]
    _wire_generation_sources(
        monkeypatch,
        service,
        project=project,
        cost_code=code,
        planned_amount="25",
        actual_amounts=("25",),
    )

    result = service.generate_draft(
        project.id,
        name="Complete ETC",
        as_of_date=service._clock.today(),
        generated_by="admin",
    )

    assert result.etc_total == Decimal("0")
    assert result.lines == ()
    assert result.decisions
    submitted = services["forecast_version_service"].submit_forecast(
        result.forecast.id,
        submitted_by="admin",
        expected_version=result.forecast.row_version,
    )
    assert submitted.status is ForecastStatus.SUBMITTED


def test_explicit_active_risk_contingency_is_additive(services, monkeypatch) -> None:
    project = _project(services, "Risk ETC")
    code = _cost_code(services, "FC-RISK")
    service = services["forecast_generation_service"]
    _wire_generation_sources(
        monkeypatch,
        service,
        project=project,
        cost_code=code,
        planned_amount=None,
    )
    risk = RegisterEntry.create(
        project.id,
        entry_type=RegisterEntryType.RISK,
        title="Supplier delay",
    )
    monkeypatch.setattr(
        service._register_repo,
        "get",
        lambda risk_id: risk if risk_id == risk.id else None,
    )

    result = service.generate_draft(
        project.id,
        name="Risk ETC",
        as_of_date=service._clock.today(),
        generated_by="admin",
        risk_contingencies=(
            RiskContingencyEstimate(
                risk_id=risk.id,
                cost_code_id=code.id,
                amount=Decimal("15"),
            ),
        ),
    )

    assert result.risk_contingency_total == Decimal("15")
    assert result.etc_total == Decimal("15")
    assert result.lines[0].source_type is ForecastLineSourceType.RISK
    assert result.lines[0].source_reference_id == risk.id


def test_generator_rolls_back_root_lines_and_decisions_when_audit_fails(
    services, monkeypatch
) -> None:
    project = _project(services, "Atomic ETC")
    code = _cost_code(services, "FC-ATOMIC")
    service = services["forecast_generation_service"]
    _wire_generation_sources(
        monkeypatch,
        service,
        project=project,
        cost_code=code,
        planned_amount="25",
    )
    monkeypatch.setattr(
        service,
        "_record_audit",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("audit unavailable")),
    )

    with pytest.raises(RuntimeError, match="audit unavailable"):
        service.generate_draft(
            project.id,
            name="Atomic ETC",
            as_of_date=service._clock.today(),
            generated_by="admin",
        )

    assert services["forecast_version_service"].list_forecasts(project.id) == []


def test_forecast_migration_is_reversible_and_installs_constraints(tmp_path) -> None:
    database_path = tmp_path / "project-forecast-migration.db"
    config = Config("src/infra/persistence/migrations/alembic.ini")
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path.as_posix()}")
    command.upgrade(config, "head")
    engine = sa.create_engine(config.get_main_option("sqlalchemy.url"), future=True)
    inspector = sa.inspect(engine)

    assert {
        "project_finance_forecasts",
        "project_finance_forecast_lines",
        "project_finance_forecast_source_decisions",
    } <= set(inspector.get_table_names())
    forecast_indexes = {
        row["name"] for row in inspector.get_indexes("project_finance_forecasts")
    }
    line_checks = {
        row["name"]: row["sqltext"] for row in inspector.get_check_constraints(
            "project_finance_forecast_lines"
        )
    }
    decision_checks = {
        row["name"] for row in inspector.get_check_constraints(
            "project_finance_forecast_source_decisions"
        )
    }
    assert "uq_pf_forecasts_one_open_per_project" in forecast_indexes
    assert "uq_pf_forecasts_one_approved_per_project" in forecast_indexes
    assert "ck_pf_forecast_lines_source_metadata" in line_checks
    assert "'risk'" in line_checks["ck_pf_forecast_lines_source_metadata"]
    assert "'financial_change'" in line_checks[
        "ck_pf_forecast_lines_source_metadata"
    ]
    assert "ck_pf_forecast_decisions_reconciled" in decision_checks
    engine.dispose()

    command.downgrade(config, "base")
    engine = sa.create_engine(config.get_main_option("sqlalchemy.url"), future=True)
    tables = set(sa.inspect(engine).get_table_names())
    assert "project_finance_forecasts" not in tables
    assert "project_finance_forecast_lines" not in tables
    assert "project_finance_forecast_source_decisions" not in tables
    engine.dispose()

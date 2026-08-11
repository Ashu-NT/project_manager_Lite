from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config

from src.core.modules.project_management.domain.financials.forecast import (
    ForecastGenerationMode,
    ForecastLine,
    ForecastLineSourceKind,
    ForecastLineSourceType,
    ForecastStatus,
    ProjectForecast,
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
        is_active=False,
    )
    organization_service.set_active_organization(other.id)
    try:
        assert service._forecast_repo.get(forecast.id) is None
        assert service._forecast_repo.list_for_project(project.id) == []
    finally:
        organization_service.set_active_organization(original.id)

    assert service._forecast_repo.get(forecast.id).id == forecast.id


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
    } <= set(inspector.get_table_names())
    forecast_indexes = {
        row["name"] for row in inspector.get_indexes("project_finance_forecasts")
    }
    line_checks = {
        row["name"] for row in inspector.get_check_constraints(
            "project_finance_forecast_lines"
        )
    }
    assert "uq_pf_forecasts_one_open_per_project" in forecast_indexes
    assert "uq_pf_forecasts_one_approved_per_project" in forecast_indexes
    assert "ck_pf_forecast_lines_source_metadata" in line_checks
    engine.dispose()

    command.downgrade(config, "u8v9w0x1y2z3")
    engine = sa.create_engine(config.get_main_option("sqlalchemy.url"), future=True)
    tables = set(sa.inspect(engine).get_table_names())
    assert "project_finance_forecasts" not in tables
    assert "project_finance_forecast_lines" not in tables
    engine.dispose()

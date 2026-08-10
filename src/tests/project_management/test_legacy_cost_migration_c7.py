from __future__ import annotations

from datetime import date

import sqlalchemy as sa
import pytest
from alembic import command
from alembic.config import Config

from src.core.modules.project_management.domain.financials.legacy_migration import (
    LegacyCostMigrationItemStatus,
    LegacyCostMigrationPurpose,
)
from src.core.platform.common.exceptions import BusinessRuleError


def _project_with_default_cost_code(services):
    organization = services["organization_service"].get_active_organization()
    project = services["project_service"].create_project(
        "Legacy C7 migration",
        currency=organization.base_currency,
    )
    cost_code = services["financial_configuration_service"].create_cost_code(
        code="LEGACY-DEFAULT",
        name="Legacy migration default",
    )
    profile = services["financial_configuration_service"].get_profile(project.id)
    services["financial_configuration_service"].configure_profile(
        project.id,
        expected_version=profile.version,
        default_cost_code_id=cost_code.id,
    )
    return project, cost_code


def test_c7_dry_run_then_execute_is_restart_safe_and_reconciled(services) -> None:
    project, cost_code = _project_with_default_cost_code(services)
    source = services["cost_service"].add_cost_item(
        project.id,
        "Legacy mixed responsibility",
        planned_amount=100.0,
        committed_amount=80.0,
        actual_amount=25.5,
        incurred_date=date(2026, 1, 12),
        currency_code="EUR",
    )
    service = services["legacy_cost_migration_service"]

    dry_run = service.run_project(
        project.id,
        execute=False,
        fallback_transaction_date=date(2026, 1, 31),
    )
    assert dry_run.source_row_count == 1
    assert dry_run.migrated_count == 0
    assert dry_run.eligible_count == 1
    assert dry_run.deferred_count == 2
    entries, total = services["cost_entry_service"].list_for_project(project.id)
    assert entries == []
    assert total == 0

    executed = service.run_project(
        project.id,
        execute=True,
        fallback_transaction_date=date(2026, 1, 31),
    )
    assert executed.migrated_count == 1
    assert executed.deferred_count == 2
    entries, total = services["cost_entry_service"].list_for_project(project.id)
    assert total == 1
    assert entries[0].source_id == source.id
    assert entries[0].source_line_id == "actual"
    assert entries[0].cost_code_id == cost_code.id
    assert entries[0].status.value == "draft"

    replay = service.run_project(
        project.id,
        execute=True,
        fallback_transaction_date=date(2026, 1, 31),
    )
    assert replay.migrated_count == 1
    _entries, replay_total = services["cost_entry_service"].list_for_project(project.id)
    assert replay_total == 1

    reconciliation = service.reconciliation(project.id)
    by_purpose = {item.purpose: item for item in reconciliation}
    assert by_purpose[LegacyCostMigrationPurpose.ACTUAL].status == LegacyCostMigrationItemStatus.MIGRATED
    assert by_purpose[LegacyCostMigrationPurpose.ACTUAL].target_id == entries[0].id
    assert by_purpose[LegacyCostMigrationPurpose.PLANNED].reason_code == "LEGACY_PLANNED_SOURCE_VARIANT_PENDING"
    assert by_purpose[LegacyCostMigrationPurpose.COMMITMENT].reason_code == "LEGACY_COMMITMENT_SOURCE_VARIANT_PENDING"


def test_c7_actual_without_default_cost_code_is_quarantined(services) -> None:
    project = services["project_service"].create_project("Legacy quarantine", currency="EUR")
    services["cost_service"].add_cost_item(
        project.id,
        "Unmapped actual",
        planned_amount=0,
        actual_amount=10,
        currency_code="EUR",
    )

    result = services["legacy_cost_migration_service"].run_project(
        project.id,
        execute=True,
        fallback_transaction_date=date(2026, 1, 31),
    )

    assert result.status == "completed_with_quarantine"
    assert result.quarantined_count == 1
    assert result.items[0].reason_code == "LEGACY_DEFAULT_COST_CODE_REQUIRED"
    _entries, total = services["cost_entry_service"].list_for_project(project.id)
    assert total == 0


def test_c7_migration_isolated_by_active_organization(services) -> None:
    project, _cost_code = _project_with_default_cost_code(services)
    services["cost_service"].add_cost_item(
        project.id,
        "Scoped actual",
        planned_amount=0,
        actual_amount=15,
        currency_code="EUR",
    )
    migration_service = services["legacy_cost_migration_service"]
    migration_service.run_project(
        project.id,
        execute=False,
        fallback_transaction_date=date(2026, 1, 31),
    )

    organization_service = services["organization_service"]
    original = organization_service.get_active_organization()
    other = organization_service.create_organization(
        organization_code="LEGC7B",
        display_name="Second legacy migration organization",
        timezone_name="UTC",
        base_currency="EUR",
        is_active=True,
    )
    organization_service.set_active_organization(other.id)
    try:
        assert migration_service.reconciliation(project.id) == ()
        with pytest.raises(BusinessRuleError, match="Project not found"):
            migration_service.run_project(
                project.id,
                execute=True,
                fallback_transaction_date=date(2026, 1, 31),
            )
    finally:
        organization_service.set_active_organization(original.id)

    assert migration_service.reconciliation(project.id)


def test_c7_migration_schema_is_reversible_and_single_headed(tmp_path) -> None:
    database_path = tmp_path / "legacy-cost-c7.db"
    config = Config("src/infra/persistence/migrations/alembic.ini")
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path.as_posix()}")
    command.upgrade(config, "head")
    engine = sa.create_engine(config.get_main_option("sqlalchemy.url"), future=True)
    with engine.begin() as connection:
        tables = set(sa.inspect(connection).get_table_names())
    assert "project_finance_legacy_migration_runs" in tables
    assert "project_finance_legacy_migration_items" in tables
    engine.dispose()

    command.downgrade(config, "s6t7u8v9w0x1")
    engine = sa.create_engine(config.get_main_option("sqlalchemy.url"), future=True)
    with engine.begin() as connection:
        tables = set(sa.inspect(connection).get_table_names())
    assert "project_finance_legacy_migration_runs" not in tables
    assert "project_finance_legacy_migration_items" not in tables
    assert "project_approved_time_labor_postings" in tables
    engine.dispose()

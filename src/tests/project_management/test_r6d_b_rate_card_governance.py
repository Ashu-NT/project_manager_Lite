from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config

from src.core.modules.project_management.api.desktop.financials.commands.rates import (
    FinancialAddRateLineCommand,
    FinancialCreateRateCardCommand,
)
from src.core.modules.project_management.domain.financials.rate_cards import RateType
from src.core.platform.common.exceptions import BusinessRuleError, ConcurrencyError
from src.ui_qml.modules.project_management.presenters.financials.command_handler import (
    add_rate_line,
    create_rate_card,
)


ROOT = Path(__file__).resolve().parents[2]


def _project_resource(services):
    project = services["project_service"].create_project(
        "R6D-B governed rates", financial_currency_code="XAF"
    )
    resource = services["resource_service"].create_resource(
        "R6D-B resource", role="engineer", hourly_rate=Decimal("999")
    )
    return project, resource


def test_rate_card_and_line_edits_require_current_versions(services):
    project, resource = _project_resource(services)
    service = services["rate_card_service"]
    card = service.create_rate_card(name="Initial rates", project_id=project.id)

    updated_card = service.update_rate_card(
        card.id, expected_version=card.version, name="Current rates"
    )
    assert updated_card.name == "Current rates"
    assert updated_card.version == 2
    with pytest.raises(ConcurrencyError):
        service.update_rate_card(card.id, expected_version=1, name="Stale rates")

    line = service.create_line(
        card.id,
        expected_card_version=updated_card.version,
        rate_type=RateType.COST,
        unit="HOUR",
        rate_amount=Decimal("125.50"),
        rate_currency="XAF",
        resource_id=resource.id,
    )
    updated_line = service.update_line(
        line.id,
        expected_version=line.version,
        expected_card_version=updated_card.version,
        rate_amount=Decimal("130.75"),
    )
    assert updated_line.rate_amount == Decimal("130.75")
    assert updated_line.version == 2
    with pytest.raises(ConcurrencyError):
        service.update_line(
            line.id,
            expected_version=1,
            expected_card_version=updated_card.version,
            rate_amount=Decimal("140"),
        )


def test_consumed_rate_line_blocks_rewrite_but_allows_future_end_date(
    services, monkeypatch
):
    project, resource = _project_resource(services)
    service = services["rate_card_service"]
    card = service.create_rate_card(name="Historical rates", project_id=project.id)
    line = service.create_line(
        card.id,
        rate_type=RateType.COST,
        unit="HOUR",
        rate_amount=Decimal("80"),
        rate_currency="XAF",
        resource_id=resource.id,
    )
    monkeypatch.setattr(
        type(service._rate_card_repo),
        "is_line_consumed",
        lambda _repo, _id: True,
    )

    with pytest.raises(BusinessRuleError) as exc:
        service.update_line(
            line.id, expected_version=line.version, rate_amount=Decimal("81")
        )
    assert exc.value.code == "RATE_CARD_LINE_HISTORICAL_IMMUTABLE"

    ended = service.update_line(
        line.id,
        expected_version=line.version,
        effective_to=date.today() + timedelta(days=30),
    )
    assert ended.effective_to == date.today() + timedelta(days=30)


def test_resolution_snapshot_captures_line_version_and_modifier(services):
    project, resource = _project_resource(services)
    service = services["rate_card_service"]
    card = service.create_rate_card(name="Snapshot rates", project_id=project.id)
    line = service.create_line(
        card.id,
        rate_type=RateType.COST,
        unit="HOUR",
        rate_amount=Decimal("100"),
        rate_currency="XAF",
        resource_id=resource.id,
        overtime_multiplier=Decimal("1.5"),
    )
    scope = services["tenant_context_service"].require_active_scope_ids(
        operation_label="test R6D-B snapshot"
    )
    snapshot = services["rate_card_resolver"].resolve(
        tenant_id=scope.tenant_id,
        organization_id=scope.organization_id,
        project_id=project.id,
        resource_id=resource.id,
        rate_type=RateType.COST,
        as_of=date.today(),
        unit="HOUR",
        modifier="overtime",
    )
    assert snapshot.rate_line_id == line.id
    assert snapshot.rate_line_version == line.version
    assert snapshot.modifiers_applied == {"overtime": Decimal("1.5")}


def test_rate_workspace_capabilities_and_consumed_state_are_server_owned(services):
    project, resource = _project_resource(services)
    service = services["rate_card_service"]
    card = service.create_rate_card(name="Capability rates", project_id=project.id)
    line = service.create_line(
        card.id,
        rate_type=RateType.COST,
        unit="HOUR",
        rate_amount=Decimal("50"),
        rate_currency="XAF",
        resource_id=resource.id,
    )
    workspace = services["finance_workspace_query"].get_rate_workspace(
        project.id, selected_rate_card_id=card.id
    )
    assert workspace.can_create_rate_card is True
    assert workspace.selected_rate_card is not None
    assert workspace.selected_rate_card.can_edit is True
    assert workspace.lines.items[0].id == line.id
    assert workspace.lines.items[0].can_edit is True
    assert workspace.lines.items[0].is_consumed is False


def test_qml_command_adapter_builds_typed_decimal_string_commands():
    class Api:
        card_command = None
        line_command = None

        def create_rate_card(self, command):
            self.card_command = command

        def add_rate_line(self, command):
            self.line_command = command

    api = Api()
    create_rate_card(
        api, {"projectId": "project-1", "scope": "project", "name": "Rates"}
    )
    add_rate_line(
        api,
        {
            "rateCardId": "card-1",
            "cardVersion": 3,
            "rateType": "cost",
            "unit": "HOUR",
            "amount": "125.5000",
            "currency": "xaf",
            "role": "engineer",
        },
    )
    assert isinstance(api.card_command, FinancialCreateRateCardCommand)
    assert isinstance(api.line_command, FinancialAddRateLineCommand)
    assert api.line_command.rate_amount == "125.5000"
    assert api.line_command.rate_currency == "XAF"


def test_rate_architecture_guards_are_forward_only():
    service = (ROOT / "core/modules/project_management/application/financials/rate_cards/rate_card_service.py").read_text(encoding="utf-8")
    repository = (ROOT / "core/modules/project_management/infrastructure/persistence/repositories/finance/rate_cards/rate_cards.py").read_text(encoding="utf-8")
    resolver = (ROOT / "core/modules/project_management/application/financials/rate_cards/rate_card_resolver.py").read_text(encoding="utf-8")
    controller = (ROOT / "ui_qml/modules/project_management/controllers/financials/financials_workspace_controller.py").read_text(encoding="utf-8")
    assert ".commit(" not in service
    assert ".rollback(" not in service
    assert "lock_line_overlap_scope" in service
    assert ".commit(" not in repository
    assert "hourly_rate" not in resolver
    assert "cost_entries_changed" not in controller
    assert controller.count("def createRateCard") == 1
    assert controller.count("def addRateLine") == 1


def test_rate_provenance_migration_is_truthful_and_reversible():
    migration = (ROOT / "infra/persistence/migrations/versions/e9f2a5b8c4d1_add_rate_selection_provenance.py").read_text(encoding="utf-8")
    assert migration.count('add_column(sa.Column("rate_line_version"') == 1
    assert "for table, constraint_prefix in _TABLES.items()" in migration
    assert "nullable=True" in migration
    assert "drop_column(\"rate_line_version\")" in migration
    assert "UPDATE project_" not in migration


def test_rate_provenance_migration_upgrades_and_downgrades_fresh_schema(tmp_path):
    database_path = tmp_path / "r6d_b_rate_provenance.db"
    config = Config(str(ROOT / "infra/persistence/migrations/alembic.ini"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path.as_posix()}")
    command.upgrade(config, "head")

    engine = sa.create_engine(f"sqlite:///{database_path.as_posix()}")
    inspector = sa.inspect(engine)
    for table in (
        "project_approved_time_labor_postings",
        "project_finance_planned_cost_lines",
        "project_billing_preparation_lines",
    ):
        columns = {column["name"] for column in inspector.get_columns(table)}
        assert {"rate_line_version", "rate_modifier", "rate_modifier_multiplier"} <= columns
    engine.dispose()

    command.downgrade(config, "d8e1f4a7b2c3")
    engine = sa.create_engine(f"sqlite:///{database_path.as_posix()}")
    inspector = sa.inspect(engine)
    for table in (
        "project_approved_time_labor_postings",
        "project_finance_planned_cost_lines",
        "project_billing_preparation_lines",
    ):
        columns = {column["name"] for column in inspector.get_columns(table)}
        assert "rate_line_version" not in columns
    engine.dispose()

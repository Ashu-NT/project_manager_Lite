from __future__ import annotations
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

import sqlalchemy as sa
from alembic import command
from alembic.config import Config

from src.core.modules.project_management.gateway.billing.accounting_billing import (
    BillingPreparationLinePayload,
    ProjectBillingPreparationPayload,
)
from src.core.modules.project_management.api.desktop.financials.api import (
    ProjectManagementFinancialsDesktopApi,
)
from src.core.modules.project_management.domain.financials.billing_preparation import (
    BillableSourceType,
    BillingPreparationStatus,
    BillingSourceLockStatus,
    ProjectBillingPreparation,
    ProjectBillingPreparationLine,
    ProjectBillingSourceLock,
)
from src.core.modules.project_management.domain.financials.billing_profile import (
    BillingProfileStatus,
    BillingScheduleLineStatus,
    ProjectBillingProfile,
    ProjectBillingScheduleLine,
)
from src.core.modules.project_management.domain.financials.configuration import BillingMethod
from src.infra.persistence.orm import Base


NOW = datetime(2026, 8, 11, 10, tzinfo=timezone.utc)
HASH = "a" * 64


def test_billing_profile_and_schedule_use_governed_lifecycles() -> None:
    profile = ProjectBillingProfile.create(
        tenant_id="tenant-1",
        organization_id="org-1",
        project_id="project-1",
        currency_code="EUR",
        contract_reference="CONTRACT-42",
        contract_value=Decimal("120000"),
        customer_party_id="party-1",
        created_by="user-1",
        created_at=NOW,
    )
    profile.activate(actor_id="user-2", occurred_at=NOW)
    line = ProjectBillingScheduleLine.create(
        tenant_id=profile.tenant_id,
        organization_id=profile.organization_id,
        project_id=profile.project_id,
        billing_profile_id=profile.id,
        name="Design acceptance",
        amount=Decimal("24000"),
        currency_code=profile.currency_code,
        due_date=date(2026, 9, 30),
        created_by="user-1",
        created_at=NOW,
    )
    line.mark_ready(actor_id="user-2", occurred_at=NOW)

    assert profile.status is BillingProfileStatus.ACTIVE
    assert line.status is BillingScheduleLineStatus.READY


def test_preparation_snapshots_and_finalizes_a_billable_source() -> None:
    preparation = ProjectBillingPreparation.create(
        tenant_id="tenant-1",
        organization_id="org-1",
        project_id="project-1",
        billing_profile_id="profile-1",
        preparation_number="BP-2026-0001",
        billing_method=BillingMethod.FIXED_PRICE,
        period_start=date(2026, 8, 1),
        period_end=date(2026, 8, 31),
        currency_code="EUR",
        idempotency_key="billing-run-2026-08",
        created_by="user-1",
        created_at=NOW,
    )
    line = ProjectBillingPreparationLine.create(
        tenant_id=preparation.tenant_id,
        organization_id=preparation.organization_id,
        project_id=preparation.project_id,
        preparation_id=preparation.id,
        source_type=BillableSourceType.SCHEDULE_LINE,
        source_id="schedule-1",
        source_revision="3",
        source_content_hash=HASH,
        description="Design acceptance",
        source_date=date(2026, 8, 20),
        quantity=Decimal("1"),
        unit="MILESTONE",
        unit_rate=Decimal("24000"),
        net_amount=Decimal("24000"),
        currency_code="EUR",
        created_at=NOW,
    )
    lock = ProjectBillingSourceLock.create(
        tenant_id=line.tenant_id,
        organization_id=line.organization_id,
        project_id=line.project_id,
        source_type=line.source_type,
        source_id=line.source_id,
        source_revision=line.source_revision,
        source_content_hash=line.source_content_hash,
        preparation_id=preparation.id,
        preparation_line_id=line.id,
        reserved_at=NOW,
    )
    preparation.replace_totals(line_count=1, total_amount=line.net_amount, occurred_at=NOW)
    preparation.submit(submitted_by="user-1", submitted_at=NOW, approval_request_id="approval-1")
    preparation.approve(approved_by="user-2", approved_at=NOW)
    lock.finalize(occurred_at=NOW)

    assert preparation.status is BillingPreparationStatus.APPROVED
    assert lock.status is BillingSourceLockStatus.FINALIZED


def test_accounting_contract_is_decimal_text_and_preparation_only() -> None:
    line = BillingPreparationLinePayload(
        line_id="line-1",
        source_type="schedule_line",
        source_id="schedule-1",
        source_revision="3",
        source_content_hash=HASH,
        description="Design acceptance",
        source_date=date(2026, 8, 20),
        quantity="1.000000",
        unit="MILESTONE",
        unit_rate="24000.000000",
        net_amount="24000.0000",
        currency_code="EUR",
    )
    payload = ProjectBillingPreparationPayload(
        schema_name="project_billing_preparation.v1",
        message_id="project-billing-preparation:prep-1",
        tenant_id="tenant-1",
        organization_id="org-1",
        project_id="project-1",
        preparation_id="prep-1",
        preparation_number="BP-2026-0001",
        billing_method="fixed_price",
        period_start=date(2026, 8, 1),
        period_end=date(2026, 8, 31),
        currency_code="EUR",
        customer_party_id="party-1",
        contract_reference="CONTRACT-42",
        external_customer_reference=None,
        purchase_order_reference=None,
        payment_terms_days=30,
        total_amount="24000.0000",
        approved_by="user-2",
        approved_at=NOW,
        lines=(line,),
    )

    assert payload.schema_name == "project_billing_preparation.v1"
    assert payload.total_amount == "24000.0000"
    assert not hasattr(payload, "invoice_number")
    assert not hasattr(payload, "payment_status")


def test_pm_schema_does_not_manufacture_accounting_truth() -> None:
    pm_billing_tables = {name for name in Base.metadata.tables if name.startswith("project_billing_")}
    forbidden_tokens = ("invoice", "receivable", "payment", "tax", "general_ledger")

    assert pm_billing_tables
    assert not any(token in table for token in forbidden_tokens for table in pm_billing_tables)

    service_source = Path(
        "src/core/modules/project_management/application/financials/invoicing/preparation_service.py"
    ).read_text(encoding="utf-8")
    assert "def issue_invoice" not in service_source
    assert "def create_receivable" not in service_source
    assert "def post_payment" not in service_source


def test_fresh_baseline_project_billing_schema_round_trips(tmp_path) -> None:
    database_path = tmp_path / "project-billing.db"
    config = Config("src/infra/persistence/migrations/alembic.ini")
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path.as_posix()}")

    command.upgrade(config, "head")
    engine = sa.create_engine(config.get_main_option("sqlalchemy.url"), future=True)
    assert {
        "project_billing_profiles",
        "project_billing_preparations",
        "project_billing_preparation_lines",
    } <= set(sa.inspect(engine).get_table_names())
    engine.dispose()

    command.downgrade(config, "base")
    engine = sa.create_engine(config.get_main_option("sqlalchemy.url"), future=True)
    assert "project_billing_profiles" not in sa.inspect(engine).get_table_names()
    engine.dispose()

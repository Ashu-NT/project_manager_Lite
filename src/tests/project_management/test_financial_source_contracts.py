from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from src.core.modules.project_management.contracts.financial_sources import (
    ApprovedTimeFinancialSource,
    FinancialPostingPurpose,
    FinancialSourceModule,
    FinancialSourcePage,
    FinancialSourceReference,
    FinancialSourceType,
    ProcurementCommitmentFinancialSource,
    ProcurementCommitmentState,
    ProcurementReceiptAccrualFinancialSource,
    financial_source_content_hash,
)
from src.core.platform.finance.money.serialization import (
    DecimalQuantityPayload,
    MonetaryRatePayload,
)


def _reference(
    *,
    source_module: FinancialSourceModule,
    source_type: FinancialSourceType,
    posting_purpose: FinancialPostingPurpose,
    source_id: str,
    source_line_id: str | None = None,
    source_revision: str = "1",
    project_id: str = "project-1",
    content_hash: str | None = None,
) -> FinancialSourceReference:
    return FinancialSourceReference(
        tenant_id="tenant-1",
        organization_id="org-1",
        project_id=project_id,
        source_module=source_module,
        source_type=source_type,
        source_id=source_id,
        source_line_id=source_line_id,
        source_revision=source_revision,
        content_hash=content_hash or financial_source_content_hash({"source": source_id}),
        posting_purpose=posting_purpose,
    )


def test_financial_source_idempotency_is_stable_and_detects_cross_project_conflicts() -> None:
    first = _reference(
        source_module=FinancialSourceModule.PLATFORM_TIME,
        source_type=FinancialSourceType.TIME_ENTRY,
        posting_purpose=FinancialPostingPurpose.LABOR_ACTUAL,
        source_id="entry-1",
    )
    conflicting_project = first.model_copy(
        update={"project_id": "project-2", "content_hash": "f" * 64}
    )
    next_revision = first.model_copy(update={"source_revision": "2"})

    assert first.idempotency_key == conflicting_project.idempotency_key
    assert first.idempotency_key != next_revision.idempotency_key
    assert first.idempotency_key.startswith("pfin:v1:")


def test_financial_source_content_hash_is_canonical() -> None:
    first = financial_source_content_hash({"b": "2.00", "a": {"value": "1.00"}})
    second = financial_source_content_hash({"a": {"value": "1.00"}, "b": "2.00"})

    assert first == second
    assert len(first) == 64


def test_financial_source_reference_rejects_invalid_semantics() -> None:
    with pytest.raises(ValidationError, match="incompatible"):
        _reference(
            source_module=FinancialSourceModule.PLATFORM_TIME,
            source_type=FinancialSourceType.TIME_ENTRY,
            posting_purpose=FinancialPostingPurpose.RECEIPT_ACCRUAL,
            source_id="entry-1",
        )

    with pytest.raises(ValidationError, match="SHA-256"):
        _reference(
            source_module=FinancialSourceModule.PLATFORM_TIME,
            source_type=FinancialSourceType.TIME_ENTRY,
            posting_purpose=FinancialPostingPurpose.LABOR_ACTUAL,
            source_id="entry-1",
            content_hash="not-a-hash",
        )

    with pytest.raises(ValidationError, match="source line ID"):
        _reference(
            source_module=FinancialSourceModule.DATA_EXCHANGE,
            source_type=FinancialSourceType.IMPORT_ROW,
            posting_purpose=FinancialPostingPurpose.LEGACY_MIGRATION,
            source_id="batch-1",
        )


@pytest.mark.parametrize(
    ("source_module", "source_type", "posting_purpose", "source_line_id"),
    [
        (
            FinancialSourceModule.PROJECT_MANAGEMENT,
            FinancialSourceType.MANUAL_COMMAND,
            FinancialPostingPurpose.MANUAL_ACTUAL,
            None,
        ),
        (
            FinancialSourceModule.DATA_EXCHANGE,
            FinancialSourceType.IMPORT_ROW,
            FinancialPostingPurpose.LEGACY_MIGRATION,
            "row-17",
        ),
    ],
)
def test_manual_and_import_source_identities_are_supported(
    source_module,
    source_type,
    posting_purpose,
    source_line_id,
) -> None:
    reference = _reference(
        source_module=source_module,
        source_type=source_type,
        posting_purpose=posting_purpose,
        source_id="command-or-batch-1",
        source_line_id=source_line_id,
    )

    assert reference.idempotency_key.startswith("pfin:v1:")


def test_approved_time_source_requires_approved_hour_snapshot() -> None:
    reference = _reference(
        source_module=FinancialSourceModule.PLATFORM_TIME,
        source_type=FinancialSourceType.TIME_ENTRY,
        posting_purpose=FinancialPostingPurpose.LABOR_ACTUAL,
        source_id="entry-1",
        source_revision="approval-3",
    )
    source = ApprovedTimeFinancialSource(
        reference=reference,
        approved_snapshot_id="snapshot-3",
        timesheet_period_id="period-1",
        time_entry_id="entry-1",
        work_allocation_id="allocation-1",
        resource_id="resource-1",
        employee_id="employee-1",
        assignment_id="assignment-1",
        task_id="task-1",
        work_date=date(2026, 8, 1),
        approved_at=datetime(
            2026,
            8,
            2,
            11,
            0,
            tzinfo=timezone(timedelta(hours=2)),
        ),
        hours=DecimalQuantityPayload(value="7.50", unit="hour"),
    )

    assert source.hours.value == "7.5"
    assert source.hours.unit == "HOUR"
    assert source.approved_at == datetime(2026, 8, 2, 9, 0, tzinfo=timezone.utc)

    with pytest.raises(ValidationError, match="positive HOUR"):
        source.model_copy(
            update={"hours": DecimalQuantityPayload(value="7.5", unit="DAY")}
        ).model_validate(
            source.model_copy(
                update={"hours": DecimalQuantityPayload(value="7.5", unit="DAY")}
            ).model_dump()
        )


def test_procurement_sources_preserve_line_identity_quantity_rate_and_state() -> None:
    commitment_reference = _reference(
        source_module=FinancialSourceModule.INVENTORY_PROCUREMENT,
        source_type=FinancialSourceType.PURCHASE_ORDER_LINE,
        posting_purpose=FinancialPostingPurpose.PURCHASE_COMMITMENT,
        source_id="po-1",
        source_line_id="po-line-1",
        source_revision="4",
    )
    commitment = ProcurementCommitmentFinancialSource(
        reference=commitment_reference,
        purchase_order_id="po-1",
        purchase_order_line_id="po-line-1",
        purchase_order_number="PO-0001",
        supplier_party_id="supplier-1",
        site_id="site-1",
        state=ProcurementCommitmentState.SENT,
        ordered_quantity=DecimalQuantityPayload(value="12.00", unit="ea"),
        unit_price=MonetaryRatePayload(amount="9.50", currency="eur", per_unit="ea"),
        order_date=date(2026, 8, 1),
    )

    receipt_reference = _reference(
        source_module=FinancialSourceModule.INVENTORY_PROCUREMENT,
        source_type=FinancialSourceType.RECEIPT_LINE,
        posting_purpose=FinancialPostingPurpose.RECEIPT_ACCRUAL,
        source_id="receipt-1",
        source_line_id="receipt-line-1",
        source_revision="posted-1",
    )
    receipt = ProcurementReceiptAccrualFinancialSource(
        reference=receipt_reference,
        receipt_id="receipt-1",
        receipt_line_id="receipt-line-1",
        receipt_number="RCV-0001",
        purchase_order_id="po-1",
        purchase_order_line_id="po-line-1",
        supplier_party_id="supplier-1",
        site_id="site-1",
        posted_at=datetime(2026, 8, 2, 10, 0, tzinfo=timezone.utc),
        accepted_quantity=DecimalQuantityPayload(value="5", unit="ea"),
        unit_cost=MonetaryRatePayload(amount="9.50", currency="eur", per_unit="ea"),
    )

    page = FinancialSourcePage[ProcurementCommitmentFinancialSource](
        items=(commitment,), next_cursor="cursor-2"
    )
    assert page.items == (commitment,)
    assert receipt.unit_cost.currency == "EUR"

    with pytest.raises(ValidationError, match="units must match"):
        ProcurementCommitmentFinancialSource(
            **commitment.model_dump(exclude={"unit_price"}),
            unit_price=MonetaryRatePayload(amount="9.50", currency="EUR", per_unit="HOUR"),
        )

from __future__ import annotations

from src.core.modules.project_management.domain.financials.commitment import (
    ProjectCommitment,
    ProjectCommitmentLine,
    ProjectCommitmentLineState,
    ProjectCommitmentMatch,
    ProjectCommitmentMatchKind,
    ProjectCommitmentSourceRevision,
)
from src.core.modules.project_management.infrastructure.persistence.orm.commitment import (
    ProjectCommitmentLineORM,
    ProjectCommitmentMatchORM,
    ProjectCommitmentORM,
    ProjectCommitmentSourceRevisionORM,
)


def commitment_to_orm(value: ProjectCommitment) -> ProjectCommitmentORM:
    return ProjectCommitmentORM(
        id=value.id,
        tenant_id=value.tenant_id,
        organization_id=value.organization_id,
        project_id=value.project_id,
        purchase_order_id=value.purchase_order_id,
        purchase_order_number=value.purchase_order_number,
        supplier_party_id=value.supplier_party_id,
        site_id=value.site_id,
        created_by=value.created_by,
        created_at=value.created_at,
    )


def commitment_from_orm(row: ProjectCommitmentORM) -> ProjectCommitment:
    return ProjectCommitment(
        id=row.id, tenant_id=row.tenant_id, organization_id=row.organization_id,
        project_id=row.project_id, purchase_order_id=row.purchase_order_id,
        purchase_order_number=row.purchase_order_number, supplier_party_id=row.supplier_party_id,
        site_id=row.site_id, created_by=row.created_by, created_at=row.created_at,
    )


def commitment_line_to_orm(value: ProjectCommitmentLine) -> ProjectCommitmentLineORM:
    return ProjectCommitmentLineORM(
        id=value.id, tenant_id=value.tenant_id, organization_id=value.organization_id,
        project_id=value.project_id, commitment_id=value.commitment_id,
        purchase_order_line_id=value.purchase_order_line_id, cost_code_id=value.cost_code_id,
        task_id=value.task_id, state=value.state.value, ordered_quantity=value.ordered_quantity,
        quantity_unit=value.quantity_unit, unit_price=value.unit_price, amount=value.amount,
        currency_code=value.currency_code, base_amount=value.base_amount,
        base_currency_code=value.base_currency_code, exchange_rate=value.exchange_rate,
        exchange_rate_date=value.exchange_rate_date,
        exchange_rate_source=value.exchange_rate_source,
        exchange_rate_captured_at=value.exchange_rate_captured_at,
        matched_amount=value.matched_amount, order_date=value.order_date,
        expected_delivery_date=value.expected_delivery_date,
        source_requisition_id=value.source_requisition_id,
        source_requisition_line_id=value.source_requisition_line_id,
        source_revision=value.source_revision, source_content_hash=value.source_content_hash,
        source_idempotency_key=value.source_idempotency_key, version=value.row_version,
        created_by=value.created_by, created_at=value.created_at,
        updated_by=value.updated_by, updated_at=value.updated_at,
    )


def commitment_line_from_orm(row: ProjectCommitmentLineORM) -> ProjectCommitmentLine:
    return ProjectCommitmentLine(
        id=row.id, tenant_id=row.tenant_id, organization_id=row.organization_id,
        project_id=row.project_id, commitment_id=row.commitment_id,
        purchase_order_line_id=row.purchase_order_line_id, cost_code_id=row.cost_code_id,
        task_id=row.task_id, state=ProjectCommitmentLineState(row.state),
        ordered_quantity=row.ordered_quantity, quantity_unit=row.quantity_unit,
        unit_price=row.unit_price, amount=row.amount, currency_code=row.currency_code,
        base_amount=row.base_amount, base_currency_code=row.base_currency_code,
        exchange_rate=row.exchange_rate, exchange_rate_date=row.exchange_rate_date,
        exchange_rate_source=row.exchange_rate_source,
        exchange_rate_captured_at=row.exchange_rate_captured_at,
        matched_amount=row.matched_amount, order_date=row.order_date,
        expected_delivery_date=row.expected_delivery_date,
        source_requisition_id=row.source_requisition_id,
        source_requisition_line_id=row.source_requisition_line_id,
        source_revision=row.source_revision, source_content_hash=row.source_content_hash,
        source_idempotency_key=row.source_idempotency_key, row_version=row.version,
        created_by=row.created_by, created_at=row.created_at,
        updated_by=row.updated_by, updated_at=row.updated_at,
    )


def commitment_revision_to_orm(
    value: ProjectCommitmentSourceRevision,
) -> ProjectCommitmentSourceRevisionORM:
    return ProjectCommitmentSourceRevisionORM(
        id=value.id,
        tenant_id=value.tenant_id,
        organization_id=value.organization_id,
        project_id=value.project_id,
        commitment_line_id=value.commitment_line_id,
        source_revision=value.source_revision,
        source_content_hash=value.source_content_hash,
        source_idempotency_key=value.source_idempotency_key,
        snapshot_json=value.snapshot_json,
        observed_at=value.observed_at,
    )


def commitment_revision_from_orm(
    row: ProjectCommitmentSourceRevisionORM,
) -> ProjectCommitmentSourceRevision:
    return ProjectCommitmentSourceRevision(
        id=row.id, tenant_id=row.tenant_id, organization_id=row.organization_id,
        project_id=row.project_id, commitment_line_id=row.commitment_line_id,
        source_revision=row.source_revision, source_content_hash=row.source_content_hash,
        source_idempotency_key=row.source_idempotency_key, snapshot_json=row.snapshot_json,
        observed_at=row.observed_at,
    )


def commitment_match_to_orm(value: ProjectCommitmentMatch) -> ProjectCommitmentMatchORM:
    return ProjectCommitmentMatchORM(
        id=value.id, tenant_id=value.tenant_id, organization_id=value.organization_id,
        project_id=value.project_id, commitment_line_id=value.commitment_line_id,
        cost_entry_id=value.cost_entry_id, kind=value.kind.value, amount=value.amount,
        currency_code=value.currency_code, idempotency_key=value.idempotency_key,
        reverses_match_id=value.reverses_match_id, created_by=value.created_by,
        created_at=value.created_at,
    )


def commitment_match_from_orm(row: ProjectCommitmentMatchORM) -> ProjectCommitmentMatch:
    return ProjectCommitmentMatch(
        id=row.id, tenant_id=row.tenant_id, organization_id=row.organization_id,
        project_id=row.project_id, commitment_line_id=row.commitment_line_id,
        cost_entry_id=row.cost_entry_id, kind=ProjectCommitmentMatchKind(row.kind),
        amount=row.amount, currency_code=row.currency_code,
        idempotency_key=row.idempotency_key, reverses_match_id=row.reverses_match_id,
        created_by=row.created_by, created_at=row.created_at,
    )


__all__ = [
    "commitment_from_orm", "commitment_line_from_orm", "commitment_line_to_orm",
    "commitment_match_from_orm", "commitment_match_to_orm", "commitment_revision_from_orm",
    "commitment_revision_to_orm", "commitment_to_orm",
]

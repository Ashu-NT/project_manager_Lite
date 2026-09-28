"""One bounded projection for a page of preparations; never materialize payloads."""

import json
from collections.abc import Sequence

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from src.core.modules.project_management.contracts.reads.financials.models.accounting_delivery import (
    AccountingDeliveryFact,
)
from src.core.modules.project_management.infrastructure.persistence.orm.accounting.handoff import (
    ProjectAccountingHandoffORM,
    ProjectAccountingOutboxORM,
)
from src.core.platform.contract.port.integration.external_accounting import (
    ExternalAccountingFailureKind,
)

from .accounting_inbound_projection import with_inbound_evidence

_SAFE_FAILURES = frozenset(item.value for item in ExternalAccountingFailureKind) | {
    "DELIVERY_ATTEMPTS_EXHAUSTED"
}


def load_accounting_deliveries(
    session: Session,
    *,
    tenant_id: str,
    organization_id: str,
    project_id: str,
    preparation_ids: Sequence[str],
) -> dict[str, AccountingDeliveryFact]:
    """The caller supplies at most one bounded page (maximum 200 preparations)."""
    if not preparation_ids:
        return {}
    if len(preparation_ids) > 200:
        raise ValueError("Accounting delivery projection exceeds the page bound.")
    handoff = ProjectAccountingHandoffORM
    outbox = ProjectAccountingOutboxORM
    ranked = (
        select(
            handoff.id,
            handoff.preparation_id,
            handoff.approved_version,
            func.row_number()
            .over(
                partition_by=handoff.preparation_id,
                order_by=(handoff.approved_version.desc(), handoff.id.asc()),
            )
            .label("rank"),
        )
        .where(
            handoff.tenant_id == tenant_id,
            handoff.organization_id == organization_id,
            handoff.project_id == project_id,
            handoff.preparation_id.in_(preparation_ids),
        )
        .subquery()
    )
    rows = session.execute(
        select(
            ranked.c.preparation_id,
            ranked.c.id,
            ranked.c.approved_version,
            outbox.created_at,
            outbox.status,
            outbox.target_adapter_id,
            outbox.target_connection_id,
            outbox.attempt_count,
            outbox.max_attempts,
            outbox.available_at,
            outbox.published_at,
            outbox.updated_at,
            outbox.last_error_code,
            outbox.transport_receipt_json,
        )
        .join(
            outbox,
            and_(
                outbox.event_id == ranked.c.id,
                outbox.tenant_id == tenant_id,
                outbox.organization_id == organization_id,
                outbox.project_id == project_id,
            ),
        )
        .where(ranked.c.rank == 1)
    ).all()
    result = {}
    for row in rows:
        receipt_reference = None
        if row.transport_receipt_json is not None:
            try:
                receipt = json.loads(row.transport_receipt_json)
                value = receipt.get("remote_reference")
                if (
                    isinstance(value, str)
                    and len(value) <= 512
                    and not any(ord(c) < 32 for c in value)
                ):
                    receipt_reference = value
            except (ValueError, TypeError, AttributeError):
                pass
        result[row.preparation_id] = AccountingDeliveryFact(
            handoff_id=row.id,
            approved_source_version=row.approved_version,
            requested_at=row.created_at,
            transport_state=row.status,
            adapter_id=row.target_adapter_id,
            connection_id=row.target_connection_id,
            attempt_count=row.attempt_count,
            max_attempts=row.max_attempts,
            next_attempt_at=row.available_at
            if row.status in {"pending", "retry"}
            else None,
            delivered_at=row.published_at,
            last_activity_at=row.updated_at,
            failure_category=row.last_error_code
            if row.last_error_code in _SAFE_FAILURES
            else ("delivery_failed" if row.last_error_code else None),
            receipt_reference=receipt_reference,
        )
    return with_inbound_evidence(
        session,
        result,
        tenant_id=tenant_id,
        organization_id=organization_id,
        project_id=project_id,
    )

"""Bounded inbox metadata; raw envelopes never cross the SQL boundary."""

from dataclasses import replace

from sqlalchemy import and_, case, cast, func, or_, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Session

from src.core.modules.project_management.contracts.reads.financials.models.accounting_delivery import (
    AccountingDeliveryFact,
)
from src.core.modules.project_management.domain.financials.accounting.outcome_policy import (
    OutcomeRejectionReason,
)
from src.core.modules.project_management.infrastructure.persistence.orm.finance_inbox import (
    ProjectFinanceInboxORM,
)
from src.core.platform.integration.accounting_events import ACCOUNTING_OUTCOME_CONSUMER

_SAFE_REASONS = frozenset(reason.value for reason in OutcomeRejectionReason) | {
    "EVENT_ID_CONTENT_CONFLICT",
    "STALE_AGGREGATE_VERSION",
    "CONFLICT",
}


def with_inbound_evidence(
    session: Session,
    deliveries: dict[str, AccountingDeliveryFact],
    *,
    tenant_id: str,
    organization_id: str,
    project_id: str,
) -> dict[str, AccountingDeliveryFact]:
    if not deliveries:
        return deliveries
    inbox = ProjectFinanceInboxORM
    postgres = session.get_bind().dialect.name == "postgresql"

    def field(*path):
        if postgres:
            return func.jsonb_extract_path_text(cast(inbox.envelope_json, JSONB), *path)
        return func.json_extract(inbox.envelope_json, "$." + ".".join(path))

    handoff_id = field("causation_id")
    conditions = [
        and_(
            handoff_id == item.handoff_id,
            field("payload", "adapter_id") == item.adapter_id,
            field("payload", "connection_id") == item.connection_id,
        )
        for item in deliveries.values()
        if item.adapter_id and item.connection_id
    ]
    if not conditions:
        return deliveries
    quarantined = inbox.status == "quarantined"
    ranked = (
        select(
            handoff_id.label("handoff_id"),
            inbox.id,
            inbox.updated_at,
            inbox.status,
            inbox.quarantine_reason_code,
            func.max(inbox.updated_at)
            .over(partition_by=handoff_id)
            .label("last_activity_at"),
            func.sum(case((quarantined, 1), else_=0))
            .over(partition_by=handoff_id)
            .label("quarantined_count"),
            func.max(
                case(
                    (
                        and_(
                            inbox.aggregate_type == "accounting_handoff_outcome",
                            inbox.processed_at.is_not(None),
                        ),
                        inbox.aggregate_version,
                    ),
                    else_=None,
                )
            )
            .over(partition_by=handoff_id)
            .label("external_sequence"),
            func.row_number()
            .over(
                partition_by=handoff_id,
                order_by=(
                    case((quarantined, 1), else_=0).desc(),
                    inbox.updated_at.desc(),
                    inbox.id.asc(),
                ),
            )
            .label("rank"),
        )
        .where(
            inbox.tenant_id == tenant_id,
            inbox.organization_id == organization_id,
            inbox.consumer_name == ACCOUNTING_OUTCOME_CONSUMER,
            or_(
                inbox.source_project_id == project_id, inbox.source_project_id.is_(None)
            ),
            or_(*conditions),
        )
        .subquery()
    )
    rows = {
        row.handoff_id: row
        for row in session.execute(select(ranked).where(ranked.c.rank == 1))
    }
    return {
        key: replace(
            item,
            quarantined_count=rows[item.handoff_id].quarantined_count,
            latest_quarantine_id=(
                rows[item.handoff_id].id
                if rows[item.handoff_id].status == "quarantined"
                else None
            ),
            latest_quarantine_at=(
                rows[item.handoff_id].updated_at
                if rows[item.handoff_id].status == "quarantined"
                else None
            ),
            latest_quarantine_reason=(
                rows[item.handoff_id].quarantine_reason_code
                if rows[item.handoff_id].quarantine_reason_code in _SAFE_REASONS
                else "invalid_inbound_evidence"
                if rows[item.handoff_id].status == "quarantined"
                else None
            ),
            last_activity_at=max(
                item.last_activity_at, rows[item.handoff_id].last_activity_at
            ),
            external_sequence=rows[item.handoff_id].external_sequence,
        )
        if item.handoff_id in rows
        else item
        for key, item in deliveries.items()
    }

from __future__ import annotations

from src.core.modules.project_management.domain.financials.billing_preparation import (
    BillableSourceType,
    BillingExternalEventType,
    BillingPreparationStatus,
    BillingSourceLockStatus,
    ProjectBillingExternalEvent,
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
from src.core.modules.project_management.infrastructure.persistence.orm.billing import (
    ProjectBillingExternalEventORM,
    ProjectBillingPreparationLineORM,
    ProjectBillingPreparationORM,
    ProjectBillingProfileORM,
    ProjectBillingScheduleLineORM,
    ProjectBillingSourceLockORM,
)


def billing_profile_to_orm(value: ProjectBillingProfile) -> ProjectBillingProfileORM:
    return ProjectBillingProfileORM(
        id=value.id,
        tenant_id=value.tenant_id,
        organization_id=value.organization_id,
        project_id=value.project_id,
        currency_code=value.currency_code,
        contract_reference=value.contract_reference,
        contract_value=value.contract_value,
        customer_party_id=value.customer_party_id,
        external_customer_reference=value.external_customer_reference,
        purchase_order_reference=value.purchase_order_reference,
        cost_plus_markup_percent=value.cost_plus_markup_percent,
        payment_terms_days=value.payment_terms_days,
        retention_years=value.retention_years,
        legal_hold=value.legal_hold,
        status=value.status.value,
        version=value.row_version,
        created_by=value.created_by,
        created_at=value.created_at,
        updated_by=value.updated_by,
        updated_at=value.updated_at,
    )


def billing_profile_from_orm(row: ProjectBillingProfileORM) -> ProjectBillingProfile:
    return ProjectBillingProfile(
        id=row.id,
        tenant_id=row.tenant_id,
        organization_id=row.organization_id,
        project_id=row.project_id,
        currency_code=row.currency_code,
        contract_reference=row.contract_reference,
        contract_value=row.contract_value,
        customer_party_id=row.customer_party_id,
        external_customer_reference=row.external_customer_reference,
        purchase_order_reference=row.purchase_order_reference,
        cost_plus_markup_percent=row.cost_plus_markup_percent,
        payment_terms_days=row.payment_terms_days,
        retention_years=row.retention_years,
        legal_hold=row.legal_hold,
        status=BillingProfileStatus(row.status),
        row_version=row.version,
        created_by=row.created_by,
        created_at=row.created_at,
        updated_by=row.updated_by,
        updated_at=row.updated_at,
    )


def schedule_line_to_orm(value: ProjectBillingScheduleLine) -> ProjectBillingScheduleLineORM:
    return ProjectBillingScheduleLineORM(
        id=value.id,
        tenant_id=value.tenant_id,
        organization_id=value.organization_id,
        project_id=value.project_id,
        billing_profile_id=value.billing_profile_id,
        name=value.name,
        amount=value.amount,
        currency_code=value.currency_code,
        due_date=value.due_date,
        task_id=value.task_id,
        acceptance_reference=value.acceptance_reference,
        status=value.status.value,
        version=value.row_version,
        created_by=value.created_by,
        created_at=value.created_at,
        updated_by=value.updated_by,
        updated_at=value.updated_at,
    )


def schedule_line_from_orm(row: ProjectBillingScheduleLineORM) -> ProjectBillingScheduleLine:
    return ProjectBillingScheduleLine(
        id=row.id,
        tenant_id=row.tenant_id,
        organization_id=row.organization_id,
        project_id=row.project_id,
        billing_profile_id=row.billing_profile_id,
        name=row.name,
        amount=row.amount,
        currency_code=row.currency_code,
        due_date=row.due_date,
        task_id=row.task_id,
        acceptance_reference=row.acceptance_reference,
        status=BillingScheduleLineStatus(row.status),
        row_version=row.version,
        created_by=row.created_by,
        created_at=row.created_at,
        updated_by=row.updated_by,
        updated_at=row.updated_at,
    )


def preparation_to_orm(value: ProjectBillingPreparation) -> ProjectBillingPreparationORM:
    return ProjectBillingPreparationORM(
        id=value.id,
        tenant_id=value.tenant_id,
        organization_id=value.organization_id,
        project_id=value.project_id,
        billing_profile_id=value.billing_profile_id,
        preparation_number=value.preparation_number,
        billing_method=value.billing_method.value,
        period_start=value.period_start,
        period_end=value.period_end,
        currency_code=value.currency_code,
        idempotency_key=value.idempotency_key,
        status=value.status.value,
        line_count=value.line_count,
        total_amount=value.total_amount,
        correction_of_preparation_id=value.correction_of_preparation_id,
        approval_request_id=value.approval_request_id,
        submitted_by=value.submitted_by,
        submitted_at=value.submitted_at,
        approved_by=value.approved_by,
        approved_at=value.approved_at,
        rejected_by=value.rejected_by,
        rejected_at=value.rejected_at,
        rejection_notes=value.rejection_notes,
        delivery_requested_at=value.delivery_requested_at,
        delivered_at=value.delivered_at,
        acknowledged_at=value.acknowledged_at,
        reconciled_at=value.reconciled_at,
        version=value.row_version,
        created_by=value.created_by,
        created_at=value.created_at,
        updated_at=value.updated_at,
    )


def preparation_from_orm(row: ProjectBillingPreparationORM) -> ProjectBillingPreparation:
    return ProjectBillingPreparation(
        id=row.id,
        tenant_id=row.tenant_id,
        organization_id=row.organization_id,
        project_id=row.project_id,
        billing_profile_id=row.billing_profile_id,
        preparation_number=row.preparation_number,
        billing_method=BillingMethod(row.billing_method),
        period_start=row.period_start,
        period_end=row.period_end,
        currency_code=row.currency_code,
        idempotency_key=row.idempotency_key,
        created_by=row.created_by,
        status=BillingPreparationStatus(row.status),
        line_count=row.line_count,
        total_amount=row.total_amount,
        correction_of_preparation_id=row.correction_of_preparation_id,
        approval_request_id=row.approval_request_id,
        submitted_by=row.submitted_by,
        submitted_at=row.submitted_at,
        approved_by=row.approved_by,
        approved_at=row.approved_at,
        rejected_by=row.rejected_by,
        rejected_at=row.rejected_at,
        rejection_notes=row.rejection_notes,
        delivery_requested_at=row.delivery_requested_at,
        delivered_at=row.delivered_at,
        acknowledged_at=row.acknowledged_at,
        reconciled_at=row.reconciled_at,
        row_version=row.version,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def preparation_line_to_orm(
    value: ProjectBillingPreparationLine,
) -> ProjectBillingPreparationLineORM:
    return ProjectBillingPreparationLineORM(
        id=value.id,
        tenant_id=value.tenant_id,
        organization_id=value.organization_id,
        project_id=value.project_id,
        preparation_id=value.preparation_id,
        source_type=value.source_type.value,
        source_id=value.source_id,
        source_revision=value.source_revision,
        source_content_hash=value.source_content_hash,
        description=value.description,
        source_date=value.source_date,
        quantity=value.quantity,
        unit=value.unit,
        unit_rate=value.unit_rate,
        net_amount=value.net_amount,
        currency_code=value.currency_code,
        task_id=value.task_id,
        resource_id=value.resource_id,
        source_amount=value.source_amount,
        markup_percent=value.markup_percent,
        rate_card_id=value.rate_card_id,
        rate_line_id=value.rate_line_id,
        rate_card_version=value.rate_card_version,
        created_at=value.created_at,
    )


def preparation_line_from_orm(
    row: ProjectBillingPreparationLineORM,
) -> ProjectBillingPreparationLine:
    return ProjectBillingPreparationLine(
        id=row.id,
        tenant_id=row.tenant_id,
        organization_id=row.organization_id,
        project_id=row.project_id,
        preparation_id=row.preparation_id,
        source_type=BillableSourceType(row.source_type),
        source_id=row.source_id,
        source_revision=row.source_revision,
        source_content_hash=row.source_content_hash,
        description=row.description,
        source_date=row.source_date,
        quantity=row.quantity,
        unit=row.unit,
        unit_rate=row.unit_rate,
        net_amount=row.net_amount,
        currency_code=row.currency_code,
        task_id=row.task_id,
        resource_id=row.resource_id,
        source_amount=row.source_amount,
        markup_percent=row.markup_percent,
        rate_card_id=row.rate_card_id,
        rate_line_id=row.rate_line_id,
        rate_card_version=row.rate_card_version,
        created_at=row.created_at,
    )


def source_lock_to_orm(value: ProjectBillingSourceLock) -> ProjectBillingSourceLockORM:
    return ProjectBillingSourceLockORM(
        id=value.id,
        tenant_id=value.tenant_id,
        organization_id=value.organization_id,
        project_id=value.project_id,
        source_type=value.source_type.value,
        source_id=value.source_id,
        source_revision=value.source_revision,
        source_content_hash=value.source_content_hash,
        preparation_id=value.preparation_id,
        preparation_line_id=value.preparation_line_id,
        status=value.status.value,
        reserved_at=value.reserved_at,
        finalized_at=value.finalized_at,
        released_at=value.released_at,
    )


def source_lock_from_orm(row: ProjectBillingSourceLockORM) -> ProjectBillingSourceLock:
    return ProjectBillingSourceLock(
        id=row.id,
        tenant_id=row.tenant_id,
        organization_id=row.organization_id,
        project_id=row.project_id,
        source_type=BillableSourceType(row.source_type),
        source_id=row.source_id,
        source_revision=row.source_revision,
        source_content_hash=row.source_content_hash,
        preparation_id=row.preparation_id,
        preparation_line_id=row.preparation_line_id,
        status=BillingSourceLockStatus(row.status),
        reserved_at=row.reserved_at,
        finalized_at=row.finalized_at,
        released_at=row.released_at,
    )


def external_event_to_orm(value: ProjectBillingExternalEvent) -> ProjectBillingExternalEventORM:
    return ProjectBillingExternalEventORM(
        id=value.id,
        tenant_id=value.tenant_id,
        organization_id=value.organization_id,
        project_id=value.project_id,
        preparation_id=value.preparation_id,
        event_type=value.event_type.value,
        external_system=value.external_system,
        external_status=value.external_status,
        idempotency_key=value.idempotency_key,
        occurred_at=value.occurred_at,
        external_invoice_reference=value.external_invoice_reference,
        reconciliation_reference=value.reconciliation_reference,
        message=value.message,
        recorded_at=value.recorded_at,
    )


def external_event_from_orm(row: ProjectBillingExternalEventORM) -> ProjectBillingExternalEvent:
    return ProjectBillingExternalEvent(
        id=row.id,
        tenant_id=row.tenant_id,
        organization_id=row.organization_id,
        project_id=row.project_id,
        preparation_id=row.preparation_id,
        event_type=BillingExternalEventType(row.event_type),
        external_system=row.external_system,
        external_status=row.external_status,
        idempotency_key=row.idempotency_key,
        occurred_at=row.occurred_at,
        external_invoice_reference=row.external_invoice_reference,
        reconciliation_reference=row.reconciliation_reference,
        message=row.message,
        recorded_at=row.recorded_at,
    )


__all__ = [
    "billing_profile_from_orm",
    "billing_profile_to_orm",
    "external_event_from_orm",
    "external_event_to_orm",
    "preparation_from_orm",
    "preparation_line_from_orm",
    "preparation_line_to_orm",
    "preparation_to_orm",
    "schedule_line_from_orm",
    "schedule_line_to_orm",
    "source_lock_from_orm",
    "source_lock_to_orm",
]

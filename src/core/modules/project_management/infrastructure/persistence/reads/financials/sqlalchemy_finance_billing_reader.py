from __future__ import annotations

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.orm import Session, aliased

from src.core.modules.project_management.contracts.reads.financials.models.finance_billing_facts import (
    AccountingStatusFact,
    AccountingStatusQuery,
    BillingPreparationDetailFact,
    BillingPreparationLineFact,
    BillingPreparationLineQuery,
    BillingPreparationQuery,
    BillingPreparationSummaryFact,
    BillingProfileFact,
    BillingScheduleFact,
    BillingScheduleQuery,
)
from src.core.modules.project_management.contracts.reads.financials.models.finance_budget_facts import (
    FinancePageFacts,
)
from src.core.modules.project_management.infrastructure.persistence.orm.billing import (
    ProjectBillingExternalEventORM,
    ProjectBillingPreparationLineORM,
    ProjectBillingPreparationORM,
    ProjectBillingProfileORM,
    ProjectBillingScheduleLineORM,
    ProjectBillingSourceLockORM,
)
from src.core.modules.project_management.infrastructure.persistence.orm.task import TaskORM
from src.core.platform.infrastructure.persistence.orm.approval.approval import ApprovalRequestORM


_SCHEDULE_STATUSES = {"planned", "ready", "billed", "cancelled"}
_PREPARATION_STATUSES = {
    "draft", "submitted", "approved", "delivery_pending", "delivered",
    "acknowledged", "reconciled", "rejected", "cancelled",
}
_BILLING_METHODS = {"time_and_materials", "fixed_price", "cost_plus"}
_SOURCE_TYPES = {"approved_time", "posted_cost", "schedule_line", "adjustment"}
_SOURCE_STATES = {"available", "reserved", "finalized", "released"}
_CORRECTION_STATES = {"original", "correction"}
_DELIVERY_STATES = {"ready", "local_requested", "external_acknowledged", "not_requested"}


class SqlAlchemyFinanceBillingReader:
    """Bounded PM commercial projections; Accounting outcomes remain read-only evidence."""

    def __init__(self, *, session: Session) -> None:
        self._session = session

    def list_accounting_statuses(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        project_id: str,
        request: AccountingStatusQuery,
    ) -> FinancePageFacts[AccountingStatusFact]:
        correction = aliased(ProjectBillingPreparationORM)
        latest = _latest_event_subquery(tenant_id, organization_id, project_id)
        conditions = [
            ProjectBillingPreparationORM.tenant_id == tenant_id,
            ProjectBillingPreparationORM.organization_id == organization_id,
            ProjectBillingPreparationORM.project_id == project_id,
        ]
        if request.search.strip():
            pattern = f"%{request.search.strip()}%"
            conditions.append(
                or_(
                    ProjectBillingPreparationORM.preparation_number.ilike(pattern),
                    correction.preparation_number.ilike(pattern),
                    latest.c.external_system.ilike(pattern),
                    latest.c.external_status.ilike(pattern),
                    latest.c.external_invoice_reference.ilike(pattern),
                    latest.c.reconciliation_reference.ilike(pattern),
                )
            )
        base = (
            select(
                ProjectBillingPreparationORM.id,
                ProjectBillingPreparationORM.preparation_number,
                ProjectBillingPreparationORM.status,
                ProjectBillingPreparationORM.correction_of_preparation_id,
                correction.preparation_number.label("correction_number"),
                ProjectBillingPreparationORM.delivery_requested_at,
                latest.c.event_type.label("external_event_type"),
                latest.c.external_system,
                latest.c.external_status,
                latest.c.external_invoice_reference,
                latest.c.reconciliation_reference,
                latest.c.message.label("external_message"),
                latest.c.occurred_at.label("external_occurred_at"),
                ProjectBillingPreparationORM.updated_at,
            )
            .select_from(ProjectBillingPreparationORM)
            .outerjoin(
                correction,
                and_(
                    correction.id
                    == ProjectBillingPreparationORM.correction_of_preparation_id,
                    correction.tenant_id == ProjectBillingPreparationORM.tenant_id,
                    correction.organization_id
                    == ProjectBillingPreparationORM.organization_id,
                    correction.project_id == ProjectBillingPreparationORM.project_id,
                ),
            )
            .outerjoin(latest, _latest_event_join(latest))
            .where(*conditions)
        )
        total = int(self._session.scalar(select(func.count()).select_from(base.subquery())) or 0)
        page, page_size, offset = _window(
            request.normalized_page, request.normalized_page_size, total
        )
        status_expression = func.coalesce(
            latest.c.external_status,
            ProjectBillingPreparationORM.status,
        )
        sorts = {
            "title": ProjectBillingPreparationORM.preparation_number,
            "statusLabel": status_expression,
            "metaText": func.coalesce(
                latest.c.occurred_at, ProjectBillingPreparationORM.updated_at
            ),
        }
        direction = "asc" if request.sort_direction == "asc" else "desc"
        expression = sorts[request.normalized_sort_key]
        order = expression.asc() if direction == "asc" else expression.desc()
        rows = self._session.execute(
            base.order_by(order, ProjectBillingPreparationORM.id.asc())
            .offset(offset)
            .limit(page_size)
        ).all()
        return FinancePageFacts(
            items=tuple(
                AccountingStatusFact(
                    id=str(row.id),
                    preparation_number=str(row.preparation_number),
                    preparation_status=str(row.status),
                    correction_of_preparation_id=row.correction_of_preparation_id,
                    correction_of_preparation_number=row.correction_number or "",
                    delivery_requested_at=row.delivery_requested_at,
                    latest_external_event_type=row.external_event_type or "",
                    latest_external_system=row.external_system or "",
                    latest_external_status=row.external_status or "",
                    latest_external_invoice_reference=(
                        row.external_invoice_reference or ""
                    ),
                    latest_reconciliation_reference=(
                        row.reconciliation_reference or ""
                    ),
                    latest_external_message=row.external_message or "",
                    latest_external_occurred_at=row.external_occurred_at,
                    updated_at=row.updated_at,
                )
                for row in rows
            ),
            total=total,
            page=page,
            page_size=page_size,
            sort_key=request.normalized_sort_key,
            sort_direction=direction,
        )

    def get_profile(self, *, tenant_id: str, organization_id: str, project_id: str) -> BillingProfileFact | None:
        row = self._session.execute(
            select(ProjectBillingProfileORM).where(
                ProjectBillingProfileORM.tenant_id == tenant_id,
                ProjectBillingProfileORM.organization_id == organization_id,
                ProjectBillingProfileORM.project_id == project_id,
            )
        ).scalar_one_or_none()
        if row is None:
            return None
        return BillingProfileFact(
            id=row.id,
            status=row.status,
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
            row_version=row.version,
        )

    def list_schedule(self, *, tenant_id: str, organization_id: str, project_id: str, request: BillingScheduleQuery) -> FinancePageFacts[BillingScheduleFact]:
        source_state = func.coalesce(ProjectBillingSourceLockORM.status, "available")
        conditions = [
            ProjectBillingScheduleLineORM.tenant_id == tenant_id,
            ProjectBillingScheduleLineORM.organization_id == organization_id,
            ProjectBillingScheduleLineORM.project_id == project_id,
        ]
        status = request.status.strip().lower()
        if status in _SCHEDULE_STATUSES:
            conditions.append(ProjectBillingScheduleLineORM.status == status)
        requested_source_state = request.source_state.strip().lower()
        if requested_source_state in _SOURCE_STATES:
            conditions.append(source_state == requested_source_state)
        if request.search.strip():
            pattern = f"%{request.search.strip()}%"
            conditions.append(or_(
                ProjectBillingScheduleLineORM.name.ilike(pattern),
                ProjectBillingScheduleLineORM.acceptance_reference.ilike(pattern),
                TaskORM.name.ilike(pattern),
                TaskORM.wbs_code.ilike(pattern),
            ))
        base = (
            select(
                ProjectBillingScheduleLineORM.id,
                ProjectBillingScheduleLineORM.name,
                ProjectBillingScheduleLineORM.status,
                ProjectBillingScheduleLineORM.amount,
                ProjectBillingScheduleLineORM.currency_code,
                ProjectBillingScheduleLineORM.due_date,
                ProjectBillingScheduleLineORM.task_id,
                TaskORM.name.label("task_name"),
                TaskORM.wbs_code.label("task_wbs_code"),
                ProjectBillingScheduleLineORM.acceptance_reference,
                source_state.label("source_state"),
                ProjectBillingScheduleLineORM.version,
            )
            .select_from(ProjectBillingScheduleLineORM)
            .outerjoin(TaskORM, and_(
                TaskORM.id == ProjectBillingScheduleLineORM.task_id,
                TaskORM.project_id == ProjectBillingScheduleLineORM.project_id,
            ))
            .outerjoin(ProjectBillingSourceLockORM, and_(
                ProjectBillingSourceLockORM.tenant_id == ProjectBillingScheduleLineORM.tenant_id,
                ProjectBillingSourceLockORM.organization_id == ProjectBillingScheduleLineORM.organization_id,
                ProjectBillingSourceLockORM.project_id == ProjectBillingScheduleLineORM.project_id,
                ProjectBillingSourceLockORM.source_type == "schedule_line",
                ProjectBillingSourceLockORM.source_id == ProjectBillingScheduleLineORM.id,
            ))
            .where(*conditions)
        )
        total = int(self._session.scalar(select(func.count()).select_from(base.subquery())) or 0)
        page, page_size, offset = _window(request.normalized_page, request.normalized_page_size, total)
        sort_key = request.normalized_sort_key
        direction = "asc" if request.sort_direction == "asc" else "desc"
        sorts = {
            "title": ProjectBillingScheduleLineORM.name,
            "statusLabel": ProjectBillingScheduleLineORM.status,
            "subtitle": ProjectBillingScheduleLineORM.amount,
            "supportingText": ProjectBillingScheduleLineORM.due_date,
            "metaText": source_state,
        }
        expression = sorts[sort_key]
        order = expression.asc() if direction == "asc" else expression.desc()
        rows = self._session.execute(
            base.order_by(order, ProjectBillingScheduleLineORM.id.asc()).offset(offset).limit(page_size)
        ).all()
        return FinancePageFacts(
            items=tuple(BillingScheduleFact(
                id=row.id, name=row.name, status=row.status, amount=row.amount,
                currency_code=row.currency_code, due_date=row.due_date, task_id=row.task_id,
                task_name=row.task_name or "", task_wbs_code=row.task_wbs_code or "",
                acceptance_reference=row.acceptance_reference, source_state=row.source_state,
                row_version=row.version,
            ) for row in rows),
            total=total, page=page, page_size=page_size,
            sort_key=sort_key, sort_direction=direction,
        )

    def list_preparations(self, *, tenant_id: str, organization_id: str, project_id: str, request: BillingPreparationQuery) -> FinancePageFacts[BillingPreparationSummaryFact]:
        correction = aliased(ProjectBillingPreparationORM)
        latest = _latest_event_subquery(tenant_id, organization_id, project_id)
        approval_status = func.coalesce(ApprovalRequestORM.status, "")
        conditions = [
            ProjectBillingPreparationORM.tenant_id == tenant_id,
            ProjectBillingPreparationORM.organization_id == organization_id,
            ProjectBillingPreparationORM.project_id == project_id,
        ]
        status = request.status.strip().lower()
        if status in _PREPARATION_STATUSES:
            conditions.append(ProjectBillingPreparationORM.status == status)
        method = request.billing_method.strip().lower()
        if method in _BILLING_METHODS:
            conditions.append(ProjectBillingPreparationORM.billing_method == method)
        if request.approval_status.strip():
            conditions.append(func.lower(approval_status) == request.approval_status.strip().lower())
        correction_state = request.correction_state.strip().lower()
        if correction_state in _CORRECTION_STATES:
            conditions.append(
                ProjectBillingPreparationORM.correction_of_preparation_id.is_not(None)
                if correction_state == "correction"
                else ProjectBillingPreparationORM.correction_of_preparation_id.is_(None)
            )
        delivery_state = request.delivery_state.strip().lower()
        if delivery_state in _DELIVERY_STATES:
            conditions.append(_delivery_condition(delivery_state, latest))
        if request.search.strip():
            pattern = f"%{request.search.strip()}%"
            conditions.append(or_(
                ProjectBillingPreparationORM.preparation_number.ilike(pattern),
                ProjectBillingPreparationORM.created_by.ilike(pattern),
                ProjectBillingPreparationORM.approval_request_id.ilike(pattern),
                correction.preparation_number.ilike(pattern),
                latest.c.external_invoice_reference.ilike(pattern),
                latest.c.reconciliation_reference.ilike(pattern),
            ))
        base = (
            select(
                ProjectBillingPreparationORM.id,
                ProjectBillingPreparationORM.preparation_number,
                ProjectBillingPreparationORM.billing_method,
                ProjectBillingPreparationORM.period_start,
                ProjectBillingPreparationORM.period_end,
                ProjectBillingPreparationORM.status,
                approval_status.label("approval_status"),
                ProjectBillingPreparationORM.currency_code,
                ProjectBillingPreparationORM.line_count,
                ProjectBillingPreparationORM.total_amount,
                ProjectBillingPreparationORM.correction_of_preparation_id,
                correction.preparation_number.label("correction_number"),
                ProjectBillingPreparationORM.delivery_requested_at,
                latest.c.event_type.label("external_event_type"),
                latest.c.external_status,
                latest.c.external_system,
                latest.c.occurred_at.label("external_occurred_at"),
                ProjectBillingPreparationORM.created_at,
                ProjectBillingPreparationORM.submitted_at,
                ProjectBillingPreparationORM.approved_at,
                ProjectBillingPreparationORM.version,
            )
            .select_from(ProjectBillingPreparationORM)
            .outerjoin(ApprovalRequestORM, _approval_join())
            .outerjoin(correction, and_(
                correction.id == ProjectBillingPreparationORM.correction_of_preparation_id,
                correction.tenant_id == ProjectBillingPreparationORM.tenant_id,
                correction.organization_id == ProjectBillingPreparationORM.organization_id,
                correction.project_id == ProjectBillingPreparationORM.project_id,
            ))
            .outerjoin(latest, _latest_event_join(latest))
            .where(*conditions)
        )
        total = int(self._session.scalar(select(func.count()).select_from(base.subquery())) or 0)
        page, page_size, offset = _window(request.normalized_page, request.normalized_page_size, total)
        sort_key = request.normalized_sort_key
        direction = "asc" if request.sort_direction == "asc" else "desc"
        sorts = {
            "title": ProjectBillingPreparationORM.preparation_number,
            "statusLabel": ProjectBillingPreparationORM.status,
            "subtitle": ProjectBillingPreparationORM.period_start,
            "supportingText": ProjectBillingPreparationORM.total_amount,
            "metaText": ProjectBillingPreparationORM.created_at,
        }
        expression = sorts[sort_key]
        order = expression.asc() if direction == "asc" else expression.desc()
        rows = self._session.execute(
            base.order_by(order, ProjectBillingPreparationORM.id.asc()).offset(offset).limit(page_size)
        ).all()
        return FinancePageFacts(
            items=tuple(BillingPreparationSummaryFact(
                id=row.id, preparation_number=row.preparation_number,
                billing_method=row.billing_method, period_start=row.period_start,
                period_end=row.period_end, status=row.status,
                approval_status=row.approval_status or "", currency_code=row.currency_code,
                line_count=row.line_count, total_amount=row.total_amount,
                correction_of_preparation_id=row.correction_of_preparation_id,
                correction_of_preparation_number=row.correction_number or "",
                delivery_requested_at=row.delivery_requested_at,
                latest_external_event_type=row.external_event_type or "",
                latest_external_status=row.external_status or "",
                latest_external_system=row.external_system or "",
                latest_external_occurred_at=row.external_occurred_at,
                created_at=row.created_at, submitted_at=row.submitted_at,
                approved_at=row.approved_at, row_version=row.version,
            ) for row in rows),
            total=total, page=page, page_size=page_size,
            sort_key=sort_key, sort_direction=direction,
        )

    def get_preparation(self, *, tenant_id: str, organization_id: str, project_id: str, preparation_id: str) -> BillingPreparationDetailFact | None:
        correction = aliased(ProjectBillingPreparationORM)
        latest = _latest_event_subquery(tenant_id, organization_id, project_id)
        locks = _lock_summary_subquery(tenant_id, organization_id, project_id)
        row = self._session.execute(
            select(
                ProjectBillingPreparationORM,
                correction.preparation_number.label("correction_number"),
                ApprovalRequestORM.status.label("approval_status"),
                ApprovalRequestORM.requested_by_username,
                ApprovalRequestORM.requested_at,
                ApprovalRequestORM.decided_by_username,
                ApprovalRequestORM.decided_at,
                ApprovalRequestORM.decision_note,
                func.coalesce(locks.c.lock_count, 0).label("lock_count"),
                func.coalesce(locks.c.reserved_count, 0).label("reserved_count"),
                func.coalesce(locks.c.finalized_count, 0).label("finalized_count"),
                func.coalesce(locks.c.released_count, 0).label("released_count"),
                latest.c.event_type.label("external_event_type"),
                latest.c.external_system,
                latest.c.external_status,
                latest.c.external_invoice_reference,
                latest.c.reconciliation_reference,
                latest.c.message.label("external_message"),
                latest.c.occurred_at.label("external_occurred_at"),
            )
            .select_from(ProjectBillingPreparationORM)
            .outerjoin(ApprovalRequestORM, _approval_join())
            .outerjoin(correction, and_(
                correction.id == ProjectBillingPreparationORM.correction_of_preparation_id,
                correction.tenant_id == ProjectBillingPreparationORM.tenant_id,
                correction.organization_id == ProjectBillingPreparationORM.organization_id,
                correction.project_id == ProjectBillingPreparationORM.project_id,
            ))
            .outerjoin(locks, and_(
                locks.c.tenant_id == ProjectBillingPreparationORM.tenant_id,
                locks.c.organization_id == ProjectBillingPreparationORM.organization_id,
                locks.c.project_id == ProjectBillingPreparationORM.project_id,
                locks.c.preparation_id == ProjectBillingPreparationORM.id,
            ))
            .outerjoin(latest, _latest_event_join(latest))
            .where(
                ProjectBillingPreparationORM.tenant_id == tenant_id,
                ProjectBillingPreparationORM.organization_id == organization_id,
                ProjectBillingPreparationORM.project_id == project_id,
                ProjectBillingPreparationORM.id == preparation_id,
            )
        ).one_or_none()
        if row is None:
            return None
        item = row[0]
        return BillingPreparationDetailFact(
            id=item.id, preparation_number=item.preparation_number,
            billing_method=item.billing_method, period_start=item.period_start,
            period_end=item.period_end, status=item.status, currency_code=item.currency_code,
            line_count=item.line_count, total_amount=item.total_amount,
            correction_of_preparation_id=item.correction_of_preparation_id,
            correction_of_preparation_number=row.correction_number or "",
            approval_request_id=item.approval_request_id,
            approval_status=row.approval_status or "",
            approval_requested_by=row.requested_by_username or "",
            approval_requested_at=row.requested_at,
            approval_decided_by=row.decided_by_username or "",
            approval_decided_at=row.decided_at,
            approval_decision_note=row.decision_note or "",
            submitted_by=item.submitted_by, submitted_at=item.submitted_at,
            approved_by=item.approved_by, approved_at=item.approved_at,
            rejected_by=item.rejected_by, rejected_at=item.rejected_at,
            rejection_notes=item.rejection_notes,
            delivery_requested_at=item.delivery_requested_at,
            delivered_at=item.delivered_at, acknowledged_at=item.acknowledged_at,
            reconciled_at=item.reconciled_at,
            lock_count=int(row.lock_count), reserved_lock_count=int(row.reserved_count),
            finalized_lock_count=int(row.finalized_count), released_lock_count=int(row.released_count),
            latest_external_event_type=row.external_event_type or "",
            latest_external_system=row.external_system or "",
            latest_external_status=row.external_status or "",
            latest_external_invoice_reference=row.external_invoice_reference or "",
            latest_reconciliation_reference=row.reconciliation_reference or "",
            latest_external_message=row.external_message or "",
            latest_external_occurred_at=row.external_occurred_at,
            created_by=item.created_by, created_at=item.created_at,
            updated_at=item.updated_at, row_version=item.version,
        )

    def list_preparation_lines(self, *, tenant_id: str, organization_id: str, project_id: str, preparation_id: str, request: BillingPreparationLineQuery) -> FinancePageFacts[BillingPreparationLineFact]:
        source_state = func.coalesce(ProjectBillingSourceLockORM.status, "available")
        conditions = [
            ProjectBillingPreparationORM.tenant_id == tenant_id,
            ProjectBillingPreparationORM.organization_id == organization_id,
            ProjectBillingPreparationORM.project_id == project_id,
            ProjectBillingPreparationORM.id == preparation_id,
            ProjectBillingPreparationLineORM.tenant_id == tenant_id,
            ProjectBillingPreparationLineORM.organization_id == organization_id,
            ProjectBillingPreparationLineORM.project_id == project_id,
            ProjectBillingPreparationLineORM.preparation_id == preparation_id,
        ]
        source_type = request.source_type.strip().lower()
        if source_type in _SOURCE_TYPES:
            conditions.append(ProjectBillingPreparationLineORM.source_type == source_type)
        requested_source_state = request.source_state.strip().lower()
        if requested_source_state in _SOURCE_STATES:
            conditions.append(source_state == requested_source_state)
        if request.search.strip():
            pattern = f"%{request.search.strip()}%"
            conditions.append(or_(
                ProjectBillingPreparationLineORM.description.ilike(pattern),
                ProjectBillingPreparationLineORM.source_id.ilike(pattern),
                ProjectBillingPreparationLineORM.source_revision.ilike(pattern),
                ProjectBillingPreparationLineORM.task_id.ilike(pattern),
                ProjectBillingPreparationLineORM.resource_id.ilike(pattern),
            ))
        base = (
            select(
                ProjectBillingPreparationLineORM,
                source_state.label("source_state"),
            )
            .select_from(ProjectBillingPreparationLineORM)
            .join(ProjectBillingPreparationORM, and_(
                ProjectBillingPreparationORM.tenant_id == ProjectBillingPreparationLineORM.tenant_id,
                ProjectBillingPreparationORM.organization_id == ProjectBillingPreparationLineORM.organization_id,
                ProjectBillingPreparationORM.project_id == ProjectBillingPreparationLineORM.project_id,
                ProjectBillingPreparationORM.id == ProjectBillingPreparationLineORM.preparation_id,
            ))
            .outerjoin(ProjectBillingSourceLockORM, and_(
                ProjectBillingSourceLockORM.tenant_id == ProjectBillingPreparationLineORM.tenant_id,
                ProjectBillingSourceLockORM.organization_id == ProjectBillingPreparationLineORM.organization_id,
                ProjectBillingSourceLockORM.project_id == ProjectBillingPreparationLineORM.project_id,
                ProjectBillingSourceLockORM.preparation_id == ProjectBillingPreparationLineORM.preparation_id,
                ProjectBillingSourceLockORM.preparation_line_id == ProjectBillingPreparationLineORM.id,
            ))
            .where(*conditions)
        )
        total = int(self._session.scalar(select(func.count()).select_from(base.subquery())) or 0)
        page, page_size, offset = _window(request.normalized_page, request.normalized_page_size, total)
        sort_key = request.normalized_sort_key
        direction = "asc" if request.sort_direction == "asc" else "desc"
        sorts = {
            "title": ProjectBillingPreparationLineORM.description,
            "statusLabel": ProjectBillingPreparationLineORM.source_type,
            "subtitle": ProjectBillingPreparationLineORM.net_amount,
            "supportingText": source_state,
            "metaText": ProjectBillingPreparationLineORM.source_date,
        }
        expression = sorts[sort_key]
        order = expression.asc() if direction == "asc" else expression.desc()
        rows = self._session.execute(
            base.order_by(order, ProjectBillingPreparationLineORM.id.asc()).offset(offset).limit(page_size)
        ).all()
        return FinancePageFacts(
            items=tuple(_line_fact(row[0], row.source_state) for row in rows),
            total=total, page=page, page_size=page_size,
            sort_key=sort_key, sort_direction=direction,
        )


def _approval_join():
    return and_(
        ApprovalRequestORM.id == ProjectBillingPreparationORM.approval_request_id,
        ApprovalRequestORM.tenant_id == ProjectBillingPreparationORM.tenant_id,
        ApprovalRequestORM.organization_id == ProjectBillingPreparationORM.organization_id,
        ApprovalRequestORM.project_id == ProjectBillingPreparationORM.project_id,
    )


def _latest_event_subquery(tenant_id: str, organization_id: str, project_id: str):
    ranked = select(
        ProjectBillingExternalEventORM.id,
        ProjectBillingExternalEventORM.tenant_id,
        ProjectBillingExternalEventORM.organization_id,
        ProjectBillingExternalEventORM.project_id,
        ProjectBillingExternalEventORM.preparation_id,
        ProjectBillingExternalEventORM.event_type,
        ProjectBillingExternalEventORM.external_system,
        ProjectBillingExternalEventORM.external_status,
        ProjectBillingExternalEventORM.external_invoice_reference,
        ProjectBillingExternalEventORM.reconciliation_reference,
        ProjectBillingExternalEventORM.message,
        ProjectBillingExternalEventORM.occurred_at,
        func.row_number().over(
            partition_by=(
                ProjectBillingExternalEventORM.tenant_id,
                ProjectBillingExternalEventORM.organization_id,
                ProjectBillingExternalEventORM.preparation_id,
            ),
            order_by=(
                ProjectBillingExternalEventORM.occurred_at.desc(),
                ProjectBillingExternalEventORM.id.desc(),
            ),
        ).label("row_number"),
    ).where(
        ProjectBillingExternalEventORM.tenant_id == tenant_id,
        ProjectBillingExternalEventORM.organization_id == organization_id,
        ProjectBillingExternalEventORM.project_id == project_id,
    ).subquery("ranked_billing_events")
    return select(*[ranked.c[name] for name in (
        "id", "tenant_id", "organization_id", "project_id", "preparation_id",
        "event_type", "external_system", "external_status", "external_invoice_reference",
        "reconciliation_reference", "message", "occurred_at",
    )]).where(ranked.c.row_number == 1).subquery("latest_billing_event")


def _latest_event_join(latest):
    return and_(
        latest.c.tenant_id == ProjectBillingPreparationORM.tenant_id,
        latest.c.organization_id == ProjectBillingPreparationORM.organization_id,
        latest.c.project_id == ProjectBillingPreparationORM.project_id,
        latest.c.preparation_id == ProjectBillingPreparationORM.id,
    )


def _lock_summary_subquery(tenant_id: str, organization_id: str, project_id: str):
    return select(
        ProjectBillingSourceLockORM.tenant_id,
        ProjectBillingSourceLockORM.organization_id,
        ProjectBillingSourceLockORM.project_id,
        ProjectBillingSourceLockORM.preparation_id,
        func.count(ProjectBillingSourceLockORM.id).label("lock_count"),
        func.sum(case((ProjectBillingSourceLockORM.status == "reserved", 1), else_=0)).label("reserved_count"),
        func.sum(case((ProjectBillingSourceLockORM.status == "finalized", 1), else_=0)).label("finalized_count"),
        func.sum(case((ProjectBillingSourceLockORM.status == "released", 1), else_=0)).label("released_count"),
    ).where(
        ProjectBillingSourceLockORM.tenant_id == tenant_id,
        ProjectBillingSourceLockORM.organization_id == organization_id,
        ProjectBillingSourceLockORM.project_id == project_id,
    ).group_by(
        ProjectBillingSourceLockORM.tenant_id,
        ProjectBillingSourceLockORM.organization_id,
        ProjectBillingSourceLockORM.project_id,
        ProjectBillingSourceLockORM.preparation_id,
    ).subquery("billing_lock_summary")


def _delivery_condition(state: str, latest):
    if state == "external_acknowledged":
        return latest.c.id.is_not(None)
    if state == "local_requested":
        return and_(ProjectBillingPreparationORM.delivery_requested_at.is_not(None), latest.c.id.is_(None))
    if state == "ready":
        return and_(
            ProjectBillingPreparationORM.status == "approved",
            ProjectBillingPreparationORM.delivery_requested_at.is_(None),
        )
    return ProjectBillingPreparationORM.delivery_requested_at.is_(None)


def _line_fact(item, source_state: str) -> BillingPreparationLineFact:
    return BillingPreparationLineFact(
        id=item.id, preparation_id=item.preparation_id, source_type=item.source_type,
        source_id=item.source_id, source_revision=item.source_revision,
        description=item.description, source_date=item.source_date,
        quantity=item.quantity, unit=item.unit, unit_rate=item.unit_rate,
        net_amount=item.net_amount, currency_code=item.currency_code,
        task_id=item.task_id, resource_id=item.resource_id,
        source_amount=item.source_amount, markup_percent=item.markup_percent,
        rate_card_id=item.rate_card_id, rate_line_id=item.rate_line_id,
        rate_card_version=item.rate_card_version, source_state=source_state,
    )


def _window(page: int, page_size: int, total: int) -> tuple[int, int, int]:
    last_page = max(1, (total + page_size - 1) // page_size)
    normalized_page = min(page, last_page)
    return normalized_page, page_size, (normalized_page - 1) * page_size


__all__ = ["SqlAlchemyFinanceBillingReader"]

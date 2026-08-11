from __future__ import annotations

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from src.core.modules.project_management.contracts.repositories.billing import (
    ProjectBillingRepository,
)
from src.core.modules.project_management.domain.financials.billing_preparation import (
    BillableSourceType,
    ProjectBillingExternalEvent,
    ProjectBillingPreparation,
    ProjectBillingPreparationLine,
    ProjectBillingSourceLock,
)
from src.core.modules.project_management.domain.financials.billing_profile import (
    ProjectBillingProfile,
    ProjectBillingScheduleLine,
)
from src.core.modules.project_management.infrastructure.persistence.mappers.billing import (
    billing_profile_from_orm,
    billing_profile_to_orm,
    external_event_from_orm,
    external_event_to_orm,
    preparation_from_orm,
    preparation_line_from_orm,
    preparation_line_to_orm,
    preparation_to_orm,
    schedule_line_from_orm,
    schedule_line_to_orm,
    source_lock_from_orm,
    source_lock_to_orm,
)
from src.core.modules.project_management.infrastructure.persistence.orm.billing import (
    ProjectBillingExternalEventORM,
    ProjectBillingPreparationLineORM,
    ProjectBillingPreparationORM,
    ProjectBillingProfileORM,
    ProjectBillingScheduleLineORM,
    ProjectBillingSourceLockORM,
)
from src.core.modules.project_management.infrastructure.persistence.orm.project import ProjectORM
from src.core.platform.application.tenant.tenancy.tenant_context import (
    ActiveScopeIds,
    TenantContextService,
)
from src.core.platform.common.exceptions import BusinessRuleError, NotFoundError
from src.infra.persistence.db.optimistic import update_with_version_check


class SqlAlchemyProjectBillingRepository(ProjectBillingRepository):
    def __init__(self, session: Session) -> None:
        self.session = session
        self._tenant_context_service: TenantContextService | None = None

    def _context(self, *, operation_label: str) -> ActiveScopeIds:
        if self._tenant_context_service is None:
            raise BusinessRuleError(
                "Project billing repository requires TenantContextService.",
                code="TENANT_CONTEXT_REQUIRED",
            )
        return self._tenant_context_service.require_active_scope_ids(
            operation_label=operation_label
        )

    @staticmethod
    def _require_scope(value, context: ActiveScopeIds) -> None:
        if (
            value.tenant_id != context.tenant_id
            or value.organization_id != context.organization_id
        ):
            raise BusinessRuleError(
                "Project billing scope does not match the active organization.",
                code="PROJECT_BILLING_SCOPE_MISMATCH",
            )

    def _require_project(self, project_id: str, context: ActiveScopeIds) -> None:
        project = self.session.execute(
            select(ProjectORM.id).where(
                ProjectORM.id == project_id,
                ProjectORM.tenant_id == context.tenant_id,
                ProjectORM.organization_id == context.organization_id,
            )
        ).scalar_one_or_none()
        if project is None:
            raise NotFoundError("Project not found.", code="PROJECT_NOT_FOUND")

    def add_profile(self, profile: ProjectBillingProfile) -> None:
        context = self._context(operation_label="create project billing profile")
        self._require_scope(profile, context)
        self._require_project(profile.project_id, context)
        self.session.add(billing_profile_to_orm(profile))

    def get_profile(self, project_id: str) -> ProjectBillingProfile | None:
        context = self._context(operation_label="access project billing profile")
        row = self.session.execute(
            select(ProjectBillingProfileORM).where(
                ProjectBillingProfileORM.project_id == project_id,
                ProjectBillingProfileORM.tenant_id == context.tenant_id,
                ProjectBillingProfileORM.organization_id == context.organization_id,
            )
        ).scalar_one_or_none()
        return billing_profile_from_orm(row) if row else None

    def update_profile(
        self, profile: ProjectBillingProfile, *, expected_row_version: int
    ) -> None:
        context = self._context(operation_label="update project billing profile")
        self._require_scope(profile, context)
        profile.row_version = update_with_version_check(
            self.session,
            ProjectBillingProfileORM,
            profile.id,
            expected_row_version,
            {
                "currency_code": profile.currency_code,
                "contract_reference": profile.contract_reference,
                "contract_value": profile.contract_value,
                "customer_party_id": profile.customer_party_id,
                "external_customer_reference": profile.external_customer_reference,
                "purchase_order_reference": profile.purchase_order_reference,
                "cost_plus_markup_percent": profile.cost_plus_markup_percent,
                "payment_terms_days": profile.payment_terms_days,
                "retention_years": profile.retention_years,
                "legal_hold": profile.legal_hold,
                "status": profile.status.value,
                "updated_by": profile.updated_by,
                "updated_at": profile.updated_at,
            },
            extra_filters={
                "tenant_id": context.tenant_id,
                "organization_id": context.organization_id,
                "project_id": profile.project_id,
            },
            not_found_message="Project billing profile not found.",
            stale_message="Project billing profile was updated by another user.",
        )

    def add_schedule_line(self, line: ProjectBillingScheduleLine) -> None:
        context = self._context(operation_label="create billing schedule line")
        self._require_scope(line, context)
        profile = self._profile_row(line.project_id, context)
        if profile.id != line.billing_profile_id:
            raise BusinessRuleError(
                "Billing schedule profile does not match its Project.",
                code="BILLING_SCHEDULE_PROFILE_MISMATCH",
            )
        self.session.add(schedule_line_to_orm(line))

    def get_schedule_line(self, line_id: str) -> ProjectBillingScheduleLine | None:
        context = self._context(operation_label="access billing schedule line")
        row = self.session.execute(
            select(ProjectBillingScheduleLineORM).where(
                ProjectBillingScheduleLineORM.id == line_id,
                ProjectBillingScheduleLineORM.tenant_id == context.tenant_id,
                ProjectBillingScheduleLineORM.organization_id == context.organization_id,
            )
        ).scalar_one_or_none()
        return schedule_line_from_orm(row) if row else None

    def list_schedule_lines(self, project_id: str) -> list[ProjectBillingScheduleLine]:
        context = self._context(operation_label="list billing schedule lines")
        self._profile_row(project_id, context)
        rows = self.session.execute(
            select(ProjectBillingScheduleLineORM)
            .where(
                ProjectBillingScheduleLineORM.project_id == project_id,
                ProjectBillingScheduleLineORM.tenant_id == context.tenant_id,
                ProjectBillingScheduleLineORM.organization_id == context.organization_id,
            )
            .order_by(
                ProjectBillingScheduleLineORM.due_date.asc(),
                ProjectBillingScheduleLineORM.id.asc(),
            )
        ).scalars().all()
        return [schedule_line_from_orm(row) for row in rows]

    def update_schedule_line(
        self, line: ProjectBillingScheduleLine, *, expected_row_version: int
    ) -> None:
        context = self._context(operation_label="update billing schedule line")
        self._require_scope(line, context)
        line.row_version = update_with_version_check(
            self.session,
            ProjectBillingScheduleLineORM,
            line.id,
            expected_row_version,
            {
                "name": line.name,
                "amount": line.amount,
                "currency_code": line.currency_code,
                "due_date": line.due_date,
                "task_id": line.task_id,
                "acceptance_reference": line.acceptance_reference,
                "status": line.status.value,
                "updated_by": line.updated_by,
                "updated_at": line.updated_at,
            },
            extra_filters={
                "tenant_id": context.tenant_id,
                "organization_id": context.organization_id,
                "project_id": line.project_id,
                "billing_profile_id": line.billing_profile_id,
            },
            not_found_message="Billing schedule line not found.",
            stale_message="Billing schedule line was updated by another user.",
        )

    def add_preparation(self, preparation: ProjectBillingPreparation) -> None:
        context = self._context(operation_label="create billing preparation")
        self._require_scope(preparation, context)
        profile = self._profile_row(preparation.project_id, context)
        if profile.id != preparation.billing_profile_id:
            raise BusinessRuleError(
                "Billing preparation profile does not match its Project.",
                code="BILLING_PREPARATION_PROFILE_MISMATCH",
            )
        self.session.add(preparation_to_orm(preparation))

    def get_preparation(self, preparation_id: str) -> ProjectBillingPreparation | None:
        context = self._context(operation_label="access billing preparation")
        row = self.session.execute(
            select(ProjectBillingPreparationORM).where(
                ProjectBillingPreparationORM.id == preparation_id,
                ProjectBillingPreparationORM.tenant_id == context.tenant_id,
                ProjectBillingPreparationORM.organization_id == context.organization_id,
            )
        ).scalar_one_or_none()
        return preparation_from_orm(row) if row else None

    def get_preparation_by_idempotency_key(
        self, idempotency_key: str
    ) -> ProjectBillingPreparation | None:
        context = self._context(operation_label="resolve billing preparation retry")
        row = self.session.execute(
            select(ProjectBillingPreparationORM).where(
                ProjectBillingPreparationORM.idempotency_key == idempotency_key,
                ProjectBillingPreparationORM.tenant_id == context.tenant_id,
                ProjectBillingPreparationORM.organization_id == context.organization_id,
            )
        ).scalar_one_or_none()
        return preparation_from_orm(row) if row else None

    def list_preparations(self, project_id: str) -> list[ProjectBillingPreparation]:
        context = self._context(operation_label="list billing preparations")
        self._profile_row(project_id, context)
        rows = self.session.execute(
            select(ProjectBillingPreparationORM)
            .where(
                ProjectBillingPreparationORM.project_id == project_id,
                ProjectBillingPreparationORM.tenant_id == context.tenant_id,
                ProjectBillingPreparationORM.organization_id == context.organization_id,
            )
            .order_by(
                ProjectBillingPreparationORM.created_at.desc(),
                ProjectBillingPreparationORM.id.desc(),
            )
        ).scalars().all()
        return [preparation_from_orm(row) for row in rows]

    def update_preparation(
        self, preparation: ProjectBillingPreparation, *, expected_row_version: int
    ) -> None:
        context = self._context(operation_label="update billing preparation")
        self._require_scope(preparation, context)
        preparation.row_version = update_with_version_check(
            self.session,
            ProjectBillingPreparationORM,
            preparation.id,
            expected_row_version,
            {
                "status": preparation.status.value,
                "line_count": preparation.line_count,
                "total_amount": preparation.total_amount,
                "approval_request_id": preparation.approval_request_id,
                "submitted_by": preparation.submitted_by,
                "submitted_at": preparation.submitted_at,
                "approved_by": preparation.approved_by,
                "approved_at": preparation.approved_at,
                "rejected_by": preparation.rejected_by,
                "rejected_at": preparation.rejected_at,
                "rejection_notes": preparation.rejection_notes,
                "delivery_requested_at": preparation.delivery_requested_at,
                "delivered_at": preparation.delivered_at,
                "acknowledged_at": preparation.acknowledged_at,
                "reconciled_at": preparation.reconciled_at,
                "updated_at": preparation.updated_at,
            },
            extra_filters={
                "tenant_id": context.tenant_id,
                "organization_id": context.organization_id,
                "project_id": preparation.project_id,
            },
            not_found_message="Billing preparation not found.",
            stale_message="Billing preparation was updated by another user.",
        )

    def reserve_source(
        self,
        line: ProjectBillingPreparationLine,
        source_lock: ProjectBillingSourceLock,
    ) -> None:
        context = self._context(operation_label="reserve billable source")
        self._require_scope(line, context)
        self._require_scope(source_lock, context)
        if (
            line.project_id != source_lock.project_id
            or line.preparation_id != source_lock.preparation_id
            or line.id != source_lock.preparation_line_id
            or line.source_type != source_lock.source_type
            or line.source_id != source_lock.source_id
            or line.source_revision != source_lock.source_revision
            or line.source_content_hash != source_lock.source_content_hash
        ):
            raise BusinessRuleError(
                "Billing line and source-lock snapshots do not match.",
                code="BILLING_SOURCE_LOCK_SNAPSHOT_MISMATCH",
            )
        self._preparation_row(line.preparation_id, context)
        self.session.add(preparation_line_to_orm(line))
        self.session.add(source_lock_to_orm(source_lock))

    def list_preparation_lines(
        self, preparation_id: str
    ) -> list[ProjectBillingPreparationLine]:
        context = self._context(operation_label="list billing preparation lines")
        self._preparation_row(preparation_id, context)
        rows = self.session.execute(
            select(ProjectBillingPreparationLineORM)
            .where(
                ProjectBillingPreparationLineORM.preparation_id == preparation_id,
                ProjectBillingPreparationLineORM.tenant_id == context.tenant_id,
                ProjectBillingPreparationLineORM.organization_id == context.organization_id,
            )
            .order_by(
                ProjectBillingPreparationLineORM.source_date.asc(),
                ProjectBillingPreparationLineORM.id.asc(),
            )
        ).scalars().all()
        return [preparation_line_from_orm(row) for row in rows]

    def get_source_lock(
        self, *, source_type: BillableSourceType, source_id: str
    ) -> ProjectBillingSourceLock | None:
        context = self._context(operation_label="access billable source lock")
        row = self.session.execute(
            select(ProjectBillingSourceLockORM).where(
                ProjectBillingSourceLockORM.source_type == source_type.value,
                ProjectBillingSourceLockORM.source_id == source_id,
                ProjectBillingSourceLockORM.tenant_id == context.tenant_id,
                ProjectBillingSourceLockORM.organization_id == context.organization_id,
            )
        ).scalar_one_or_none()
        return source_lock_from_orm(row) if row else None

    def list_source_locks(self, preparation_id: str) -> list[ProjectBillingSourceLock]:
        context = self._context(operation_label="list billable source locks")
        self._preparation_row(preparation_id, context)
        rows = self.session.execute(
            select(ProjectBillingSourceLockORM).where(
                ProjectBillingSourceLockORM.preparation_id == preparation_id,
                ProjectBillingSourceLockORM.tenant_id == context.tenant_id,
                ProjectBillingSourceLockORM.organization_id == context.organization_id,
            )
        ).scalars().all()
        return [source_lock_from_orm(row) for row in rows]

    def update_source_lock(self, source_lock: ProjectBillingSourceLock) -> None:
        context = self._context(operation_label="update billable source lock")
        self._require_scope(source_lock, context)
        result = self.session.execute(
            update(ProjectBillingSourceLockORM)
            .where(
                ProjectBillingSourceLockORM.id == source_lock.id,
                ProjectBillingSourceLockORM.tenant_id == context.tenant_id,
                ProjectBillingSourceLockORM.organization_id == context.organization_id,
                ProjectBillingSourceLockORM.preparation_id == source_lock.preparation_id,
            )
            .values(
                status=source_lock.status.value,
                finalized_at=source_lock.finalized_at,
                released_at=source_lock.released_at,
            )
        )
        if result.rowcount != 1:
            raise NotFoundError(
                "Billable source lock not found.", code="BILLING_SOURCE_LOCK_NOT_FOUND"
            )

    def add_external_event(self, event: ProjectBillingExternalEvent) -> None:
        context = self._context(operation_label="record external billing outcome")
        self._require_scope(event, context)
        self._preparation_row(event.preparation_id, context)
        self.session.add(external_event_to_orm(event))

    def get_external_event_by_idempotency_key(
        self, *, external_system: str, idempotency_key: str
    ) -> ProjectBillingExternalEvent | None:
        context = self._context(operation_label="resolve external billing retry")
        row = self.session.execute(
            select(ProjectBillingExternalEventORM).where(
                ProjectBillingExternalEventORM.external_system == external_system,
                ProjectBillingExternalEventORM.idempotency_key == idempotency_key,
                ProjectBillingExternalEventORM.tenant_id == context.tenant_id,
                ProjectBillingExternalEventORM.organization_id == context.organization_id,
            )
        ).scalar_one_or_none()
        return external_event_from_orm(row) if row else None

    def list_external_events(
        self, preparation_id: str
    ) -> list[ProjectBillingExternalEvent]:
        context = self._context(operation_label="list external billing outcomes")
        self._preparation_row(preparation_id, context)
        rows = self.session.execute(
            select(ProjectBillingExternalEventORM)
            .where(
                ProjectBillingExternalEventORM.preparation_id == preparation_id,
                ProjectBillingExternalEventORM.tenant_id == context.tenant_id,
                ProjectBillingExternalEventORM.organization_id == context.organization_id,
            )
            .order_by(
                ProjectBillingExternalEventORM.occurred_at.asc(),
                ProjectBillingExternalEventORM.id.asc(),
            )
        ).scalars().all()
        return [external_event_from_orm(row) for row in rows]

    def flush(self) -> None:
        self.session.flush()

    def _profile_row(
        self, project_id: str, context: ActiveScopeIds
    ) -> ProjectBillingProfileORM:
        row = self.session.execute(
            select(ProjectBillingProfileORM).where(
                ProjectBillingProfileORM.project_id == project_id,
                ProjectBillingProfileORM.tenant_id == context.tenant_id,
                ProjectBillingProfileORM.organization_id == context.organization_id,
            )
        ).scalar_one_or_none()
        if row is None:
            raise NotFoundError(
                "Project billing profile not found.", code="BILLING_PROFILE_NOT_FOUND"
            )
        return row

    def _preparation_row(
        self, preparation_id: str, context: ActiveScopeIds
    ) -> ProjectBillingPreparationORM:
        row = self.session.execute(
            select(ProjectBillingPreparationORM).where(
                ProjectBillingPreparationORM.id == preparation_id,
                ProjectBillingPreparationORM.tenant_id == context.tenant_id,
                ProjectBillingPreparationORM.organization_id == context.organization_id,
            )
        ).scalar_one_or_none()
        if row is None:
            raise NotFoundError(
                "Billing preparation not found.", code="BILLING_PREPARATION_NOT_FOUND"
            )
        return row


__all__ = ["SqlAlchemyProjectBillingRepository"]

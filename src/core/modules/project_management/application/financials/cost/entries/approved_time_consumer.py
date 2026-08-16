from src.core.modules.project_management.application.financials.cost.entries.cost_entry_service import ProjectCostEntryService
from src.core.modules.project_management.contracts.financial_sources.approved_time import (
    ApprovedTimeFinancialSource,
)
from src.core.modules.project_management.contracts.financial_sources.reference import (
    FinancialPostingPurpose,
    FinancialSourceModule,
    FinancialSourceReference,
    FinancialSourceType,
)
from src.core.modules.project_management.domain.financials.cost_entry import ProjectCostEntry
from src.core.platform.integration import APPROVED_TIME_ENTRY_EVENT_TYPE, ApprovedTimeEntryEventPayload, IntegrationEventEnvelope


class ApprovedTimeLaborCostConsumer:
    def __init__(self, cost_entry_service: ProjectCostEntryService) -> None:
        self._cost_entry_service = cost_entry_service

    def consume(self, envelope: IntegrationEventEnvelope) -> ProjectCostEntry:
        if envelope.event_type != APPROVED_TIME_ENTRY_EVENT_TYPE:
            raise ValueError(f"Unsupported Approved Time event: {envelope.event_type}")
        payload = ApprovedTimeEntryEventPayload.model_validate(envelope.payload)
        source = ApprovedTimeFinancialSource(
            reference=FinancialSourceReference(
                tenant_id=envelope.tenant_id,
                organization_id=str(envelope.organization_id),
                project_id=payload.project_id,
                source_module=FinancialSourceModule.PLATFORM_TIME,
                source_type=FinancialSourceType.TIME_ENTRY,
                source_id=payload.time_entry_id,
                source_revision=str(payload.source_revision),
                content_hash=payload.source_content_hash,
                posting_purpose=FinancialPostingPurpose.LABOR_ACTUAL,
            ),
            approved_snapshot_id=payload.approved_snapshot_id,
            timesheet_period_id=payload.timesheet_period_id,
            time_entry_id=payload.time_entry_id,
            work_allocation_id=payload.work_allocation_id,
            resource_id=payload.resource_id,
            employee_id=payload.employee_id,
            assignment_id=payload.assignment_id,
            task_id=payload.task_id,
            work_date=payload.work_date,
            approved_at=payload.approved_at,
            hours=payload.hours,
            correction_of_revision=(str(payload.correction_of_revision) if payload.correction_of_revision else None),
        )
        return self._cost_entry_service.apply_approved_time_source(source)


__all__ = ["ApprovedTimeLaborCostConsumer"]

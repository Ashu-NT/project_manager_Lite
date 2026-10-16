from __future__ import annotations

from src.core.modules.project_management.application.financials.integration.dto.responses.posting_failures import (
    FinancialPostingFailureDto,
    FinancialPostingFailurePageDto,
)
from src.core.modules.project_management.contracts.reads.financials.integration.models.integration_facts import (
    ApprovedTimePostingFailurePage,
)


def map_posting_failures(result: ApprovedTimePostingFailurePage) -> FinancialPostingFailurePageDto:
    return FinancialPostingFailurePageDto(
        items=tuple(
            FinancialPostingFailureDto(
                id=item.id,
                event_id=item.event_id,
                source_id=item.source_id,
                source_revision=item.source_revision,
                resource_id=item.resource_id,
                work_date=item.work_date.isoformat() if item.work_date else "",
                status=item.status,
                failure_code=item.failure_code,
                failure_message=item.failure_message,
                failure_category=item.failure_category,
                corrective_action=item.corrective_action,
                attempt_count=item.attempt_count,
                max_attempts=item.max_attempts,
                retryable=item.retryable,
                updated_at=item.updated_at.isoformat(),
            )
            for item in result.items
        ),
        total=result.total,
        page=result.page,
        page_size=result.page_size,
        sort_key=result.sort_key,
        sort_direction=result.sort_direction,
    )

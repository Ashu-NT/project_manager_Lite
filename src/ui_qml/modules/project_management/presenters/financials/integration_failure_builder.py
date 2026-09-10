from __future__ import annotations

from src.ui_qml.modules.project_management.view_models.financials import (
    FinancialsCollectionViewModel,
    FinancialsRecordViewModel,
)


def build_posting_failure_collection(page) -> FinancialsCollectionViewModel:
    return FinancialsCollectionViewModel(
        title="Approved Time Posting Failures",
        subtitle=(
            "Read-only delivery diagnostics. Correct Time, Rate Card, or Finance "
            "configuration at its authoritative source."
        ),
        empty_state="No approved-time posting failures for this project.",
        items=tuple(
            FinancialsRecordViewModel(
                id=row.id,
                title=f"Time {row.source_id[:12]} | revision {row.source_revision}",
                status_label=row.status.replace("_", " ").title(),
                subtitle=f"{row.failure_category} | {row.failure_code}",
                supporting_text=(
                    f"{'Automatic retry' if row.retryable else 'Operator review'} | "
                    f"attempt {row.attempt_count}/{row.max_attempts}"
                ),
                meta_text=row.work_date or row.updated_at[:10],
                can_primary_action=False,
                can_secondary_action=False,
                state={
                    "eventId": row.event_id,
                    "sourceId": row.source_id,
                    "sourceRevision": row.source_revision,
                    "resourceId": row.resource_id,
                    "workDate": row.work_date,
                    "status": row.status,
                    "failureCode": row.failure_code,
                    "failureMessage": row.failure_message,
                    "failureCategory": row.failure_category,
                    "correctiveAction": row.corrective_action,
                    "attemptCount": row.attempt_count,
                    "maxAttempts": row.max_attempts,
                    "retryable": row.retryable,
                    "updatedAt": row.updated_at,
                },
            )
            for row in page.items
        ),
        page=page.page,
        page_size=page.page_size,
        total=page.total,
    )


__all__ = ["build_posting_failure_collection"]

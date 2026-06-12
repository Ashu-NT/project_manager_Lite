from __future__ import annotations


def generation_result_record(row) -> dict[str, object]:
    target_id = row.generated_work_order_id or row.generated_work_request_id or row.plan_id
    return {
        "id": target_id,
        "title": row.plan_code,
        "subtitle": row.generation_target_label,
        "statusLabel": str(row.generated_task_count),
        "supportingText": (
            f"Work request: {row.generated_work_request_id or '-'} | "
            f"Work order: {row.generated_work_order_id or '-'}"
        ),
        "metaText": (
            f"Steps: {row.generated_step_count} | "
            f"{row.skipped_reason or 'Generation completed successfully.'}"
        ),
        "canPrimaryAction": False,
        "canSecondaryAction": False,
        "canTertiaryAction": False,
        "state": {},
    }

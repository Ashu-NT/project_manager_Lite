from __future__ import annotations

from .generation_result_mapper import generation_result_record


def generate_due_work(desktop_api, *, plan_id: str) -> list[dict]:
    rows = desktop_api.generate_due_work(plan_id=plan_id)
    return [generation_result_record(row) for row in rows]

from __future__ import annotations


def normalize_task_ids(task_ids) -> tuple[str, ...]:
    normalized_ids: list[str] = []
    seen: set[str] = set()
    for task_id in task_ids or ():
        normalized_id = str(task_id or "").strip()
        if not normalized_id or normalized_id in seen:
            continue
        normalized_ids.append(normalized_id)
        seen.add(normalized_id)
    return tuple(normalized_ids)


__all__ = ["normalize_task_ids"]

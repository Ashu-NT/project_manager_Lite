from __future__ import annotations

from dataclasses import dataclass
from typing import Any

@dataclass(frozen=True)
class PagedTaskResult:
    items: tuple[Any, ...]
    total_count: int
    page: int
    page_size: int

def paginate_tasks(tasks: Any, *, page: int, page_size: int) -> PagedTaskResult:
    total_count = len(tasks)
    resolved_page = max(1, page)
    resolved_page_size = max(1, page_size)
    offset = (resolved_page - 1) * resolved_page_size
    return PagedTaskResult(
        items=tasks[offset: offset + resolved_page_size],
        total_count=total_count,
        page=resolved_page,
        page_size=resolved_page_size,
    )

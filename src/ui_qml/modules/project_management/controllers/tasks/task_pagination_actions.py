from __future__ import annotations


def set_task_page(controller, page: int) -> None:
    p = max(1, page)
    if p == controller._task_page:
        return
    controller._set_task_page(p)
    controller.refresh()


def set_task_page_size(controller, page_size: int) -> None:
    if page_size <= 0 or page_size == controller._task_page_size:
        return
    controller._set_task_page_size(page_size)
    controller._set_task_page(1)
    controller.refresh()


def set_task_sort(controller, sort_key: str, sort_direction: int) -> None:
    normalized_key = (sort_key or "").strip()
    if not normalized_key:
        return
    if (
        normalized_key == controller._task_sort_key
        and sort_direction == controller._task_sort_direction
    ):
        return
    controller._set_task_sort_key(normalized_key)
    controller._set_task_sort_direction(sort_direction)
    controller._set_task_page(1)
    controller.refresh()


__all__ = ["set_task_page", "set_task_page_size", "set_task_sort"]

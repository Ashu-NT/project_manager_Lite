from __future__ import annotations


def normalize_page_for_total(*, page: int, page_size: int, total: int) -> int:
    """Clamp an offset page to the final valid page for a known result count."""
    normalized_size = max(1, int(page_size))
    total_pages = max(1, -(-max(0, int(total)) // normalized_size))
    return min(max(1, int(page)), total_pages)


def normalize_offset_for_total(*, offset: int, limit: int, total: int) -> int:
    """Clamp an offset request to the first row of its final valid page."""
    normalized_limit = max(1, int(limit))
    requested_page = (max(0, int(offset)) // normalized_limit) + 1
    normalized_page = normalize_page_for_total(
        page=requested_page,
        page_size=normalized_limit,
        total=total,
    )
    return (normalized_page - 1) * normalized_limit


__all__ = ["normalize_offset_for_total", "normalize_page_for_total"]

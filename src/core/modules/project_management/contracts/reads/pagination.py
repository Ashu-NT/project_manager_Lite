from __future__ import annotations


def normalize_page_for_total(*, page: int, page_size: int, total: int) -> int:
    """Clamp an offset page to the final valid page for a known result count."""
    normalized_size = max(1, int(page_size))
    total_pages = max(1, -(-max(0, int(total)) // normalized_size))
    return min(max(1, int(page)), total_pages)


def normalize_offset_for_total(*, offset: int, limit: int, total: int) -> int:
    """Preserve a valid SQL offset and clamp only past-the-end requests."""
    normalized_limit = max(1, int(limit))
    normalized_offset = max(0, int(offset))
    normalized_total = max(0, int(total))
    if normalized_total == 0:
        return 0
    if normalized_offset < normalized_total:
        return normalized_offset
    return ((normalized_total - 1) // normalized_limit) * normalized_limit


__all__ = ["normalize_offset_for_total", "normalize_page_for_total"]

from __future__ import annotations


def filter_rows(
    rows: list[dict[str, object]],
    search_text: str,
    keys: list[str],
) -> list[dict[str, object]]:
    if not search_text:
        return rows
    term = search_text.lower()
    result = []
    for row in rows:
        for key in keys:
            val = row.get(key)
            if val is not None and term in str(val).lower():
                result.append(row)
                break
    return result


__all__ = ["filter_rows"]

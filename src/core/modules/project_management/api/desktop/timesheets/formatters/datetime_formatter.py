from __future__ import annotations


def format_datetime(value) -> str:
    if value is None:
        return "-"
    return value.strftime("%Y-%m-%d %H:%M")


__all__ = ["format_datetime"]

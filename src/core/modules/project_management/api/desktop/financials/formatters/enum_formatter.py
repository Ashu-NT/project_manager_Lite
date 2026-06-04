"""Enum label formatting helpers."""

from __future__ import annotations


def format_enum_label(value: str) -> str:
    return value.replace("_", " ").title()


__all__ = ["format_enum_label"]

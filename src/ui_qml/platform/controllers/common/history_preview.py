from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TypeVar

from .error_sanitizer import safe_exception_message

_T = TypeVar("_T")
_LOG = logging.getLogger(__name__)


def run_history_preview(
    *,
    operation: Callable[[], list[_T]],
    set_error_message: Callable[[str], None],
    label: str,
) -> list[_T]:
    try:
        result = operation()
    except Exception as exc:
        _LOG.exception("History preview failed: %s", label)
        set_error_message(
            safe_exception_message(exc, fallback="History could not be loaded. Please try again.")
        )
        return []
    set_error_message("")
    return result

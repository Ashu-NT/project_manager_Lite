from __future__ import annotations

import logging

from src.core.platform.common.exceptions import DomainError

logger = logging.getLogger(__name__)

_DEFAULT_SAFE_MESSAGE = "The workspace data could not be loaded. Try again or refresh."


def safe_error_message(
    exc: Exception, *, safe_message: str = _DEFAULT_SAFE_MESSAGE
) -> str:
    """Log the real exception, return a UI-safe message for a read/refresh failure """
    logger.exception("Workspace refresh/read operation failed.")
    if isinstance(exc, DomainError):
        return str(exc)
    return safe_message


__all__ = ["safe_error_message"]

from __future__ import annotations

import functools
from collections.abc import Iterable
from typing import Any

from src.core.platform.auth.authorization import require_any_permission, require_permission


def requires_permission(permission_code: str, *, operation_label: str = "") -> Any:
    """Method decorator that calls require_permission before executing.
    Requires self._user_session on the owner object.
    """
    def decorator(func: Any) -> Any:
        @functools.wraps(func)
        def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
            require_permission(
                getattr(self, "_user_session", None),
                permission_code,
                operation_label=operation_label or func.__name__,
            )
            return func(self, *args, **kwargs)
        return wrapper
    return decorator


def requires_any_permission(permission_codes: Iterable[str], *, operation_label: str = "") -> Any:
    """Decorator form of require_any_permission."""
    def decorator(func: Any) -> Any:
        @functools.wraps(func)
        def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
            require_any_permission(
                getattr(self, "_user_session", None),
                permission_codes,
                operation_label=operation_label or func.__name__,
            )
            return func(self, *args, **kwargs)
        return wrapper
    return decorator


def requires_all_permissions(permission_codes: Iterable[str], *, operation_label: str = "") -> Any:
    """Decorator form — user must hold ALL listed permissions."""
    codes = tuple(permission_codes)

    def decorator(func: Any) -> Any:
        @functools.wraps(func)
        def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
            for code in codes:
                require_permission(
                    getattr(self, "_user_session", None),
                    code,
                    operation_label=operation_label or func.__name__,
                )
            return func(self, *args, **kwargs)
        return wrapper
    return decorator


__all__ = ["requires_all_permissions", "requires_any_permission", "requires_permission"]

from __future__ import annotations

from typing import Any

from src.core.platform.auth.authorization import require_permission


def _require_read(owner: Any, operation_label: str) -> None:
    require_permission(owner._user_session, "inventory.read", operation_label=operation_label)


def _require_manage(owner: Any, operation_label: str) -> None:
    require_permission(owner._user_session, "inventory.manage", operation_label=operation_label)


__all__ = ["_require_manage", "_require_read"]

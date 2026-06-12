from __future__ import annotations

from typing import Any

from src.core.platform.org.domain import Organization


def _active_organization(owner: Any) -> Organization:
    operation_label = getattr(owner, "_catalog_operation_label", "inventory catalog")
    return owner._tenant_context_service.require_context(
        operation_label=operation_label
    ).organization


__all__ = ["_active_organization"]

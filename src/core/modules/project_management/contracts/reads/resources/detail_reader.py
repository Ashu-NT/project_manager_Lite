from __future__ import annotations

from typing import Protocol

from .models import ResourceInspectorFact, ResourceSummaryFact


class ResourceInspectorReader(Protocol):
    def read_inspector(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        resource_id: str,
    ) -> ResourceInspectorFact | None: ...


class ResourceSummaryReader(Protocol):
    def read_summary(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        resource_id: str,
    ) -> ResourceSummaryFact | None: ...


__all__ = ["ResourceInspectorReader", "ResourceSummaryReader"]

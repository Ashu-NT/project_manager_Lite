from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class DocumentCreated:
    tenant_id: str
    organization_id: str
    document_id: str
    occurred_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class DocumentProfileUpdated:
    tenant_id: str
    organization_id: str
    document_id: str
    occurred_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class DocumentStructureCreated:
    tenant_id: str
    organization_id: str
    structure_id: str
    occurred_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class DocumentStructureProfileUpdated:
    tenant_id: str
    organization_id: str
    structure_id: str
    occurred_at: datetime


__all__ = [
    "DocumentCreated",
    "DocumentProfileUpdated",
    "DocumentStructureCreated",
    "DocumentStructureProfileUpdated",
]

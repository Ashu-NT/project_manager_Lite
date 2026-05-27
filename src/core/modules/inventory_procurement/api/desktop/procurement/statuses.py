from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class InventoryProcurementStatusDescriptor:
    value: str
    label: str


__all__ = ["InventoryProcurementStatusDescriptor"]

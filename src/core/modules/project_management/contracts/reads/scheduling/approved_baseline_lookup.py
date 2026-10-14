from __future__ import annotations

from typing import Protocol


class ApprovedBaselineLookup(Protocol):
    def get_approved_baseline(self, project_id: str) -> object | None: ...


__all__ = ["ApprovedBaselineLookup"]

"""Scoped application capability for schedule-impact orchestration."""

from __future__ import annotations

from typing import Protocol


class ApprovedBaselineReference(Protocol):
    @property
    def id(self) -> str: ...


class ApprovedBaselineLookup(Protocol):
    def get_approved_baseline(self, project_id: str) -> ApprovedBaselineReference | None: ...


__all__ = ["ApprovedBaselineLookup", "ApprovedBaselineReference"]

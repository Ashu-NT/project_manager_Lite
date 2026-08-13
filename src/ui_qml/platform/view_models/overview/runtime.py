from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PlatformMetricViewModel:
    label: str
    value: str
    supporting_text: str


@dataclass(frozen=True)
class PlatformRuntimeOverviewViewModel:
    title: str
    subtitle: str
    status_label: str
    metrics: tuple[PlatformMetricViewModel, ...]


__all__ = ["PlatformMetricViewModel", "PlatformRuntimeOverviewViewModel"]

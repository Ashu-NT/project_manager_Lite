from __future__ import annotations

from dataclasses import dataclass

from src.ui_qml.platform.view_models.common.workspace import PlatformMetricViewModel


@dataclass(frozen=True)
class PlatformRuntimeOverviewViewModel:
    title: str
    subtitle: str
    status_label: str
    metrics: tuple[PlatformMetricViewModel, ...]


__all__ = ["PlatformRuntimeOverviewViewModel"]

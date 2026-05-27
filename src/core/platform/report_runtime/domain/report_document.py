from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


ReportFormat = Literal["csv", "excel", "pdf", "png"]


@dataclass(frozen=True)
class MetricRow:
    label: str
    value: object


@dataclass(frozen=True)
class MetricBlock:
    title: str
    rows: tuple[MetricRow, ...]


@dataclass(frozen=True)
class TableBlock:
    title: str
    columns: tuple[str, ...]
    rows: tuple[tuple[object, ...], ...]


@dataclass(frozen=True)
class ChartSeries:
    name: str
    points: tuple[tuple[object, object], ...]


@dataclass(frozen=True)
class ChartBlock:
    title: str
    chart_type: str
    series: tuple[ChartSeries, ...]


@dataclass(frozen=True)
class TextBlock:
    title: str
    body: str


ReportBlock = MetricBlock | TableBlock | ChartBlock | TextBlock


@dataclass(frozen=True)
class ReportSection:
    title: str
    blocks: tuple[ReportBlock, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ReportDocument:
    title: str
    sections: tuple[ReportSection, ...] = field(default_factory=tuple)


__all__ = [
    "ChartBlock",
    "ChartSeries",
    "MetricBlock",
    "MetricRow",
    "ReportDocument",
    "ReportFormat",
    "ReportSection",
    "TableBlock",
    "TextBlock",
]

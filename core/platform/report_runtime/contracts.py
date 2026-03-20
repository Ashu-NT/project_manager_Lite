from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from .models import ReportFormat


class ReportDefinition(Protocol):
    report_key: str
    module_code: str
    permission_code: str
    supported_formats: Sequence[ReportFormat]

    def render(self, request: object) -> object: ...


__all__ = ["ReportDefinition"]

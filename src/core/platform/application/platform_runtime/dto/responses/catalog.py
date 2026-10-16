from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CountryDto:
    code: str
    name: str


@dataclass(frozen=True)
class TimezoneDto:
    name: str

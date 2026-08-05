from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar

_ResultT = TypeVar("_ResultT")


@dataclass(frozen=True)
class DesktopApiError:
    code: str
    message: str
    category: str


@dataclass(frozen=True)
class DesktopApiResult(Generic[_ResultT]):
    ok: bool
    data: _ResultT | None = None
    error: DesktopApiError | None = None

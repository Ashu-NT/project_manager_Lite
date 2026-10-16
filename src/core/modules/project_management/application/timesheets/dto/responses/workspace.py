"""Transport-neutral application response DTOs."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TimesheetWorkspaceAccessResponseDto:
    available_scopes: tuple[str, ...]
    default_scope: str
    mine_resource_id: str = ""
    mine_resource_name: str = ""


@dataclass(frozen=True, slots=True)
class TimesheetResourceResponseDto:
    resource_id: str
    resource_name: str
    resource_code: str
    kind: str
    worker_type: str


@dataclass(frozen=True, slots=True)
class TimesheetResourcePageResponseDto:
    items: tuple[TimesheetResourceResponseDto, ...] = ()
    total: int = 0
    page: int = 1
    page_size: int = 20


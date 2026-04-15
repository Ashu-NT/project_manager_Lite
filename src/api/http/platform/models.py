from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class HttpApiResponse:
    status_code: int
    body: dict[str, Any]


@dataclass(frozen=True)
class ModuleStatePatchRequest:
    module_code: str
    licensed: bool | None = None
    enabled: bool | None = None
    lifecycle_status: str | None = None


@dataclass(frozen=True)
class OrganizationProvisionRequest:
    organization_code: str
    display_name: str
    timezone_name: str
    base_currency: str
    is_active: bool = True
    initial_module_codes: tuple[str, ...] = field(default_factory=tuple)

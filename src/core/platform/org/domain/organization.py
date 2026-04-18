from __future__ import annotations

from dataclasses import dataclass

from core.platform.common.ids import generate_id


@dataclass
class Organization:
    id: str
    organization_code: str
    display_name: str
    timezone_name: str = "UTC"
    base_currency: str = "EUR"
    is_active: bool = True
    version: int = 1

    @staticmethod
    def create(
        organization_code: str,
        display_name: str,
        timezone_name: str = "UTC",
        base_currency: str = "EUR",
        is_active: bool = True,
    ) -> "Organization":
        return Organization(
            id=generate_id(),
            organization_code=organization_code,
            display_name=display_name,
            timezone_name=timezone_name,
            base_currency=base_currency,
            is_active=is_active,
            version=1,
        )


__all__ = ["Organization"]

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone as dt_timezone

from core.platform.common.ids import generate_id


@dataclass
class Department:
    id: str
    organization_id: str
    department_code: str
    name: str
    description: str = ""
    site_id: str | None = None
    default_location_id: str | None = None
    parent_department_id: str | None = None
    department_type: str = ""
    cost_center_code: str = ""
    manager_employee_id: str | None = None
    is_active: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None
    notes: str = ""
    version: int = 1

    @staticmethod
    def create(
        organization_id: str,
        department_code: str,
        name: str,
        *,
        description: str = "",
        site_id: str | None = None,
        default_location_id: str | None = None,
        parent_department_id: str | None = None,
        department_type: str = "",
        cost_center_code: str = "",
        manager_employee_id: str | None = None,
        is_active: bool = True,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
        notes: str = "",
    ) -> "Department":
        now = datetime.now(dt_timezone.utc)
        return Department(
            id=generate_id(),
            organization_id=organization_id,
            department_code=department_code,
            name=name,
            description=description,
            site_id=site_id,
            default_location_id=default_location_id,
            parent_department_id=parent_department_id,
            department_type=department_type,
            cost_center_code=cost_center_code,
            manager_employee_id=manager_employee_id,
            is_active=is_active,
            created_at=created_at or now,
            updated_at=updated_at or now,
            notes=notes,
            version=1,
        )

    @property
    def display_name(self) -> str:
        return self.name

    @display_name.setter
    def display_name(self, value: str) -> None:
        self.name = value


__all__ = ["Department"]

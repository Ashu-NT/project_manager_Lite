from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone

from core.modules.maintenance_management.domain import MaintenanceWorkOrder, MaintenanceWorkOrderTask
from core.modules.maintenance_management.interfaces import (
    MaintenanceWorkOrderRepository,
    MaintenanceWorkOrderTaskRepository,
)
from src.core.platform.org.contracts import EmployeeRepository, OrganizationRepository


@dataclass
class MaintenanceTaskWorkAllocationRecord:
    id: str
    resource_id: str
    hours_logged: float
    owner_type: str
    owner_id: str | None
    owner_label: str
    work_owner_id: str | None
    scope_type: str | None
    scope_id: str | None


@dataclass
class MaintenanceTaskWorkOwnerRecord:
    id: str
    name: str
    scope_type: str | None
    scope_id: str | None
    start_date: date | None = None
    actual_start: date | None = None


@dataclass
class MaintenanceEmployeeWorkResourceRecord:
    id: str
    name: str
    employee_id: str | None


class MaintenanceTaskWorkAllocationRepository:
    def __init__(
        self,
        *,
        organization_repo: OrganizationRepository,
        work_order_task_repo: MaintenanceWorkOrderTaskRepository,
        work_order_repo: MaintenanceWorkOrderRepository,
    ) -> None:
        self._organization_repo = organization_repo
        self._work_order_task_repo = work_order_task_repo
        self._work_order_repo = work_order_repo

    def get(self, work_allocation_id: str) -> MaintenanceTaskWorkAllocationRecord | None:
        task = self._work_order_task_repo.get(work_allocation_id)
        if task is None:
            return None
        work_order = self._work_order_repo.get(task.work_order_id)
        if work_order is None:
            return None
        return self._build_allocation(task, work_order)

    def list_by_resource(self, resource_id: str) -> list[MaintenanceTaskWorkAllocationRecord]:
        organization = self._organization_repo.get_active()
        if organization is None:
            return []
        rows: list[MaintenanceTaskWorkAllocationRecord] = []
        for task in self._work_order_task_repo.list_for_organization(
            organization.id,
            assigned_employee_id=resource_id,
        ):
            work_order = self._work_order_repo.get(task.work_order_id)
            if work_order is None:
                continue
            rows.append(self._build_allocation(task, work_order))
        return rows

    def update(self, work_allocation: MaintenanceTaskWorkAllocationRecord) -> None:
        task = self._work_order_task_repo.get(work_allocation.id)
        if task is None:
            return
        task.actual_minutes = max(0, int(round(float(work_allocation.hours_logged or 0.0) * 60.0)))
        task.updated_at = datetime.now(timezone.utc)
        self._work_order_task_repo.update(task)

    def _build_allocation(
        self,
        task: MaintenanceWorkOrderTask,
        work_order: MaintenanceWorkOrder,
    ) -> MaintenanceTaskWorkAllocationRecord:
        owner_label = f"{work_order.work_order_code} - {task.sequence_no}. {task.task_name}"
        return MaintenanceTaskWorkAllocationRecord(
            id=task.id,
            resource_id=(task.assigned_employee_id or "").strip(),
            hours_logged=float((task.actual_minutes or 0) / 60.0),
            owner_type="maintenance_work_order_task",
            owner_id=task.id,
            owner_label=owner_label,
            work_owner_id=task.id,
            scope_type="maintenance",
            scope_id=self._scope_anchor_for(work_order),
        )

    @staticmethod
    def _scope_anchor_for(work_order: MaintenanceWorkOrder) -> str | None:
        if work_order.asset_id:
            return work_order.asset_id
        if work_order.system_id:
            return work_order.system_id
        if work_order.location_id:
            return work_order.location_id
        return None


class MaintenanceTaskWorkOwnerRepository:
    def __init__(
        self,
        *,
        work_order_task_repo: MaintenanceWorkOrderTaskRepository,
        work_order_repo: MaintenanceWorkOrderRepository,
    ) -> None:
        self._work_order_task_repo = work_order_task_repo
        self._work_order_repo = work_order_repo

    def get(self, owner_id: str) -> MaintenanceTaskWorkOwnerRecord | None:
        task = self._work_order_task_repo.get(owner_id)
        if task is None:
            return None
        work_order = self._work_order_repo.get(task.work_order_id)
        if work_order is None:
            return None
        return MaintenanceTaskWorkOwnerRecord(
            id=task.id,
            name=f"{work_order.work_order_code} - {task.sequence_no}. {task.task_name}",
            scope_type="maintenance",
            scope_id=MaintenanceTaskWorkAllocationRepository._scope_anchor_for(work_order),
            start_date=work_order.planned_start.date() if work_order.planned_start is not None else None,
            actual_start=work_order.actual_start.date() if work_order.actual_start is not None else None,
        )


class MaintenanceEmployeeWorkResourceRepository:
    def __init__(self, *, employee_repo: EmployeeRepository) -> None:
        self._employee_repo = employee_repo

    def get(self, resource_id: str) -> MaintenanceEmployeeWorkResourceRecord | None:
        employee = self._employee_repo.get(resource_id)
        if employee is None:
            return None
        return MaintenanceEmployeeWorkResourceRecord(
            id=employee.id,
            name=employee.full_name,
            employee_id=employee.id,
        )


__all__ = [
    "MaintenanceEmployeeWorkResourceRepository",
    "MaintenanceTaskWorkAllocationRecord",
    "MaintenanceTaskWorkAllocationRepository",
    "MaintenanceTaskWorkOwnerRecord",
    "MaintenanceTaskWorkOwnerRepository",
]

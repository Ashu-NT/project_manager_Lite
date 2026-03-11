from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from core.models import CostType, ProjectStatus, TaskStatus
from core.services.cost import CostService
from core.services.project import ProjectService
from core.services.resource import ResourceService
from core.services.task import TaskService


@dataclass
class ImportSummary:
    entity_type: str
    created_count: int = 0
    updated_count: int = 0
    error_rows: list[str] = field(default_factory=list)

    @property
    def error_count(self) -> int:
        return len(self.error_rows)


class DataImportService:
    def __init__(
        self,
        *,
        project_service: ProjectService,
        task_service: TaskService,
        resource_service: ResourceService,
        cost_service: CostService,
    ) -> None:
        self._project_service = project_service
        self._task_service = task_service
        self._resource_service = resource_service
        self._cost_service = cost_service

    def import_csv(self, entity_type: str, file_path: str | Path) -> ImportSummary:
        normalized = str(entity_type or "").strip().lower()
        rows = self._load_csv_rows(file_path)
        if normalized == "projects":
            return self._import_projects(rows)
        if normalized == "resources":
            return self._import_resources(rows)
        if normalized == "tasks":
            return self._import_tasks(rows)
        if normalized == "costs":
            return self._import_costs(rows)
        raise ValueError(f"Unsupported import type: {entity_type}")

    def _import_projects(self, rows: list[tuple[int, dict[str, str]]]) -> ImportSummary:
        summary = ImportSummary(entity_type="projects")
        existing = self._project_lookup()
        for line_no, row in rows:
            try:
                project_id = row.get("id") or None
                name = self._required(row, "name")
                project = self._resolve_project(existing, project_id=project_id, project_name=name)
                payload = {
                    "name": name,
                    "description": row.get("description", ""),
                    "client_name": row.get("client_name") or None,
                    "client_contact": row.get("client_contact") or None,
                    "planned_budget": self._optional_float(row.get("planned_budget")),
                    "currency": row.get("currency") or None,
                    "start_date": self._optional_date(row.get("start_date")),
                    "end_date": self._optional_date(row.get("end_date")),
                }
                status = self._optional_project_status(row.get("status"))
                if project is None:
                    created = self._project_service.create_project(**payload)
                    if status is not None and status != ProjectStatus.PLANNED:
                        self._project_service.set_status(created.id, status)
                    summary.created_count += 1
                else:
                    self._project_service.update_project(
                        project.id,
                        expected_version=project.version,
                        status=status,
                        **payload,
                    )
                    summary.updated_count += 1
                existing = self._project_lookup()
            except Exception as exc:
                summary.error_rows.append(f"line {line_no}: {exc}")
        return summary

    def _import_resources(self, rows: list[tuple[int, dict[str, str]]]) -> ImportSummary:
        summary = ImportSummary(entity_type="resources")
        existing = {
            resource.id: resource for resource in self._resource_service.list_resources()
        }
        existing_by_name = {
            resource.name.strip().lower(): resource for resource in self._resource_service.list_resources()
        }
        for line_no, row in rows:
            try:
                resource = existing.get(row.get("id") or "") or existing_by_name.get(
                    self._required(row, "name").strip().lower()
                )
                payload = {
                    "name": self._required(row, "name"),
                    "role": row.get("role", ""),
                    "hourly_rate": self._optional_float(row.get("hourly_rate")) or 0.0,
                    "is_active": self._optional_bool(row.get("is_active"), default=True),
                    "cost_type": self._optional_cost_type(row.get("cost_type")) or CostType.LABOR,
                    "currency_code": row.get("currency_code") or None,
                    "capacity_percent": self._optional_float(row.get("capacity_percent")) or 100.0,
                    "address": row.get("address", ""),
                    "contact": row.get("contact", ""),
                }
                if resource is None:
                    self._resource_service.create_resource(**payload)
                    summary.created_count += 1
                else:
                    self._resource_service.update_resource(
                        resource.id,
                        expected_version=resource.version,
                        **payload,
                    )
                    summary.updated_count += 1
                existing = {
                    current.id: current for current in self._resource_service.list_resources()
                }
                existing_by_name = {
                    current.name.strip().lower(): current
                    for current in self._resource_service.list_resources()
                }
            except Exception as exc:
                summary.error_rows.append(f"line {line_no}: {exc}")
        return summary

    def _import_tasks(self, rows: list[tuple[int, dict[str, str]]]) -> ImportSummary:
        summary = ImportSummary(entity_type="tasks")
        projects = self._project_lookup()
        for line_no, row in rows:
            try:
                project = self._resolve_project(
                    projects,
                    project_id=row.get("project_id") or None,
                    project_name=row.get("project_name") or None,
                )
                if project is None:
                    raise ValueError("Project reference is required via project_id or project_name.")
                name = self._required(row, "name")
                tasks = self._task_service.list_tasks_for_project(project.id)
                task = None
                task_id = row.get("id") or ""
                if task_id:
                    task = next((item for item in tasks if item.id == task_id), None)
                if task is None:
                    task = next((item for item in tasks if item.name.strip().lower() == name.strip().lower()), None)
                payload = {
                    "name": name,
                    "description": row.get("description", ""),
                    "start_date": self._optional_date(row.get("start_date")),
                    "duration_days": self._optional_int(row.get("duration_days")),
                    "priority": self._optional_int(row.get("priority")) or 0,
                    "deadline": self._optional_date(row.get("deadline")),
                }
                status = self._optional_task_status(row.get("status"))
                percent_complete = self._optional_float(row.get("percent_complete"))
                if task is None:
                    created = self._task_service.create_task(
                        project.id,
                        status=status or TaskStatus.TODO,
                        **payload,
                    )
                    if percent_complete is not None:
                        self._task_service.update_progress(created.id, percent_complete=percent_complete)
                    summary.created_count += 1
                else:
                    updated = self._task_service.update_task(
                        task.id,
                        expected_version=task.version,
                        status=status,
                        **payload,
                    )
                    if percent_complete is not None:
                        self._task_service.update_progress(
                            updated.id,
                            percent_complete=percent_complete,
                            expected_version=updated.version,
                        )
                    summary.updated_count += 1
            except Exception as exc:
                summary.error_rows.append(f"line {line_no}: {exc}")
        return summary

    def _import_costs(self, rows: list[tuple[int, dict[str, str]]]) -> ImportSummary:
        summary = ImportSummary(entity_type="costs")
        projects = self._project_lookup()
        for line_no, row in rows:
            try:
                project = self._resolve_project(
                    projects,
                    project_id=row.get("project_id") or None,
                    project_name=row.get("project_name") or None,
                )
                if project is None:
                    raise ValueError("Project reference is required via project_id or project_name.")
                task = self._resolve_task(
                    project_id=project.id,
                    task_id=row.get("task_id") or None,
                    task_name=row.get("task_name") or None,
                )
                existing = self._resolve_cost(project_id=project.id, cost_id=row.get("id") or None)
                payload = {
                    "description": self._required(row, "description"),
                    "planned_amount": self._optional_float(row.get("planned_amount")) or 0.0,
                    "committed_amount": self._optional_float(row.get("committed_amount")) or 0.0,
                    "actual_amount": self._optional_float(row.get("actual_amount")) or 0.0,
                    "cost_type": self._optional_cost_type(row.get("cost_type")) or CostType.OVERHEAD,
                    "currency_code": row.get("currency_code") or None,
                    "incurred_date": self._optional_date(row.get("incurred_date")),
                }
                if existing is None:
                    self._cost_service.add_cost_item(
                        project_id=project.id,
                        task_id=task.id if task is not None else None,
                        **payload,
                    )
                    summary.created_count += 1
                else:
                    self._cost_service.update_cost_item(
                        existing.id,
                        expected_version=existing.version,
                        **payload,
                    )
                    summary.updated_count += 1
            except Exception as exc:
                summary.error_rows.append(f"line {line_no}: {exc}")
        return summary

    @staticmethod
    def _load_csv_rows(file_path: str | Path) -> list[tuple[int, dict[str, str]]]:
        path = Path(file_path)
        rows: list[tuple[int, dict[str, str]]] = []
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            for idx, raw in enumerate(reader, start=2):
                normalized = {
                    str(key or "").strip().lower(): str(value or "").strip()
                    for key, value in (raw or {}).items()
                    if str(key or "").strip()
                }
                if any(normalized.values()):
                    rows.append((idx, normalized))
        return rows

    def _project_lookup(self) -> dict[str, object]:
        lookup: dict[str, object] = {}
        for project in self._project_service.list_projects():
            lookup[project.id] = project
            lookup[project.name.strip().lower()] = project
        return lookup

    @staticmethod
    def _resolve_project(lookup: dict[str, object], *, project_id: str | None, project_name: str | None):
        if project_id and project_id in lookup:
            return lookup[project_id]
        key = (project_name or "").strip().lower()
        return lookup.get(key) if key else None

    def _resolve_task(self, *, project_id: str, task_id: str | None, task_name: str | None):
        tasks = self._task_service.list_tasks_for_project(project_id)
        if task_id:
            found = next((task for task in tasks if task.id == task_id), None)
            if found is not None:
                return found
        if task_name:
            key = task_name.strip().lower()
            return next((task for task in tasks if task.name.strip().lower() == key), None)
        return None

    def _resolve_cost(self, *, project_id: str, cost_id: str | None):
        if not cost_id:
            return None
        return next(
            (item for item in self._cost_service.list_cost_items_for_project(project_id) if item.id == cost_id),
            None,
        )

    @staticmethod
    def _required(row: dict[str, str], key: str) -> str:
        value = (row.get(key) or "").strip()
        if not value:
            raise ValueError(f"Missing required column '{key}'.")
        return value

    @staticmethod
    def _optional_date(value: str | None) -> date | None:
        text = str(value or "").strip()
        return date.fromisoformat(text) if text else None

    @staticmethod
    def _optional_int(value: str | None) -> int | None:
        text = str(value or "").strip()
        return int(text) if text else None

    @staticmethod
    def _optional_float(value: str | None) -> float | None:
        text = str(value or "").strip()
        return float(text) if text else None

    @staticmethod
    def _optional_bool(value: str | None, *, default: bool) -> bool:
        text = str(value or "").strip().lower()
        if not text:
            return default
        return text in {"1", "true", "yes", "y", "on"}

    @staticmethod
    def _optional_project_status(value: str | None) -> ProjectStatus | None:
        text = str(value or "").strip().upper()
        return ProjectStatus(text) if text else None

    @staticmethod
    def _optional_task_status(value: str | None) -> TaskStatus | None:
        text = str(value or "").strip().upper()
        return TaskStatus(text) if text else None

    @staticmethod
    def _optional_cost_type(value: str | None) -> CostType | None:
        text = str(value or "").strip().upper()
        return CostType(text) if text else None


__all__ = ["DataImportService", "ImportSummary"]

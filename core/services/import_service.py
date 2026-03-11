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


@dataclass(frozen=True)
class ImportFieldSpec:
    key: str
    label: str
    required: bool = False


@dataclass
class ImportPreviewRow:
    line_no: int
    status: str
    action: str
    message: str
    row: dict[str, str] = field(default_factory=dict)


@dataclass
class ImportPreview:
    entity_type: str
    available_columns: list[str]
    mapped_columns: dict[str, str | None]
    rows: list[ImportPreviewRow] = field(default_factory=list)
    created_count: int = 0
    updated_count: int = 0

    @property
    def error_count(self) -> int:
        return sum(1 for row in self.rows if row.status == "ERROR")

    @property
    def ready_count(self) -> int:
        return sum(1 for row in self.rows if row.status == "READY")


class DataImportService:
    _SCHEMAS: dict[str, tuple[ImportFieldSpec, ...]] = {
        "projects": (
            ImportFieldSpec("id", "Project ID"),
            ImportFieldSpec("name", "Name", required=True),
            ImportFieldSpec("description", "Description"),
            ImportFieldSpec("client_name", "Client"),
            ImportFieldSpec("client_contact", "Client Contact"),
            ImportFieldSpec("planned_budget", "Planned Budget"),
            ImportFieldSpec("currency", "Currency"),
            ImportFieldSpec("start_date", "Start Date"),
            ImportFieldSpec("end_date", "End Date"),
            ImportFieldSpec("status", "Status"),
        ),
        "resources": (
            ImportFieldSpec("id", "Resource ID"),
            ImportFieldSpec("name", "Name", required=True),
            ImportFieldSpec("role", "Role"),
            ImportFieldSpec("hourly_rate", "Hourly Rate"),
            ImportFieldSpec("is_active", "Active"),
            ImportFieldSpec("cost_type", "Cost Type"),
            ImportFieldSpec("currency_code", "Currency"),
            ImportFieldSpec("capacity_percent", "Capacity %"),
            ImportFieldSpec("address", "Address"),
            ImportFieldSpec("contact", "Contact"),
        ),
        "tasks": (
            ImportFieldSpec("id", "Task ID"),
            ImportFieldSpec("project_id", "Project ID"),
            ImportFieldSpec("project_name", "Project Name"),
            ImportFieldSpec("name", "Task Name", required=True),
            ImportFieldSpec("description", "Description"),
            ImportFieldSpec("start_date", "Start Date"),
            ImportFieldSpec("duration_days", "Duration Days"),
            ImportFieldSpec("priority", "Priority"),
            ImportFieldSpec("deadline", "Deadline"),
            ImportFieldSpec("status", "Status"),
            ImportFieldSpec("percent_complete", "Percent Complete"),
        ),
        "costs": (
            ImportFieldSpec("id", "Cost ID"),
            ImportFieldSpec("project_id", "Project ID"),
            ImportFieldSpec("project_name", "Project Name"),
            ImportFieldSpec("task_id", "Task ID"),
            ImportFieldSpec("task_name", "Task Name"),
            ImportFieldSpec("description", "Description", required=True),
            ImportFieldSpec("planned_amount", "Planned Amount"),
            ImportFieldSpec("committed_amount", "Committed Amount"),
            ImportFieldSpec("actual_amount", "Actual Amount"),
            ImportFieldSpec("cost_type", "Cost Type"),
            ImportFieldSpec("currency_code", "Currency"),
            ImportFieldSpec("incurred_date", "Incurred Date"),
        ),
    }

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

    def get_import_schema(self, entity_type: str) -> tuple[ImportFieldSpec, ...]:
        normalized = self._normalize_entity_type(entity_type)
        return self._SCHEMAS[normalized]

    def read_csv_columns(self, file_path: str | Path) -> list[str]:
        columns, _ = self._load_csv_source(file_path)
        return columns

    def preview_csv(
        self,
        entity_type: str,
        file_path: str | Path,
        *,
        column_mapping: dict[str, str | None] | None = None,
        max_rows: int = 100,
    ) -> ImportPreview:
        normalized = self._normalize_entity_type(entity_type)
        columns, rows, mapping = self._prepare_rows(
            normalized,
            file_path,
            column_mapping=column_mapping,
        )
        handlers = {
            "projects": self._preview_projects,
            "resources": self._preview_resources,
            "tasks": self._preview_tasks,
            "costs": self._preview_costs,
        }
        preview = handlers[normalized](rows[: max(1, int(max_rows))])
        preview.entity_type = normalized
        preview.available_columns = columns
        preview.mapped_columns = mapping
        return preview

    def import_csv(
        self,
        entity_type: str,
        file_path: str | Path,
        *,
        column_mapping: dict[str, str | None] | None = None,
    ) -> ImportSummary:
        normalized = self._normalize_entity_type(entity_type)
        _columns, rows, _mapping = self._prepare_rows(
            normalized,
            file_path,
            column_mapping=column_mapping,
        )
        if normalized == "projects":
            return self._import_projects(rows)
        if normalized == "resources":
            return self._import_resources(rows)
        if normalized == "tasks":
            return self._import_tasks(rows)
        if normalized == "costs":
            return self._import_costs(rows)
        raise ValueError(f"Unsupported import type: {entity_type}")

    def _normalize_entity_type(self, entity_type: str) -> str:
        normalized = str(entity_type or "").strip().lower()
        if normalized not in self._SCHEMAS:
            raise ValueError(f"Unsupported import type: {entity_type}")
        return normalized

    def _prepare_rows(
        self,
        entity_type: str,
        file_path: str | Path,
        *,
        column_mapping: dict[str, str | None] | None,
    ) -> tuple[list[str], list[tuple[int, dict[str, str]]], dict[str, str | None]]:
        columns, raw_rows = self._load_csv_source(file_path)
        mapping = self._effective_mapping(entity_type, columns, column_mapping)
        rows = [
            (
                line_no,
                {
                    key: str(raw.get(source or "", "") or "").strip() if source else ""
                    for key, source in mapping.items()
                },
            )
            for line_no, raw in raw_rows
        ]
        return columns, rows, mapping

    def _effective_mapping(
        self,
        entity_type: str,
        available_columns: list[str],
        mapping: dict[str, str | None] | None,
    ) -> dict[str, str | None]:
        normalized_input = {
            str(key or "").strip().lower(): (
                str(value or "").strip().lower() if value not in (None, "") else None
            )
            for key, value in (mapping or {}).items()
        }
        available = {column.lower() for column in available_columns}
        resolved: dict[str, str | None] = {}
        for field in self.get_import_schema(entity_type):
            selected = normalized_input.get(field.key)
            if selected is None and field.key in available:
                selected = field.key
            resolved[field.key] = selected if selected in available else None
        return resolved

    def _preview_projects(self, rows: list[tuple[int, dict[str, str]]]) -> ImportPreview:
        preview = ImportPreview(entity_type="projects", available_columns=[], mapped_columns={})
        existing = self._project_lookup()
        for line_no, row in rows:
            try:
                name = self._required(row, "name")
                project = self._resolve_project(
                    existing,
                    project_id=row.get("id") or None,
                    project_name=name,
                )
                self._optional_float(row.get("planned_budget"))
                self._optional_date(row.get("start_date"))
                self._optional_date(row.get("end_date"))
                self._optional_project_status(row.get("status"))
                action = "UPDATE" if project is not None else "CREATE"
                preview.rows.append(
                    ImportPreviewRow(
                        line_no=line_no,
                        status="READY",
                        action=action,
                        message=f"Ready to {action.lower()} project '{name}'.",
                        row=row,
                    )
                )
                if action == "CREATE":
                    preview.created_count += 1
                else:
                    preview.updated_count += 1
            except Exception as exc:
                preview.rows.append(
                    ImportPreviewRow(line_no=line_no, status="ERROR", action="ERROR", message=str(exc), row=row)
                )
        return preview

    def _preview_resources(self, rows: list[tuple[int, dict[str, str]]]) -> ImportPreview:
        preview = ImportPreview(entity_type="resources", available_columns=[], mapped_columns={})
        existing = {resource.id: resource for resource in self._resource_service.list_resources()}
        existing_by_name = {
            resource.name.strip().lower(): resource for resource in self._resource_service.list_resources()
        }
        for line_no, row in rows:
            try:
                name = self._required(row, "name")
                resource = existing.get(row.get("id") or "") or existing_by_name.get(name.strip().lower())
                self._optional_float(row.get("hourly_rate"))
                self._optional_float(row.get("capacity_percent"))
                self._optional_bool(row.get("is_active"), default=True)
                self._optional_cost_type(row.get("cost_type"))
                action = "UPDATE" if resource is not None else "CREATE"
                preview.rows.append(
                    ImportPreviewRow(
                        line_no=line_no,
                        status="READY",
                        action=action,
                        message=f"Ready to {action.lower()} resource '{name}'.",
                        row=row,
                    )
                )
                if action == "CREATE":
                    preview.created_count += 1
                else:
                    preview.updated_count += 1
            except Exception as exc:
                preview.rows.append(
                    ImportPreviewRow(line_no=line_no, status="ERROR", action="ERROR", message=str(exc), row=row)
                )
        return preview

    def _preview_tasks(self, rows: list[tuple[int, dict[str, str]]]) -> ImportPreview:
        preview = ImportPreview(entity_type="tasks", available_columns=[], mapped_columns={})
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
                task_id = row.get("id") or ""
                task = next((item for item in tasks if item.id == task_id), None) if task_id else None
                if task is None:
                    task = next((item for item in tasks if item.name.strip().lower() == name.strip().lower()), None)
                self._optional_date(row.get("start_date"))
                self._optional_int(row.get("duration_days"))
                self._optional_int(row.get("priority"))
                self._optional_date(row.get("deadline"))
                self._optional_task_status(row.get("status"))
                self._optional_float(row.get("percent_complete"))
                action = "UPDATE" if task is not None else "CREATE"
                preview.rows.append(
                    ImportPreviewRow(
                        line_no=line_no,
                        status="READY",
                        action=action,
                        message=f"Ready to {action.lower()} task '{name}' in '{project.name}'.",
                        row=row,
                    )
                )
                if action == "CREATE":
                    preview.created_count += 1
                else:
                    preview.updated_count += 1
            except Exception as exc:
                preview.rows.append(
                    ImportPreviewRow(line_no=line_no, status="ERROR", action="ERROR", message=str(exc), row=row)
                )
        return preview

    def _preview_costs(self, rows: list[tuple[int, dict[str, str]]]) -> ImportPreview:
        preview = ImportPreview(entity_type="costs", available_columns=[], mapped_columns={})
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
                self._resolve_task(
                    project_id=project.id,
                    task_id=row.get("task_id") or None,
                    task_name=row.get("task_name") or None,
                )
                existing = self._resolve_cost(project_id=project.id, cost_id=row.get("id") or None)
                label = self._required(row, "description")
                self._optional_float(row.get("planned_amount"))
                self._optional_float(row.get("committed_amount"))
                self._optional_float(row.get("actual_amount"))
                self._optional_cost_type(row.get("cost_type"))
                self._optional_date(row.get("incurred_date"))
                action = "UPDATE" if existing is not None else "CREATE"
                preview.rows.append(
                    ImportPreviewRow(
                        line_no=line_no,
                        status="READY",
                        action=action,
                        message=f"Ready to {action.lower()} cost '{label}' in '{project.name}'.",
                        row=row,
                    )
                )
                if action == "CREATE":
                    preview.created_count += 1
                else:
                    preview.updated_count += 1
            except Exception as exc:
                preview.rows.append(
                    ImportPreviewRow(line_no=line_no, status="ERROR", action="ERROR", message=str(exc), row=row)
                )
        return preview

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
        existing = {resource.id: resource for resource in self._resource_service.list_resources()}
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
                existing = {current.id: current for current in self._resource_service.list_resources()}
                existing_by_name = {
                    current.name.strip().lower(): current for current in self._resource_service.list_resources()
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
    def _load_csv_source(file_path: str | Path) -> tuple[list[str], list[tuple[int, dict[str, str]]]]:
        path = Path(file_path)
        rows: list[tuple[int, dict[str, str]]] = []
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            columns = [str(field or "").strip().lower() for field in (reader.fieldnames or []) if str(field or "").strip()]
            for idx, raw in enumerate(reader, start=2):
                normalized = {
                    str(key or "").strip().lower(): str(value or "").strip()
                    for key, value in (raw or {}).items()
                    if str(key or "").strip()
                }
                if any(normalized.values()):
                    rows.append((idx, normalized))
        return columns, rows

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


__all__ = [
    "DataImportService",
    "ImportFieldSpec",
    "ImportPreview",
    "ImportPreviewRow",
    "ImportSummary",
]

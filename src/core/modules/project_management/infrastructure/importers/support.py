from __future__ import annotations

import csv
from datetime import date
from pathlib import Path
from typing import Any

from core.modules.project_management.domain.enums import CostType, ProjectStatus, TaskStatus
from src.core.modules.project_management.application.financials import CostService
from src.core.modules.project_management.application.projects import ProjectService
from src.core.modules.project_management.application.resources import ResourceService
from src.core.modules.project_management.application.tasks import TaskService
from src.core.modules.project_management.infrastructure.importers.models import (
    ImportFieldSpec,
)


class DataImportSupportMixin:
    _SCHEMAS: dict[str, tuple[ImportFieldSpec, ...]]
    _project_service: ProjectService
    _task_service: TaskService
    _resource_service: ResourceService
    _cost_service: CostService

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

    @staticmethod
    def _load_csv_source(file_path: str | Path) -> tuple[list[str], list[tuple[int, dict[str, str]]]]:
        path = Path(file_path)
        rows: list[tuple[int, dict[str, str]]] = []
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            columns = [
                str(field or "").strip().lower()
                for field in (reader.fieldnames or [])
                if str(field or "").strip()
            ]
            for idx, raw in enumerate(reader, start=2):
                normalized = {
                    str(key or "").strip().lower(): str(value or "").strip()
                    for key, value in (raw or {}).items()
                    if str(key or "").strip()
                }
                if any(normalized.values()):
                    rows.append((idx, normalized))
        return columns, rows

    def _project_lookup(self) -> dict[str, Any]:
        lookup: dict[str, Any] = {}
        for project in self._project_service.list_projects():
            lookup[project.id] = project
            lookup[project.name.strip().lower()] = project
        return lookup

    @staticmethod
    def _resolve_project(lookup: dict[str, Any], *, project_id: str | None, project_name: str | None):
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


__all__ = ["DataImportSupportMixin"]

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from src.api.desktop.platform._support import execute_desktop_operation
from src.api.desktop.platform.models import AuditLogEntryDto, DesktopApiResult
from src.core.platform.audit import AuditService
from src.core.platform.audit.domain import AuditLogEntry
from core.modules.project_management.services.baseline import BaselineService
from core.modules.project_management.services.cost import CostService
from src.core.modules.project_management.application.projects import ProjectService
from core.modules.project_management.services.resource import ResourceService
from src.core.modules.project_management.application.tasks import TaskService


@dataclass(frozen=True)
class _AuditReferenceMaps:
    project_name_by_id: dict[str, str] = field(default_factory=dict)
    task_name_by_id: dict[str, str] = field(default_factory=dict)
    resource_name_by_id: dict[str, str] = field(default_factory=dict)
    cost_label_by_id: dict[str, str] = field(default_factory=dict)
    baseline_name_by_id: dict[str, str] = field(default_factory=dict)


class PlatformAuditDesktopApi:
    """Desktop-facing adapter for governance audit-log flows."""

    def __init__(
        self,
        *,
        audit_service: AuditService,
        project_service: ProjectService | None = None,
        task_service: TaskService | None = None,
        resource_service: ResourceService | None = None,
        cost_service: CostService | None = None,
        baseline_service: BaselineService | None = None,
    ) -> None:
        self._audit_service = audit_service
        self._project_service = project_service
        self._task_service = task_service
        self._resource_service = resource_service
        self._cost_service = cost_service
        self._baseline_service = baseline_service

    def list_recent(
        self,
        *,
        limit: int = 1000,
        project_id: str | None = None,
        entity_type: str | None = None,
    ) -> DesktopApiResult[tuple[AuditLogEntryDto, ...]]:
        return execute_desktop_operation(
            lambda: self._serialize_entries(
                self._audit_service.list_recent(
                    limit=limit,
                    project_id=project_id,
                    entity_type=entity_type,
                )
            )
        )

    def _serialize_entries(self, entries: list[AuditLogEntry]) -> tuple[AuditLogEntryDto, ...]:
        references = self._build_reference_maps()
        return tuple(self._serialize_entry(entry, references) for entry in entries)

    def _build_reference_maps(self) -> _AuditReferenceMaps:
        project_name_by_id: dict[str, str] = {}
        task_name_by_id: dict[str, str] = {}
        resource_name_by_id: dict[str, str] = {}
        cost_label_by_id: dict[str, str] = {}
        baseline_name_by_id: dict[str, str] = {}

        projects = self._safe_list_projects()
        for project in projects:
            project_name_by_id[project.id] = project.name

        if self._task_service is not None:
            for project in projects:
                for task in self._safe_list_tasks(project.id):
                    task_name_by_id[task.id] = task.name

        if self._resource_service is not None:
            for resource in self._safe_list_resources():
                resource_name_by_id[resource.id] = resource.name

        if self._cost_service is not None:
            for project in projects:
                for item in self._safe_list_cost_items(project.id):
                    cost_label_by_id[item.id] = item.description

        if self._baseline_service is not None:
            for project in projects:
                for baseline in self._safe_list_baselines(project.id):
                    baseline_name_by_id[baseline.id] = baseline.name

        return _AuditReferenceMaps(
            project_name_by_id=project_name_by_id,
            task_name_by_id=task_name_by_id,
            resource_name_by_id=resource_name_by_id,
            cost_label_by_id=cost_label_by_id,
            baseline_name_by_id=baseline_name_by_id,
        )

    def _serialize_entry(
        self,
        entry: AuditLogEntry,
        references: _AuditReferenceMaps,
    ) -> AuditLogEntryDto:
        project_label = references.project_name_by_id.get(entry.project_id or "", entry.project_id or "-")
        return AuditLogEntryDto(
            id=entry.id,
            occurred_at=entry.occurred_at,
            actor_user_id=entry.actor_user_id,
            actor_username=entry.actor_username,
            action=entry.action,
            entity_type=entry.entity_type,
            entity_id=entry.entity_id,
            project_id=entry.project_id,
            details=dict(entry.details or {}),
            project_label=project_label or (entry.project_id or "-"),
            entity_label=self._entity_label(entry),
            details_label=self._details_label(entry, references),
        )

    def _details_label(self, entry: AuditLogEntry, references: _AuditReferenceMaps) -> str:
        details = entry.details or {}
        if not details:
            return "-"
        pairs: list[str] = []
        for key in sorted(details):
            if key.endswith("_id") and f"{key[:-3]}_name" in details:
                continue
            value = self._resolve_detail_value(entry, key, details[key], references)
            if value in {"", None}:
                continue
            label_key = key.replace("_name", "").replace("_id", "").replace("_", " ")
            pairs.append(f"{label_key}={value}")
        if not pairs:
            return "-"
        text = ", ".join(pairs)
        return text if len(text) <= 200 else f"{text[:197]}..."

    def _resolve_detail_value(
        self,
        entry: AuditLogEntry,
        key: str,
        value: Any,
        references: _AuditReferenceMaps,
    ) -> str:
        raw = str(value).strip() if value is not None else ""
        if key.endswith("_name"):
            return raw
        if not key.endswith("_id"):
            return raw
        if not raw:
            return ""
        if key in {"task_id", "predecessor_id", "successor_id"}:
            return references.task_name_by_id.get(raw, raw)
        if key == "project_id":
            return references.project_name_by_id.get(raw, raw)
        if key == "resource_id":
            return references.resource_name_by_id.get(raw, raw)
        if key == "cost_id":
            return references.cost_label_by_id.get(raw, raw)
        if key == "baseline_id":
            return references.baseline_name_by_id.get(raw, raw)
        if key == "entity_id":
            if entry.entity_type == "task":
                return references.task_name_by_id.get(raw, raw)
            if entry.entity_type == "project":
                return references.project_name_by_id.get(raw, raw)
            if entry.entity_type == "resource":
                return references.resource_name_by_id.get(raw, raw)
            if entry.entity_type == "cost_item":
                return references.cost_label_by_id.get(raw, raw)
            if entry.entity_type == "project_baseline":
                return references.baseline_name_by_id.get(raw, raw)
        return raw

    @staticmethod
    def _entity_label(entry: AuditLogEntry) -> str:
        entity = entry.entity_type.replace("_", " ").title()
        request_type = str((entry.details or {}).get("request_type") or "").strip()
        if request_type:
            return f"{entity} ({request_type})"
        return entity

    def _safe_list_projects(self) -> list[object]:
        if self._project_service is None:
            return []
        try:
            return list(self._project_service.list_projects())
        except Exception:
            return []

    def _safe_list_tasks(self, project_id: str) -> list[object]:
        if self._task_service is None:
            return []
        try:
            return list(self._task_service.list_tasks_for_project(project_id))
        except Exception:
            return []

    def _safe_list_resources(self) -> list[object]:
        if self._resource_service is None:
            return []
        try:
            return list(self._resource_service.list_resources())
        except Exception:
            return []

    def _safe_list_cost_items(self, project_id: str) -> list[object]:
        if self._cost_service is None:
            return []
        try:
            return list(self._cost_service.list_cost_items_for_project(project_id))
        except Exception:
            return []

    def _safe_list_baselines(self, project_id: str) -> list[object]:
        if self._baseline_service is None:
            return []
        try:
            return list(self._baseline_service.list_baselines(project_id))
        except Exception:
            return []


__all__ = ["PlatformAuditDesktopApi"]

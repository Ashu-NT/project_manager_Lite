from __future__ import annotations

from src.core.modules.project_management.domain.enums import CostType, ProjectStatus, TaskStatus

from src.core.modules.project_management.infrastructure.importers.models import ImportSummary


class DataImportExecutionMixin:
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
                summary.add_row_error(line_no=line_no, message=str(exc))
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
                summary.add_row_error(line_no=line_no, message=str(exc))
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
                summary.add_row_error(line_no=line_no, message=str(exc))
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
                summary.add_row_error(line_no=line_no, message=str(exc))
        return summary


__all__ = ["DataImportExecutionMixin"]

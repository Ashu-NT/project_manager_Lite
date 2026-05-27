from __future__ import annotations

from src.core.modules.project_management.infrastructure.importers.models import ImportPreview, ImportPreviewRow


class DataImportPreviewMixin:
    def _preview_projects(self, rows: list[tuple[int, dict[str, str]]]) -> ImportPreview:
        preview = ImportPreview(entity_type="projects", available_columns=[], mapped_columns={})
        existing = self._project_lookup()
        for line_no, row in rows:
            try:
                name = self._required(row, "name")
                project = self._resolve_project(existing, project_id=row.get("id") or None, project_name=name)
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


__all__ = ["DataImportPreviewMixin"]

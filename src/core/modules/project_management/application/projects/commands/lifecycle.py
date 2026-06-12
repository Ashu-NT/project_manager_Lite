from __future__ import annotations

import logging
from datetime import date

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.core.modules.project_management.application.projects.commands.validation import (
    ProjectValidationMixin,
)
from src.core.modules.project_management.contracts.repositories.cost_calendar import (
    CalendarEventRepository,
    CostRepository,
)
from src.core.modules.project_management.contracts.repositories.project import ProjectRepository
from src.core.modules.project_management.contracts.repositories.task import (
    AssignmentRepository,
    DependencyRepository,
    TaskRepository,
)
from src.core.modules.project_management.domain.projects.project import Project
from src.core.platform.access.authorization import require_project_permission
from src.core.platform.audit.helpers import record_audit
from src.core.platform.auth.authorization import require_permission
from src.core.platform.common.exceptions import BusinessRuleError, ConcurrencyError, NotFoundError, ValidationError
from src.core.platform.common.interfaces import TimeEntryRepository
from src.core.shared.events.domain_events import domain_events
from src.core.modules.project_management.domain.enums import ProjectStatus

logger = logging.getLogger(__name__)
DEFAULT_CURRENCY_CODE = "EUR"


class ProjectLifecycleMixin(ProjectValidationMixin):
    _session: Session
    _project_repo: ProjectRepository
    _task_repo: TaskRepository
    _dependency_repo: DependencyRepository
    _assignment_repo: AssignmentRepository
    _time_entry_repo: TimeEntryRepository | None
    _calendar_repo: CalendarEventRepository
    _cost_repo: CostRepository

    def _resolve_project_code(
        self,
        code: str,
        name: str,
        *,
        exclude_id: str | None = None,
        organization_id: str | None = None,
    ) -> str:
        """Normalize a manual code or auto-generate a unique code."""
        from src.core.platform.common.code_generation import (
            CodeGenerator,
            assert_code_unique,
            normalize_manual_code,
        )

        if not organization_id:
            raise BusinessRuleError(
                "Active organization context is required for project code generation.",
                code="TENANT_CONTEXT_REQUIRED",
            )
        project_rows = self._project_repo.list_for_organization(organization_id)
        existing = {
            str(getattr(project, "code", "") or "").upper()
            for project in project_rows
            if exclude_id is None or project.id != exclude_id
        }
        manual = normalize_manual_code(code)
        if manual:
            assert_code_unique(
                manual,
                exists=lambda candidate: candidate.upper() in existing,
                label="Project code",
            )
            return manual
        return CodeGenerator().generate(
            "project",
            exists=lambda candidate: candidate.upper() in existing,
            name=(name or "").strip() or None,
            use_year=not bool((name or "").strip()),
        )

    @staticmethod
    def _is_project_code_integrity_error(exc: IntegrityError) -> bool:
        message = " ".join(
            part
            for part in [
                str(getattr(exc, "orig", "") or ""),
                str(getattr(exc, "statement", "") or ""),
                str(exc),
            ]
            if part
        ).lower()
        return "ux_projects_code" in message or "projects.project_code" in message

    @staticmethod
    def _raise_project_code_duplicate(code: str, exc: IntegrityError) -> None:
        raise ValidationError(
            f"Project code '{code}' already exists.",
            code="CODE_DUPLICATE",
        ) from exc

    def create_project(
        self,
        name: str,
        description: str = "",
        client_name: str | None = None,
        client_contact: str | None = None,
        planned_budget: float | None = None,
        currency: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        organization_id: str | None = None,
        site_id: str | None = None,
        client_party_id: str | None = None,
        manager_user_id: str | None = None,
        code: str = "",
    ) -> Project:
        require_permission(self._user_session, "project.manage", operation_label="create project")
        resolved_organization_id = self._resolve_project_organization_id(
            organization_id,
            operation_label="create project",
        )
        self._validate_project_name(name, organization_id=resolved_organization_id)
        resolved_currency = (currency or "").strip().upper() or DEFAULT_CURRENCY_CODE
        resolved_code = self._resolve_project_code(
            code,
            name,
            organization_id=resolved_organization_id,
        )
        project = Project.create(
            name=name.strip(),
            code=resolved_code,
            description=(description or "").strip(),
            client_name=(client_name or "").strip() or None,
            client_contact=(client_contact or "").strip() or None,
            planned_budget=planned_budget,
            currency=resolved_currency,
            start_date=start_date,
            end_date=end_date,
            organization_id=resolved_organization_id,
            site_id=(site_id or "").strip() or None,
            client_party_id=(client_party_id or "").strip() or None,
            manager_user_id=(manager_user_id or "").strip() or None,
        )

        try:
            self._project_repo.add(project)
            self._session.commit()
            record_audit(
                self,
                action="project.create",
                entity_type="project",
                entity_id=project.id,
                project_id=project.id,
                details={"name": project.name},
            )
            logger.info("Created project %s - %s", project.id, project.name)
            domain_events.project_changed.emit(project.id)
            return project
        except IntegrityError as exc:
            self._session.rollback()
            if self._is_project_code_integrity_error(exc):
                self._raise_project_code_duplicate(resolved_code, exc)
            logger.error("Error creating project: %s", exc)
            raise
        except Exception as exc:
            self._session.rollback()
            logger.error("Error creating project: %s", exc)
            raise

    def set_status(self, project_id: str, status: ProjectStatus) -> None:
        require_permission(self._user_session, "project.manage", operation_label="set project status")
        project = self._project_repo.get(project_id)
        if not project:
            raise NotFoundError("Project not found")
        self._assert_project_in_active_organization(project, operation_label="set project status")
        require_project_permission(
            self._user_session,
            project.id,
            "project.manage",
            operation_label="set project status",
        )

        project.status = status
        try:
            self._project_repo.update(project)
            self._session.commit()
            record_audit(
                self,
                action="project.set_status",
                entity_type="project",
                entity_id=project.id,
                project_id=project.id,
                details={"status": project.status.value},
            )
        except Exception:
            self._session.rollback()
            raise

    def update_dates_from_tasks(self, project_id: str) -> None:
        project = self._project_repo.get(project_id)
        if not project:
            raise NotFoundError("Project not found")
        self._assert_project_in_active_organization(project, operation_label="update project dates")

        tasks = self._task_repo.list_by_project(project_id)
        if not tasks:
            return

        start_dates = [task.start_date for task in tasks if task.start_date]
        end_dates = [task.end_date for task in tasks if task.end_date]

        if start_dates:
            project.start_date = min(start_dates)
        if end_dates:
            project.end_date = max(end_dates)

        self._project_repo.update(project)

    def update_project(
        self,
        project_id: str,
        expected_version: int | None = None,
        name: str | None = None,
        description: str | None = None,
        status: ProjectStatus | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        client_name: str | None = None,
        client_contact: str | None = None,
        planned_budget: float | None = None,
        currency: str | None = None,
        organization_id: str | None = None,
        site_id: str | None = None,
        client_party_id: str | None = None,
        manager_user_id: str | None = None,
        code: str | None = None,
    ) -> Project:
        require_permission(self._user_session, "project.manage", operation_label="update project")
        project = self._project_repo.get(project_id)
        if not project:
            raise NotFoundError("Project not found.", code="PROJECT_NOT_FOUND")
        self._assert_project_in_active_organization(project, operation_label="update project")
        require_project_permission(
            self._user_session,
            project.id,
            "project.manage",
            operation_label="update project",
        )
        if expected_version is not None and project.version != expected_version:
            raise ConcurrencyError(
                "Project changed since you opened it. Refresh and try again.",
                code="STALE_WRITE",
            )

        if name is not None:
            if not name.strip():
                raise ValidationError("Project name cannot be empty.", code="PROJECT_NAME_EMPTY")
            self._validate_project_name(
                name,
                organization_id=getattr(project, "organization_id", None),
                exclude_id=project.id,
            )
            project.name = name.strip()
        if code is not None and code.strip():
            project.code = self._resolve_project_code(
                code,
                project.name,
                exclude_id=project.id,
                organization_id=getattr(project, "organization_id", None),
            )
        if description is not None:
            project.description = description.strip()
        if status is not None:
            project.status = status
        if start_date is not None:
            project.start_date = start_date
        if end_date is not None:
            if project.start_date and end_date < project.start_date:
                raise ValidationError("Project end date cannot be before start date.")
            project.end_date = end_date
        if client_name is not None:
            project.client_name = client_name.strip() or None
        if client_contact is not None:
            project.client_contact = client_contact.strip() or None
        if planned_budget is not None:
            if planned_budget < 0:
                raise ValidationError("Planned budget cannot be negative.")
            project.planned_budget = planned_budget
        if currency is not None:
            project.currency = currency.strip().upper() or None
        if organization_id is not None:
            project.organization_id = self._resolve_project_organization_id(
                organization_id,
                operation_label="update project",
            )
        if site_id is not None:
            project.site_id = (site_id or "").strip() or None
        if client_party_id is not None:
            project.client_party_id = (client_party_id or "").strip() or None
        if manager_user_id is not None:
            project.manager_user_id = (manager_user_id or "").strip() or None

        try:
            self._project_repo.update(project)
            self._session.commit()
            record_audit(
                self,
                action="project.update",
                entity_type="project",
                entity_id=project.id,
                project_id=project.id,
                details={"name": project.name, "status": project.status.value},
            )
        except IntegrityError as exc:
            self._session.rollback()
            if self._is_project_code_integrity_error(exc):
                self._raise_project_code_duplicate(project.code, exc)
            raise
        except Exception:
            self._session.rollback()
            raise

        domain_events.project_changed.emit(project_id)
        return project

    def delete_project(self, project_id: str) -> None:
        require_permission(self._user_session, "project.manage", operation_label="delete project")
        project = self._project_repo.get(project_id)
        if not project:
            raise NotFoundError("Project not found")
        self._assert_project_in_active_organization(project, operation_label="delete project")
        require_project_permission(
            self._user_session,
            project.id,
            "project.manage",
            operation_label="delete project",
        )

        try:
            tasks = self._task_repo.list_by_project(project_id)
            for task in tasks:
                self._dependency_repo.delete_for_task(task.id)
                assignments = self._assignment_repo.list_by_task(task.id)
                if self._time_entry_repo is not None:
                    for assignment in assignments:
                        self._time_entry_repo.delete_by_assignment(assignment.id)
                self._assignment_repo.delete_by_task(task.id)
                self._calendar_repo.delete_for_task(task.id)
                self._task_repo.delete(task.id)

            self._cost_repo.delete_by_project(project_id)
            self._calendar_repo.delete_for_project(project_id)
            self._project_repo.delete(project_id)
            self._session.commit()
            record_audit(
                self,
                action="project.delete",
                entity_type="project",
                entity_id=project.id,
                project_id=project.id,
                details={"name": project.name},
            )
        except Exception:
            self._session.rollback()
            raise

        domain_events.project_changed.emit(project_id)

    def _active_project_organization_id(self, *, operation_label: str) -> str | None:
        tenant_context = getattr(self, "_tenant_context_service", None)
        if tenant_context is None:
            raise BusinessRuleError(
                f"Active organization context is required for {operation_label}.",
                code="TENANT_CONTEXT_REQUIRED",
            )
        return tenant_context.require_active_organization_id(operation_label=operation_label)

    def _resolve_project_organization_id(
        self,
        organization_id: str | None,
        *,
        operation_label: str,
    ) -> str:
        active_organization_id = self._active_project_organization_id(operation_label=operation_label)
        requested_organization_id = str(organization_id or "").strip() or None
        if requested_organization_id and requested_organization_id != active_organization_id:
            raise ValidationError(
                "Project organization must match the active tenant context.",
                code="PROJECT_ORGANIZATION_MISMATCH",
            )
        return active_organization_id

    def _assert_project_in_active_organization(self, project: Project, *, operation_label: str) -> None:
        active_organization_id = self._active_project_organization_id(operation_label=operation_label)
        project_organization_id = str(getattr(project, "organization_id", "") or "").strip()
        if project_organization_id != active_organization_id:
            raise NotFoundError("Project not found.", code="PROJECT_NOT_FOUND")


__all__ = ["DEFAULT_CURRENCY_CODE", "ProjectLifecycleMixin"]

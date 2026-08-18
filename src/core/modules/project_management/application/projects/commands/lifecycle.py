from __future__ import annotations

import logging
import json
from dataclasses import replace
from datetime import date, datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.core.modules.project_management.contracts.repositories.projects.project import ProjectRepository
from src.core.modules.project_management.contracts.repositories.finance.configuration.financial_configuration import (
    ProjectFinancialProfileRepository,
)
from src.core.modules.project_management.contracts.repositories.tasks.task import (
    AssignmentRepository,
    DependencyRepository,
    TaskRepository,
)
from src.core.modules.project_management.domain.projects.project import Project
from src.core.modules.project_management.domain.tasks.hierarchy import (
    order_tasks_children_first,
    select_leaf_tasks,
)
from src.core.modules.project_management.domain.financials.configuration import (
    ProjectFinancialProfile,
)
from src.core.modules.project_management.application.common.currency_policy import (
    resolve_pm_currency,
)
from src.core.modules.project_management.access.scope_permissions import require_project_permission
from src.core.shared.activity import record_activity
from src.core.shared.audit import record_audit_entry
from src.core.platform.application.security.authorization.enforcement.permission_checks import require_permission
from src.core.platform.common.exceptions import BusinessRuleError, ConcurrencyError, NotFoundError, ValidationError
from src.core.platform.contract.repositories.time_management.time.contracts import TimeEntryRepository
from src.core.shared.events.domain_events import domain_events
from src.core.modules.project_management.domain.enums import ProjectStatus
from src.core.platform.domain.security.auth.session import UserSessionContext

logger = logging.getLogger(__name__)


class ProjectLifecycleMixin:
    _session: Session
    _project_repo: ProjectRepository
    _task_repo: TaskRepository
    _dependency_repo: DependencyRepository
    _assignment_repo: AssignmentRepository
    _time_entry_repo: TimeEntryRepository | None
    _financial_profile_repo: ProjectFinancialProfileRepository
    _user_session:UserSessionContext

    def _validate_project_name(
        self,
        name: str,
        *,
        organization_id: str,
        exclude_id: str | None = None,
    ) -> None:
        normalized_name = name.strip().lower()
        if not normalized_name:
            return
        for project in self._project_repo.list():
            if exclude_id is not None and project.id == exclude_id:
                continue
            if project.name.strip().lower() == normalized_name:
                raise ValidationError(
                    "A project with this name already exists.",
                    code="PROJECT_NAME_DUPLICATE",
                )

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

        project_rows = self._project_repo.list()
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
        financial_currency_code: str | None = None,
        status: ProjectStatus = ProjectStatus.PLANNED,
        start_date: date | None = None,
        end_date: date | None = None,
        organization_id: str | None = None,
        site_id: str | None = None,
        department_id: str | None = None,
        client_party_id: str | None = None,
        manager_user_id: str | None = None,
        code: str = "",
    ) -> Project:
        require_permission(self._user_session, "project.manage", operation_label="create project")
        resolved_organization_id = self._resolve_project_organization_id(
            organization_id,
            operation_label="create project",
        )
        resolved_currency = resolve_pm_currency(
            tenant_context_service=getattr(self, "_tenant_context_service", None),
            operation_label="create project",
            explicit=financial_currency_code,
        )
        project = Project.create(
            name=name,
            description=description,
            client_name=client_name,
            client_contact=client_contact,
            status=status,
            start_date=start_date,
            end_date=end_date,
            organization_id=resolved_organization_id,
            site_id=site_id,
            department_id=department_id,
            client_party_id=client_party_id,
            manager_user_id=manager_user_id,
        )
        self._validate_project_name(project.name, organization_id=resolved_organization_id)
        project.code = self._resolve_project_code(
            code,
            project.name,
            organization_id=resolved_organization_id,
        )

        try:
            self._project_repo.add(project)
            self._session.flush()
            context = self._tenant_context_service.require_organization_context(
                operation_label="create project financial profile"
            )
            profile = ProjectFinancialProfile.create(
                tenant_id=context.tenant_id,
                organization_id=context.organization_id,
                project_id=project.id,
                currency_code=resolved_currency,
                financial_start_date=project.start_date,
                financial_end_date=project.end_date,
            )
            self._financial_profile_repo.add(profile)
            self._record_financial_profile_audit("create", profile)
            self._session.commit()
            record_activity(
                self,
                action="project.create",
                entity_type="project",
                entity_id=project.id,
                module="project_management",
                workspace_id=project.id,
                details={"name": project.name},
            )
            logger.info("Created project %s - %s", project.id, project.name)
            domain_events.project_changed.emit(project.id)
            return project
        except IntegrityError as exc:
            self._session.rollback()
            if self._is_project_code_integrity_error(exc):
                self._raise_project_code_duplicate(project.code, exc)
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
            record_activity(
                self,
                action="project.set_status",
                entity_type="project",
                entity_id=project.id,
                module="project_management",
                workspace_id=project.id,
                details={"status": project.status.value},
            )
        except Exception:
            self._session.rollback()
            raise

    def update_dates_from_tasks(self, project_id: str) -> None:
        project = self._project_repo.get(project_id)
        if not project:
            raise NotFoundError("Project not found")

        tasks = select_leaf_tasks(self._task_repo.list_by_project(project_id))
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
        organization_id: str | None = None,
        site_id: str | None = None,
        department_id: str | None = None,
        client_party_id: str | None = None,
        manager_user_id: str | None = None,
        code: str | None = None,
    ) -> Project:
        require_permission(self._user_session, "project.manage", operation_label="update project")
        project = self._project_repo.get(project_id)
        if not project:
            raise NotFoundError("Project not found.", code="PROJECT_NOT_FOUND")
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
        resolved_organization_id = (
            self._resolve_project_organization_id(
                organization_id,
                operation_label="update project",
            )
            if organization_id is not None
            else project.organization_id
        )
        candidate = replace(
            project,
            name=project.name if name is None else name,
            description=project.description if description is None else description,
            status=project.status if status is None else status,
            start_date=project.start_date if start_date is None else start_date,
            end_date=project.end_date if end_date is None else end_date,
            client_name=project.client_name if client_name is None else client_name,
            client_contact=project.client_contact if client_contact is None else client_contact,
            organization_id=resolved_organization_id,
            site_id=project.site_id if site_id is None else site_id,
            department_id=project.department_id if department_id is None else department_id,
            client_party_id=project.client_party_id if client_party_id is None else client_party_id,
            manager_user_id=project.manager_user_id if manager_user_id is None else manager_user_id,
        )
        if name is not None:
            self._validate_project_name(
                candidate.name,
                organization_id=getattr(candidate, "organization_id", None),
                exclude_id=project.id,
            )
        if code is not None and code.strip():
            candidate.code = self._resolve_project_code(
                code,
                candidate.name,
                exclude_id=project.id,
                organization_id=getattr(candidate, "organization_id", None),
            )
        project = candidate

        try:
            self._project_repo.update(project)
            self._session.commit()
            record_activity(
                self,
                action="project.update",
                entity_type="project",
                entity_id=project.id,
                module="project_management",
                workspace_id=project.id,
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

    def _record_financial_profile_audit(
        self,
        operation: str,
        profile: ProjectFinancialProfile,
        *,
        old: ProjectFinancialProfile | None = None,
    ) -> None:
        def _value(item: ProjectFinancialProfile | None) -> str | None:
            if item is None:
                return None
            return json.dumps(
                {
                    "billing_method": item.billing_method.value,
                    "budget_control_mode": item.budget_control_mode.value,
                    "cost_code_policy": item.cost_code_policy.value,
                    "currency_code": item.currency_code,
                    "status": item.status.value,
                    "version": item.version,
                },
                sort_keys=True,
            )

        record_audit_entry(
            self,
            operation=f"financial_profile.{operation}",
            entity_type="project_financial_profile",
            entity_id=profile.id,
            entity_parent_id=profile.project_id,
            module="project_management",
            old_value=_value(old),
            new_value=_value(profile),
            workspace_id=profile.project_id,
            source="application",
            severity="high",
            compliance_tag="financial",
            metadata={"action": f"financial_profile.{operation}"},
            commit=False,
            fail_closed=True,
        )

    def delete_project(self, project_id: str) -> None:
        require_permission(self._user_session, "project.manage", operation_label="delete project")
        project = self._project_repo.get(project_id)
        if not project:
            raise NotFoundError("Project not found")
        require_project_permission(
            self._user_session,
            project.id,
            "project.manage",
            operation_label="delete project",
        )

        try:
            tasks = order_tasks_children_first(self._task_repo.list_by_project(project_id))
            for task in tasks:
                self._dependency_repo.delete_for_task(task.id)
                assignments = self._assignment_repo.list_by_task(task.id)
                if self._time_entry_repo is not None:
                    for assignment in assignments:
                        self._time_entry_repo.delete_by_assignment(assignment.id)
                self._assignment_repo.delete_by_task(task.id)
                self._task_repo.delete(task.id)

            self._project_repo.delete(project_id)
            self._session.commit()
            record_activity(
                self,
                action="project.delete",
                entity_type="project",
                entity_id=project.id,
                module="project_management",
                workspace_id=project.id,
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


__all__ = ["ProjectLifecycleMixin"]

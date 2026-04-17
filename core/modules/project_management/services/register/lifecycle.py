from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from core.modules.project_management.domain.register import (
    RegisterEntry,
    RegisterEntrySeverity,
    RegisterEntryStatus,
    RegisterEntryType,
    as_register_entry_severity,
    as_register_entry_status,
    as_register_entry_type,
)
from core.platform.notifications.domain_events import domain_events
from core.platform.common.exceptions import ConcurrencyError, NotFoundError, ValidationError
from core.modules.project_management.interfaces import ProjectRepository, RegisterEntryRepository
from src.core.platform.access.authorization import require_project_permission
from core.platform.audit.helpers import record_audit
from src.core.platform.auth.authorization import require_permission


class RegisterLifecycleMixin:
    _project_repo: ProjectRepository
    _register_repo: RegisterEntryRepository
    _UNSET = object()

    def create_entry(
        self,
        project_id: str,
        *,
        entry_type: RegisterEntryType,
        title: str,
        description: str = "",
        severity: RegisterEntrySeverity = RegisterEntrySeverity.MEDIUM,
        status: RegisterEntryStatus = RegisterEntryStatus.OPEN,
        owner_name: str | None = None,
        due_date=None,
        impact_summary: str = "",
        response_plan: str = "",
    ) -> RegisterEntry:
        require_permission(self._user_session, "register.manage", operation_label="create register entry")
        require_project_permission(
            self._user_session,
            project_id,
            "register.manage",
            operation_label="create register entry",
        )
        project = self._project_repo.get(project_id)
        if project is None:
            raise NotFoundError("Project not found.", code="PROJECT_NOT_FOUND")
        entry = RegisterEntry.create(
            project_id,
            entry_type=as_register_entry_type(entry_type),
            title=self._normalize_title(title),
            description=(description or "").strip(),
            severity=as_register_entry_severity(severity),
            status=as_register_entry_status(status),
            owner_name=self._normalize_owner(owner_name),
            due_date=due_date,
            impact_summary=(impact_summary or "").strip(),
            response_plan=(response_plan or "").strip(),
        )
        try:
            self._register_repo.add(entry)
            self._session.commit()
            record_audit(
                self,
                action="register.create",
                entity_type="register_entry",
                entity_id=entry.id,
                project_id=entry.project_id,
                details=self._audit_details(entry),
            )
        except Exception:
            self._session.rollback()
            raise
        domain_events.register_changed.emit(entry.project_id)
        return entry

    def update_entry(
        self,
        entry_id: str,
        *,
        expected_version: int | None = None,
        entry_type: RegisterEntryType | None = None,
        title: str | None = None,
        description: str | None = None,
        severity: RegisterEntrySeverity | None = None,
        status: RegisterEntryStatus | None = None,
        owner_name: str | None = None,
        due_date: Any = _UNSET,
        impact_summary: str | None = None,
        response_plan: str | None = None,
    ) -> RegisterEntry:
        require_permission(self._user_session, "register.manage", operation_label="update register entry")
        entry = self._register_repo.get(entry_id)
        if entry is None:
            raise NotFoundError("Register entry not found.", code="REGISTER_ENTRY_NOT_FOUND")
        require_project_permission(
            self._user_session,
            entry.project_id,
            "register.manage",
            operation_label="update register entry",
        )
        if expected_version is not None and entry.version != expected_version:
            raise ConcurrencyError(
                "Register entry changed since you opened it. Refresh and try again.",
                code="STALE_WRITE",
            )
        if entry_type is not None:
            entry.entry_type = as_register_entry_type(entry_type)
        if title is not None:
            entry.title = self._normalize_title(title)
        if description is not None:
            entry.description = description.strip()
        if severity is not None:
            entry.severity = as_register_entry_severity(severity)
        if status is not None:
            entry.status = as_register_entry_status(status)
        if owner_name is not None:
            entry.owner_name = self._normalize_owner(owner_name)
        if due_date is not self._UNSET:
            entry.due_date = due_date
        if impact_summary is not None:
            entry.impact_summary = impact_summary.strip()
        if response_plan is not None:
            entry.response_plan = response_plan.strip()
        entry.updated_at = datetime.now(timezone.utc)
        try:
            self._register_repo.update(entry)
            self._session.commit()
            record_audit(
                self,
                action="register.update",
                entity_type="register_entry",
                entity_id=entry.id,
                project_id=entry.project_id,
                details=self._audit_details(entry),
            )
        except Exception:
            self._session.rollback()
            raise
        domain_events.register_changed.emit(entry.project_id)
        return entry

    def delete_entry(self, entry_id: str) -> None:
        require_permission(self._user_session, "register.manage", operation_label="delete register entry")
        entry = self._register_repo.get(entry_id)
        if entry is None:
            raise NotFoundError("Register entry not found.", code="REGISTER_ENTRY_NOT_FOUND")
        require_project_permission(
            self._user_session,
            entry.project_id,
            "register.manage",
            operation_label="delete register entry",
        )
        try:
            self._register_repo.delete(entry_id)
            self._session.commit()
            record_audit(
                self,
                action="register.delete",
                entity_type="register_entry",
                entity_id=entry.id,
                project_id=entry.project_id,
                details=self._audit_details(entry),
            )
        except Exception:
            self._session.rollback()
            raise
        domain_events.register_changed.emit(entry.project_id)

    @staticmethod
    def _normalize_title(value: str) -> str:
        title = (value or "").strip()
        if not title:
            raise ValidationError("Register title cannot be empty.", code="REGISTER_TITLE_EMPTY")
        return title

    @staticmethod
    def _normalize_owner(value: str | None) -> str | None:
        return (value or "").strip() or None

    @staticmethod
    def _audit_details(entry: RegisterEntry) -> dict[str, object]:
        entry_type = as_register_entry_type(entry.entry_type)
        severity = as_register_entry_severity(entry.severity)
        status = as_register_entry_status(entry.status)
        return {
            "entry_type": entry_type.value,
            "title": entry.title,
            "severity": severity.value,
            "status": status.value,
            "owner_name": entry.owner_name,
            "due_date": entry.due_date.isoformat() if entry.due_date else None,
        }


__all__ = ["RegisterLifecycleMixin"]

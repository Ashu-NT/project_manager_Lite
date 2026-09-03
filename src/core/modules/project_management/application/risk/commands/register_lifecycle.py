from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.exc import IntegrityError

from src.core.modules.project_management.domain.risk.register import (
    RegisterEntry,
    RegisterEntrySeverity,
    RegisterEntryStatus,
    RegisterEntryType,
    as_register_entry_severity,
    as_register_entry_status,
    as_register_entry_type,
)
from src.core.modules.project_management.application.risk.register_events import (
    RegisterEntryChangeType,
    RegisterEntryChanged,
)
from src.core.platform.common.exceptions import ConcurrencyError, NotFoundError, ValidationError
from src.core.modules.project_management.contracts.repositories.projects.project import ProjectRepository
from src.core.modules.project_management.contracts.repositories.register.register import RegisterEntryRepository
from src.core.modules.project_management.access.scope_permissions import require_project_permission
from src.core.shared.activity import record_activity
from src.core.shared.audit import record_audit_entry
from src.core.platform.application.security.authorization.enforcement.permission_checks import require_permission


class RegisterLifecycleMixin:
    _project_repo: ProjectRepository
    _register_repo: RegisterEntryRepository
    _UNSET = object()

    @staticmethod
    def _is_register_code_integrity_error(exc: IntegrityError) -> bool:
        message = " ".join(
            part
            for part in [
                str(getattr(exc, "orig", "") or ""),
                str(getattr(exc, "statement", "") or ""),
                str(exc),
            ]
            if part
        ).lower()
        return (
            "ux_register_entries_project_code" in message
            or "register_entries.entry_code" in message
        )

    @staticmethod
    def _raise_register_code_duplicate(code: str, exc: IntegrityError) -> None:
        raise ValidationError(
            f"Register code '{code}' already exists in this project.",
            code="CODE_DUPLICATE",
        ) from exc

    def _resolve_entry_code(
        self,
        code: str,
        project_id: str,
        title: str,
        *,
        exclude_id: str | None = None,
        register_repo: RegisterEntryRepository | None = None,
    ) -> str:
        from src.core.platform.common.code_generation import (
            CodeGenerator,
            assert_code_unique,
            normalize_manual_code,
        )

        repo = register_repo if register_repo is not None else self._register_repo
        existing = {
            str(getattr(entry, "code", "") or "").upper()
            for entry in repo.list_entries(project_id=project_id)
            if exclude_id is None or entry.id != exclude_id
        }
        manual = normalize_manual_code(code)
        if manual:
            assert_code_unique(
                manual,
                exists=lambda candidate: candidate.upper() in existing,
                label="Register code",
            )
            return manual
        return CodeGenerator().generate(
            "register",
            exists=lambda candidate: candidate.upper() in existing,
            name=(title or "").strip() or None,
            use_year=not bool((title or "").strip()),
        )

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
        code: str = "",
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
            entry_type=entry_type,
            title=title,
            code="",
            description=description,
            severity=severity,
            status=status,
            owner_name=owner_name,
            due_date=due_date,
            impact_summary=impact_summary,
            response_plan=response_plan,
        )
        scope = self._tenant_context_service.require_active_scope_ids(
            operation_label="create register entry"
        )
        try:
            with self._require_uow_factory().create(context=self._new_context()) as uow:
                entry.code = self._resolve_entry_code(
                    code, project_id, entry.title, register_repo=uow.entries
                )
                uow.entries.add(entry)
                record_activity(
                    uow,
                    action="register.create",
                    entity_type="register_entry",
                    entity_id=entry.id,
                    module="project_management",
                    workspace_id=entry.project_id,
                    details=self._audit_details(entry),
                    commit=False,
                )
                record_audit_entry(
                    uow,
                    operation="create",
                    entity_type="register_entry",
                    entity_id=entry.id,
                    module="project_management",
                    organization_id=scope.organization_id,
                    severity="low",
                    metadata={"action": "register.create", **self._audit_details(entry)},
                    commit=False,
                    fail_closed=True,
                )
                uow.record_event(
                    RegisterEntryChanged(
                        tenant_id=scope.tenant_id,
                        organization_id=scope.organization_id,
                        project_id=entry.project_id,
                        register_entry_id=entry.id,
                        entry_type=as_register_entry_type(entry.entry_type),
                        change_type=RegisterEntryChangeType.CREATED,
                        occurred_at=datetime.now(timezone.utc),
                    )
                )
                uow.commit()
        except IntegrityError as exc:
            if self._is_register_code_integrity_error(exc):
                self._raise_register_code_duplicate(entry.code, exc)
            raise
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
        code: str | None = None,
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
        candidate = replace(
            entry,
            entry_type=entry.entry_type if entry_type is None else entry_type,
            title=entry.title if title is None else title,
            description=entry.description if description is None else description,
            severity=entry.severity if severity is None else severity,
            status=entry.status if status is None else status,
            owner_name=entry.owner_name if owner_name is None else owner_name,
            due_date=entry.due_date if due_date is self._UNSET else due_date,
            impact_summary=entry.impact_summary if impact_summary is None else impact_summary,
            response_plan=entry.response_plan if response_plan is None else response_plan,
            updated_at=datetime.now(timezone.utc),
        )
        scope = self._tenant_context_service.require_active_scope_ids(
            operation_label="update register entry"
        )
        try:
            with self._require_uow_factory().create(context=self._new_context()) as uow:
                if code is not None and code.strip():
                    candidate = replace(
                        candidate,
                        code=self._resolve_entry_code(
                            code,
                            entry.project_id,
                            candidate.title,
                            exclude_id=entry.id,
                            register_repo=uow.entries,
                        ),
                    )
                uow.entries.update(candidate)
                record_activity(
                    uow,
                    action="register.update",
                    entity_type="register_entry",
                    entity_id=candidate.id,
                    module="project_management",
                    workspace_id=candidate.project_id,
                    details=self._audit_details(candidate),
                    commit=False,
                )
                record_audit_entry(
                    uow,
                    operation="update",
                    entity_type="register_entry",
                    entity_id=candidate.id,
                    module="project_management",
                    organization_id=scope.organization_id,
                    severity="low",
                    metadata={"action": "register.update", **self._audit_details(candidate)},
                    commit=False,
                    fail_closed=True,
                )
                uow.record_event(
                    RegisterEntryChanged(
                        tenant_id=scope.tenant_id,
                        organization_id=scope.organization_id,
                        project_id=candidate.project_id,
                        register_entry_id=candidate.id,
                        entry_type=as_register_entry_type(candidate.entry_type),
                        change_type=RegisterEntryChangeType.UPDATED,
                        occurred_at=datetime.now(timezone.utc),
                    )
                )
                uow.commit()
        except IntegrityError as exc:
            if self._is_register_code_integrity_error(exc):
                self._raise_register_code_duplicate(candidate.code, exc)
            raise
        return candidate

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
        scope = self._tenant_context_service.require_active_scope_ids(
            operation_label="delete register entry"
        )
        with self._require_uow_factory().create(context=self._new_context()) as uow:
            uow.entries.delete(entry_id)
            record_activity(
                uow,
                action="register.delete",
                entity_type="register_entry",
                entity_id=entry.id,
                module="project_management",
                workspace_id=entry.project_id,
                details=self._audit_details(entry),
                commit=False,
            )
            record_audit_entry(
                uow,
                operation="delete",
                entity_type="register_entry",
                entity_id=entry.id,
                module="project_management",
                organization_id=scope.organization_id,
                severity="low",
                metadata={"action": "register.delete", **self._audit_details(entry)},
                commit=False,
                fail_closed=True,
            )
            uow.record_event(
                RegisterEntryChanged(
                    tenant_id=scope.tenant_id,
                    organization_id=scope.organization_id,
                    project_id=entry.project_id,
                    register_entry_id=entry.id,
                    entry_type=as_register_entry_type(entry.entry_type),
                    change_type=RegisterEntryChangeType.REMOVED,
                    occurred_at=datetime.now(timezone.utc),
                )
            )
            uow.commit()

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

from __future__ import annotations

from datetime import date

from core.modules.project_management.domain.register import RegisterEntry, RegisterEntrySeverity, RegisterEntryStatus, RegisterEntryType
from src.core.platform.common.exceptions import NotFoundError
from core.modules.project_management.interfaces import ProjectRepository, RegisterEntryRepository
from src.core.platform.access.authorization import filter_project_rows, require_project_permission
from src.core.platform.auth.authorization import require_permission
from core.modules.project_management.services.register.models import RegisterProjectSummary, RegisterUrgentItem

_ACTIVE_STATUSES = {
    RegisterEntryStatus.OPEN,
    RegisterEntryStatus.IN_PROGRESS,
    RegisterEntryStatus.MITIGATED,
}
_SEVERITY_ORDER = {
    RegisterEntrySeverity.CRITICAL: 0,
    RegisterEntrySeverity.HIGH: 1,
    RegisterEntrySeverity.MEDIUM: 2,
    RegisterEntrySeverity.LOW: 3,
}


class RegisterQueryMixin:
    _project_repo: ProjectRepository
    _register_repo: RegisterEntryRepository

    def get_entry(self, entry_id: str) -> RegisterEntry:
        require_permission(self._user_session, "register.read", operation_label="view register entry")
        entry = self._register_repo.get(entry_id)
        if entry is None:
            raise NotFoundError("Register entry not found.", code="REGISTER_ENTRY_NOT_FOUND")
        require_project_permission(
            self._user_session,
            entry.project_id,
            "register.read",
            operation_label="view register entry",
        )
        return entry

    def list_entries(
        self,
        *,
        project_id: str | None = None,
        entry_type: RegisterEntryType | None = None,
        status: RegisterEntryStatus | None = None,
        severity: RegisterEntrySeverity | None = None,
    ) -> list[RegisterEntry]:
        require_permission(self._user_session, "register.read", operation_label="view risk/issue/change register")
        if project_id:
            require_project_permission(
                self._user_session,
                project_id,
                "register.read",
                operation_label="view risk/issue/change register",
            )
        rows = self._register_repo.list_entries(
            project_id=project_id,
            entry_type=entry_type,
            status=status,
            severity=severity,
        )
        return filter_project_rows(
            rows,
            self._user_session,
            permission_code="register.read",
            project_id_getter=lambda entry: entry.project_id,
        )

    def get_project_summary(self, project_id: str) -> RegisterProjectSummary:
        require_permission(self._user_session, "register.read", operation_label="view register summary")
        require_project_permission(
            self._user_session,
            project_id,
            "register.read",
            operation_label="view register summary",
        )
        project = self._project_repo.get(project_id)
        if project is None:
            raise NotFoundError("Project not found.", code="PROJECT_NOT_FOUND")
        items = self._register_repo.list_entries(project_id=project_id)
        today = date.today()
        active_items = [item for item in items if item.status in _ACTIVE_STATUSES]
        urgent = sorted(
            active_items,
            key=lambda item: (
                _SEVERITY_ORDER.get(item.severity, 99),
                0 if item.due_date and item.due_date < today else 1,
                item.due_date or date.max,
                item.title.lower(),
            ),
        )[:5]
        return RegisterProjectSummary(
            open_risks=sum(
                1
                for item in items
                if item.entry_type == RegisterEntryType.RISK and item.status in _ACTIVE_STATUSES
            ),
            open_issues=sum(
                1
                for item in items
                if item.entry_type == RegisterEntryType.ISSUE and item.status in _ACTIVE_STATUSES
            ),
            pending_changes=sum(
                1
                for item in items
                if item.entry_type == RegisterEntryType.CHANGE
                and item.status in {RegisterEntryStatus.OPEN, RegisterEntryStatus.IN_PROGRESS}
            ),
            overdue_items=sum(
                1
                for item in active_items
                if item.due_date is not None and item.due_date < today
            ),
            critical_items=sum(
                1
                for item in active_items
                if item.severity == RegisterEntrySeverity.CRITICAL
            ),
            urgent_items=[
                RegisterUrgentItem(
                    entry_id=item.id,
                    entry_type=item.entry_type,
                    title=item.title,
                    severity=item.severity,
                    status=item.status,
                    owner_name=item.owner_name,
                    due_date=item.due_date,
                )
                for item in urgent
            ],
        )


__all__ = ["RegisterQueryMixin"]

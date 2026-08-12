from __future__ import annotations

from datetime import date

from src.core.modules.project_management.domain.risk.register import RegisterEntry, RegisterEntrySeverity, RegisterEntryStatus, RegisterEntryType
from src.core.platform.common.exceptions import NotFoundError
from src.core.modules.project_management.contracts.repositories.projects.project import ProjectRepository
from src.core.modules.project_management.contracts.repositories.register.register import RegisterEntryRepository
from src.core.modules.project_management.application.common.pagination import PageRequest
from src.core.modules.project_management.contracts.reads.register import (
    RegisterCatalogReadPage,
    RegisterCatalogReader,
)
from src.core.modules.project_management.access.scope_permissions import filter_project_rows, require_project_permission
from src.core.platform.application.security.authorization.enforcement.permission_checks import require_permission
from src.core.modules.project_management.application.risk.dto.register_summary import (
    RegisterDashboardSnapshot,
    RegisterProjectSummary,
    RegisterUrgentItem,
)

_ACTIVE_STATUSES = {
    RegisterEntryStatus.OPEN,
    RegisterEntryStatus.IN_PROGRESS,
    RegisterEntryStatus.MITIGATED,
}
class RegisterQueryMixin:
    _project_repo: ProjectRepository
    _register_repo: RegisterEntryRepository
    _register_catalog_reader: RegisterCatalogReader | None

    def query_catalog_page(
        self,
        *,
        project_id: str | None = None,
        entry_type: RegisterEntryType | None = None,
        status: RegisterEntryStatus | None = None,
        severity: RegisterEntrySeverity | None = None,
        search_text: str = "",
        as_of: date | None = None,
        page: int = 1,
        page_size: int = 25,
    ) -> RegisterCatalogReadPage:
        require_permission(
            self._user_session,
            "register.read",
            operation_label="view register catalog",
        )
        if project_id:
            require_project_permission(
                self._user_session,
                project_id,
                "register.read",
                operation_label="view register catalog",
            )
        if self._register_catalog_reader is None or self._tenant_context_service is None:
            raise RuntimeError("Register catalog reader is not configured.")
        page_request = PageRequest(page=page, page_size=page_size)
        scope = self._tenant_context_service.require_active_scope_ids(
            operation_label="view register catalog"
        )
        allowed_project_ids: tuple[str, ...] | None = None
        if self._user_session is not None and self._user_session.is_project_restricted():
            allowed_project_ids = tuple(
                sorted(self._user_session.project_ids_for("register.read"))
            )
        return self._register_catalog_reader.read_page(
            tenant_id=scope.tenant_id,
            organization_id=scope.organization_id,
            allowed_project_ids=allowed_project_ids,
            project_id=project_id,
            entry_type=entry_type,
            status=status,
            severity=severity,
            search_text=str(search_text or "").strip(),
            as_of=as_of or date.today(),
            page=page_request.page,
            page_size=page_request.page_size,
        )

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
        as_of: date | None = None,
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
        scoped_rows = filter_project_rows(
            rows,
            self._user_session,
            permission_code="register.read",
            project_id_getter=lambda entry: entry.project_id,
        )
        triage_date = as_of or date.today()
        return sorted(scoped_rows, key=lambda entry: entry.triage_key(triage_date))

    def get_project_summary(self, project_id: str) -> RegisterProjectSummary:
        items = self._project_entries(
            project_id,
            operation_label="view register summary",
        )
        today = date.today()
        return self._build_project_summary(items, today=today)

    def get_dashboard_snapshot(
        self,
        project_id: str,
        *,
        as_of: date | None = None,
    ) -> RegisterDashboardSnapshot:
        items = self._project_entries(
            project_id,
            operation_label="view dashboard register",
        )
        today = as_of or date.today()
        ordered = sorted(items, key=lambda item: item.triage_key(today))
        high_risks = tuple(
            item
            for item in ordered
            if item.entry_type == RegisterEntryType.RISK
            and item.severity in {
                RegisterEntrySeverity.HIGH,
                RegisterEntrySeverity.CRITICAL,
            }
            and item.status in {
                RegisterEntryStatus.OPEN,
                RegisterEntryStatus.IN_PROGRESS,
            }
        )
        return RegisterDashboardSnapshot(
            summary=self._build_project_summary(items, today=today),
            high_risks=high_risks,
        )

    def _project_entries(
        self,
        project_id: str,
        *,
        operation_label: str,
    ) -> list[RegisterEntry]:
        require_permission(
            self._user_session,
            "register.read",
            operation_label=operation_label,
        )
        require_project_permission(
            self._user_session,
            project_id,
            "register.read",
            operation_label=operation_label,
        )
        project = self._project_repo.get(project_id)
        if project is None:
            raise NotFoundError("Project not found.", code="PROJECT_NOT_FOUND")
        return self._register_repo.list_entries(project_id=project_id)

    @staticmethod
    def _build_project_summary(
        items: list[RegisterEntry],
        *,
        today: date,
    ) -> RegisterProjectSummary:
        active_items = [item for item in items if item.status in _ACTIVE_STATUSES]
        urgent = sorted(active_items, key=lambda item: item.triage_key(today))[:5]
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
                if item.is_overdue_on(today)
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

from __future__ import annotations

from datetime import date

from src.core.modules.project_management.access.scope_permissions import (
    filter_project_rows,
    require_project_permission,
)
from src.core.modules.project_management.application.common.module_guard import (
    ProjectManagementModuleGuardMixin,
)
from src.core.modules.project_management.application.common.pagination import (
    PageRequest,
    normalize_page_for_total,
)
from src.core.modules.project_management.application.risk.dto.responses.register_summary import (
    RegisterDashboardSnapshot,
    RegisterHighRiskItem,
    RegisterProjectSummary,
    RegisterUrgentItem,
)
from src.core.modules.project_management.contracts.reads import ReadSort
from src.core.modules.project_management.contracts.reads.register import (
    RegisterCatalogReader,
    RegisterCatalogReadPage,
)
from src.core.modules.project_management.contracts.repositories.projects.project import (
    ProjectRepository,
)
from src.core.modules.project_management.contracts.repositories.register.register import (
    RegisterEntryRepository,
)
from src.core.modules.project_management.domain.risk.register import (
    RegisterEntry,
    RegisterEntrySeverity,
    RegisterEntryStatus,
    RegisterEntryType,
)
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)
from src.core.platform.application.tenant.tenancy.tenant_context import (
    TenantContextService,
)
from src.core.platform.common.exceptions import ConfigurationError, NotFoundError
from src.core.platform.domain.security.auth.session import UserSessionContext

_ACTIVE_STATUSES = {
    RegisterEntryStatus.OPEN,
    RegisterEntryStatus.IN_PROGRESS,
    RegisterEntryStatus.MITIGATED,
}


from src.core.modules.project_management.application.risk.dto.responses.entries import (
    RegisterEntryResponseDto,
    RegisterCatalogResponseDto,
)
from src.core.modules.project_management.application.risk.mappers.entries import (
    map_register_entry,
    map_register_catalog,
)


class RegisterQueryHandler(ProjectManagementModuleGuardMixin):
    _project_repo: ProjectRepository
    _register_repo: RegisterEntryRepository
    _register_catalog_reader: RegisterCatalogReader | None
    _user_session: UserSessionContext | None
    _tenant_context_service: TenantContextService | None

    def __init__(
        self,
        *,
        project_repo: ProjectRepository,
        register_repo: RegisterEntryRepository,
        user_session: UserSessionContext | None = None,
        module_catalog_service=None,
        tenant_context_service: TenantContextService | None = None,
        register_catalog_reader: RegisterCatalogReader | None = None,
    ) -> None:
        self._project_repo = project_repo
        self._register_repo = register_repo
        self._user_session = user_session
        self._module_catalog_service = module_catalog_service
        self._tenant_context_service = tenant_context_service
        self._register_catalog_reader = register_catalog_reader

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
        sort_key: str = "triage",
        sort_direction: str = "asc",
    ) -> RegisterCatalogResponseDto:
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
            raise ConfigurationError("Register catalog reader is not configured.")
        page_request = PageRequest(page=page, page_size=page_size)
        sort = ReadSort.normalize(
            key=sort_key,
            direction=sort_direction,
            allowed_keys={
                "title",
                "entryCode",
                "typeLabel",
                "projectTitle",
                "ownerName",
                "severityLabel",
                "statusLabel",
                "dueDateLabel",
            },
            default_key="triage",
        )
        scope = self._tenant_context_service.require_active_scope_ids(
            operation_label="view register catalog"
        )
        allowed_project_ids: tuple[str, ...] | None = None
        if self._user_session is not None and self._user_session.is_project_restricted():
            allowed_project_ids = tuple(
                sorted(self._user_session.project_ids_for("register.read"))
            )
        effective_as_of = as_of or date.today()  # noqa: DTZ011

        def read_page(page_number: int) -> RegisterCatalogReadPage:
            assert self._register_catalog_reader is not None
            return self._register_catalog_reader.read_page(
                tenant_id=scope.tenant_id,
                organization_id=scope.organization_id,
                allowed_project_ids=allowed_project_ids,
                project_id=project_id,
                entry_type=entry_type,
                status=status,
                severity=severity,
                search_text=str(search_text or "").strip(),
                as_of=effective_as_of,
                page=page_number,
                page_size=page_request.page_size,
                sort=sort,
            )

        result = read_page(page_request.page)
        normalized_page = normalize_page_for_total(
            page=result.page,
            page_size=result.page_size,
            total=result.filtered_total,
        )
        if normalized_page != result.page:
            result = read_page(normalized_page)
        return map_register_catalog(result, as_of=effective_as_of)

    def get_entry(self, entry_id: str) -> RegisterEntryResponseDto:
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
        return map_register_entry(entry, project_name_by_id={}, as_of=date.today())

    def list_entries(
        self,
        *,
        project_id: str | None = None,
        entry_type: RegisterEntryType | None = None,
        status: RegisterEntryStatus | None = None,
        severity: RegisterEntrySeverity | None = None,
        as_of: date | None = None,
    ) -> list[RegisterEntryResponseDto]:
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
        triage_date = as_of or date.today()  # noqa: DTZ011
        return [map_register_entry(entry, project_name_by_id={}, as_of=triage_date) for entry in sorted(scoped_rows, key=lambda entry: entry.triage_key(triage_date))]

    def get_project_summary(self, project_id: str) -> RegisterProjectSummary:
        items = self._project_entries(
            project_id,
            operation_label="view register summary",
        )
        today = date.today()  # noqa: DTZ011
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
        today = as_of or date.today()  # noqa: DTZ011
        ordered = sorted(items, key=lambda item: item.triage_key(today))
        high_risks = tuple(
            RegisterHighRiskItem.from_entry(item)
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


__all__ = ["RegisterQueryHandler"]

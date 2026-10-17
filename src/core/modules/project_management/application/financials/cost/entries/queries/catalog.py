from __future__ import annotations

from src.core.modules.project_management.access.scope_permissions import (
    require_project_permission,
)
from src.core.modules.project_management.application.common.module_guard import (
    ProjectManagementModuleGuardMixin,
)
from src.core.modules.project_management.application.financials.cost.entries.capabilities import (
    build_cost_entry_capabilities,
    can_create_manual_actual,
)
from src.core.modules.project_management.application.financials.cost.entries.dto.responses.cost_entry import (
    CostEntryResponse,
)
from src.core.modules.project_management.application.financials.cost.entries.dto.responses.page import (
    CostEntryPage,
)
from src.core.modules.project_management.application.financials.cost.entries.mappers.cost_entry import (
    map_cost_entry,
)
from src.core.modules.project_management.contracts.financial_sources.reference import (
    FinancialSourceModule,
)
from src.core.modules.project_management.contracts.reads.financials.shared.sorting import (
    normalize_cost_entry_sort,
)
from src.core.modules.project_management.contracts.reads.pagination import normalize_offset_for_total
from src.core.modules.project_management.contracts.repositories.finance.cost_entries.cost_entry import (
    ProjectCostEntryRepository,
)
from src.core.modules.project_management.domain.financials.cost_entry import (
    ProjectCostEntry,
    ProjectCostEntryStatus,
)
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)
from src.core.platform.common.exceptions import (
    NotFoundError,
    ValidationError,
)


class ProjectCostEntryQueryHandler(ProjectManagementModuleGuardMixin):
    """Authorized reads for project cost entry query handler."""

    def __init__(
        self,
        *,
        entry_repo: ProjectCostEntryRepository,
        user_session=None,
        module_catalog_service=None,
    ) -> None:
        self._entry_repo = entry_repo
        self._user_session = user_session
        self._module_catalog_service = module_catalog_service

    def get_entry(self, entry_id: str) -> CostEntryResponse:
        require_permission(
            self._user_session,
            "finance.read",
            operation_label="view project cost entry",
        )
        entry = self._require_entry(entry_id)
        require_project_permission(
            self._user_session,
            entry.project_id,
            "finance.read",
            operation_label="view project cost entry",
        )
        return map_cost_entry(
            entry,
            capabilities=build_cost_entry_capabilities(
                entry, user_session=self._user_session
            ),
        )

    def list_for_project(
        self,
        project_id: str,
        *,
        status: ProjectCostEntryStatus | str | None = None,
        source_module: FinancialSourceModule | str | None = None,
        offset: int = 0,
        limit: int = 50,
        sort_key: str = "metaText",
        sort_direction: str = "desc",
    ) -> tuple[list[CostEntryResponse], int]:
        require_permission(
            self._user_session,
            "finance.read",
            operation_label="list project cost entries",
        )
        require_project_permission(
            self._user_session,
            project_id,
            "finance.read",
            operation_label="list project cost entries",
        )
        try:
            resolved_status = (
                ProjectCostEntryStatus(status) if status is not None else None
            )
        except ValueError as exc:
            raise ValidationError(
                "Project cost entry status is invalid.",
                code="PROJECT_COST_ENTRY_STATUS_INVALID",
            ) from exc
        try:
            resolved_source = (
                FinancialSourceModule(source_module)
                if source_module is not None
                else None
            )
        except ValueError as exc:
            raise ValidationError(
                "Project cost entry source is invalid.",
                code="PROJECT_COST_ENTRY_SOURCE_INVALID",
            ) from exc
        entries, total = self._entry_repo.list_for_project(
            project_id,
            status=resolved_status,
            source_module=resolved_source,
            offset=offset,
            limit=limit,
            sort=normalize_cost_entry_sort(
                key=sort_key,
                direction=sort_direction,
            ),
        )

        return [
            map_cost_entry(
                entry,
                capabilities=build_cost_entry_capabilities(
                    entry, user_session=self._user_session
                ),
            )
            for entry in entries
        ], total

    def list_page_for_project(
        self, project_id: str, *, status: str | None = None,
        source_module: str | None = None, offset: int = 0, limit: int = 50,
        sort_key: str = "metaText", sort_direction: str = "desc",
    ) -> CostEntryPage:
        sort = normalize_cost_entry_sort(key=sort_key, direction=sort_direction)
        entries, total = self.list_for_project(
            project_id, status=status, source_module=source_module, offset=offset,
            limit=limit, sort_key=sort.key, sort_direction=sort.direction.value,
        )
        normalized_offset = normalize_offset_for_total(offset=offset, limit=limit, total=total)
        if normalized_offset != offset:
            entries, total = self.list_for_project(
                project_id, status=status, source_module=source_module, offset=normalized_offset,
                limit=limit, sort_key=sort.key, sort_direction=sort.direction.value,
            )
        return CostEntryPage(
            items=tuple(entries), total=total, offset=normalized_offset, limit=limit,
            sort_key=sort.key, sort_direction=sort.direction.value,
            can_create_manual_actual=self.can_create_manual_entry(project_id),
        )

    def can_create_manual_entry(self, project_id: str) -> bool:
        return can_create_manual_actual(
            user_session=self._user_session,
            project_id=str(project_id or "").strip(),
        )

    def _require_entry(
        self, entry_id: str, *, for_update: bool = False
    ) -> ProjectCostEntry:
        entry = self._entry_repo.get(entry_id, for_update=for_update)
        if entry is None:
            raise NotFoundError(
                "Project cost entry not found.", code="PROJECT_COST_ENTRY_NOT_FOUND"
            )
        return entry


__all__ = ["ProjectCostEntryQueryHandler"]

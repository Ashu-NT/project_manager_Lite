from __future__ import annotations

from src.core.modules.project_management.access.scope_permissions import (
    require_project_permission,
)
from src.core.modules.project_management.application.common.module_guard import (
    ProjectManagementModuleGuardMixin,
)
from src.core.modules.project_management.application.financials.commitments.dto.responses.lines import (
    CommitmentLineResponse,
    CommitmentPage,
)
from src.core.modules.project_management.contracts.reads.pagination import normalize_offset_for_total
from src.core.modules.project_management.contracts.reads.financials.shared.sorting import (
    normalize_commitment_sort,
)
from src.core.modules.project_management.contracts.repositories.finance.commitments.commitment import (
    ProjectCommitmentRepository,
)
from src.core.modules.project_management.domain.financials.commitment import (
    ProjectCommitmentLine,
)
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)
from src.core.platform.common.exceptions import (
    NotFoundError,
    ValidationError,
)


class ProjectCommitmentQueryHandler(ProjectManagementModuleGuardMixin):
    """Authorized reads for project commitment query handler."""

    def __init__(
        self,
        *,
        commitment_repo: ProjectCommitmentRepository,
        user_session=None,
        module_catalog_service=None,
    ) -> None:
        self._commitment_repo = commitment_repo
        self._user_session = user_session
        self._module_catalog_service = module_catalog_service

    def get_line(self, line_id: str) -> ProjectCommitmentLine:
        require_permission(
            self._user_session, "finance.read", operation_label="view commitment"
        )
        line = self._require_line(line_id)
        require_project_permission(
            self._user_session,
            line.project_id,
            "finance.read",
            operation_label="view commitment",
        )
        return line

    def list_for_project(
        self,
        project_id: str,
        *,
        offset: int = 0,
        limit: int = 50,
        sort_key: str = "metaText",
        sort_direction: str = "desc",
        exposure: str = "",
    ) -> tuple[list[ProjectCommitmentLine], int]:
        require_permission(
            self._user_session, "finance.read", operation_label="list commitments"
        )
        require_project_permission(
            self._user_session,
            project_id,
            "finance.read",
            operation_label="list commitments",
        )
        if exposure not in {"", "open", "none"}:
            raise ValidationError(
                "Commitment exposure filter is invalid.",
                code="PROJECT_COMMITMENT_EXPOSURE_FILTER_INVALID",
            )
        return self._commitment_repo.list_lines_for_project(
            project_id,
            offset=offset,
            limit=limit,
            sort=normalize_commitment_sort(
                key=sort_key,
                direction=sort_direction,
            ),
            exposure=exposure,
        )

    def list_page_for_project(
        self, project_id: str, *, offset: int = 0, limit: int = 50,
        sort_key: str = "metaText", sort_direction: str = "desc", exposure: str = "",
    ) -> CommitmentPage:
        sort = normalize_commitment_sort(key=sort_key, direction=sort_direction)
        lines, total = self.list_for_project(
            project_id, offset=offset, limit=limit, sort_key=sort.key,
            sort_direction=sort.direction.value, exposure=exposure,
        )
        normalized_offset = normalize_offset_for_total(offset=offset, limit=limit, total=total)
        if normalized_offset != offset:
            lines, total = self.list_for_project(
                project_id, offset=normalized_offset, limit=limit, sort_key=sort.key,
                sort_direction=sort.direction.value, exposure=exposure,
            )
        return CommitmentPage(
            items=tuple(CommitmentLineResponse(
                id=line.id, purchase_order_line_id=line.purchase_order_line_id,
                state=line.state.value, amount=line.amount, matched_amount=line.matched_amount,
                remaining_amount=line.remaining_money.amount, currency_code=line.currency_code,
                task_id=line.task_id, ordered_quantity=line.ordered_quantity,
                quantity_unit=line.quantity_unit, order_date=line.order_date,
                expected_delivery_date=line.expected_delivery_date, source_revision=line.source_revision,
            ) for line in lines),
            total=total, offset=normalized_offset, limit=limit, sort_key=sort.key,
            sort_direction=sort.direction.value,
        )

    def _require_line(
        self, line_id: str, *, for_update: bool = False
    ) -> ProjectCommitmentLine:
        line = self._commitment_repo.get_line(line_id, for_update=for_update)
        if line is None:
            raise NotFoundError(
                "Project commitment line not found.",
                code="PROJECT_COMMITMENT_LINE_NOT_FOUND",
            )
        return line


__all__ = ["ProjectCommitmentQueryHandler"]

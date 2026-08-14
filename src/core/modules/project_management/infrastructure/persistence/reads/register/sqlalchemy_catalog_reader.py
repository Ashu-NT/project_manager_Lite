from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session

from src.core.modules.project_management.contracts.reads.sorting import ReadSort
from src.core.modules.project_management.contracts.reads.register import (
    RegisterCatalogReadItem,
    RegisterCatalogReadPage,
    RegisterCatalogSummary,
)
from src.core.modules.project_management.domain.risk.register import (
    RegisterEntrySeverity,
    RegisterEntryStatus,
    RegisterEntryType,
)
from src.core.modules.project_management.infrastructure.persistence.mappers.register import (
    register_entry_from_orm,
)
from src.core.modules.project_management.infrastructure.persistence.orm.project import ProjectORM
from src.core.modules.project_management.infrastructure.persistence.orm.register import RegisterEntryORM
from src.core.modules.project_management.infrastructure.persistence.reads.sorting import stable_order_by


_ACTIVE_STATUSES = (
    RegisterEntryStatus.OPEN,
    RegisterEntryStatus.IN_PROGRESS,
    RegisterEntryStatus.MITIGATED,
)


def _contains_pattern(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped.lower()}%"


class SqlAlchemyRegisterCatalogReader:
    def __init__(self, *, session: Session) -> None:
        self._session = session

    def read_page(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        allowed_project_ids: tuple[str, ...] | None,
        project_id: str | None,
        entry_type: RegisterEntryType | None,
        status: RegisterEntryStatus | None,
        severity: RegisterEntrySeverity | None,
        search_text: str,
        as_of: date,
        page: int,
        page_size: int,
        sort: ReadSort,
    ) -> RegisterCatalogReadPage:
        if allowed_project_ids == ():
            return RegisterCatalogReadPage(page=page, page_size=page_size, sort=sort)
        scope_filters = [
            ProjectORM.tenant_id == tenant_id,
            ProjectORM.organization_id == organization_id,
        ]
        if allowed_project_ids is not None:
            scope_filters.append(RegisterEntryORM.project_id.in_(allowed_project_ids))
        if project_id:
            scope_filters.append(RegisterEntryORM.project_id == project_id)

        scope_row = self._session.execute(
            select(
                func.count(RegisterEntryORM.id),
                func.sum(case((RegisterEntryORM.entry_type == RegisterEntryType.RISK, 1), else_=0)),
            )
            .select_from(RegisterEntryORM)
            .join(ProjectORM, ProjectORM.id == RegisterEntryORM.project_id)
            .where(*scope_filters)
        ).one()

        filtered = list(scope_filters)
        if entry_type is not None:
            filtered.append(RegisterEntryORM.entry_type == entry_type)
        if status is not None:
            filtered.append(RegisterEntryORM.status == status)
        if severity is not None:
            filtered.append(RegisterEntryORM.severity == severity)
        normalized_search = str(search_text or "").strip()
        if normalized_search:
            pattern = _contains_pattern(normalized_search)
            filtered.append(
                or_(
                    *(
                        func.lower(func.coalesce(column, "")).like(pattern, escape="\\")
                        for column in (
                            RegisterEntryORM.entry_code,
                            RegisterEntryORM.title,
                            RegisterEntryORM.description,
                            RegisterEntryORM.owner_name,
                            RegisterEntryORM.impact_summary,
                            RegisterEntryORM.response_plan,
                            ProjectORM.name,
                        )
                    )
                )
            )

        active = RegisterEntryORM.status.in_(_ACTIVE_STATUSES)
        overdue = active & RegisterEntryORM.due_date.is_not(None) & (RegisterEntryORM.due_date < as_of)
        due_soon = active & RegisterEntryORM.due_date.between(as_of, as_of + timedelta(days=7))
        filtered_row = self._session.execute(
            select(
                func.count(RegisterEntryORM.id),
                func.sum(case(((RegisterEntryORM.entry_type == RegisterEntryType.RISK) & active, 1), else_=0)),
                func.sum(case(((RegisterEntryORM.entry_type == RegisterEntryType.ISSUE) & active, 1), else_=0)),
                func.sum(case(((RegisterEntryORM.entry_type == RegisterEntryType.CHANGE)
                               & RegisterEntryORM.status.in_((RegisterEntryStatus.OPEN, RegisterEntryStatus.IN_PROGRESS)), 1), else_=0)),
                func.sum(case((active, 1), else_=0)),
                func.sum(case((RegisterEntryORM.severity == RegisterEntrySeverity.CRITICAL, 1), else_=0)),
                func.sum(case((overdue, 1), else_=0)),
                func.sum(case((due_soon, 1), else_=0)),
            )
            .select_from(RegisterEntryORM)
            .join(ProjectORM, ProjectORM.id == RegisterEntryORM.project_id)
            .where(*filtered)
        ).one()
        filtered_total = int(filtered_row[0] or 0)
        summary = RegisterCatalogSummary(
            scope_total=int(scope_row[0] or 0),
            scope_risk_total=int(scope_row[1] or 0),
            open_risks=int(filtered_row[1] or 0),
            open_issues=int(filtered_row[2] or 0),
            pending_changes=int(filtered_row[3] or 0),
            active=int(filtered_row[4] or 0),
            critical=int(filtered_row[5] or 0),
            overdue=int(filtered_row[6] or 0),
            due_soon=int(filtered_row[7] or 0),
        )

        base_rows = (
            select(RegisterEntryORM, ProjectORM.name)
            .join(ProjectORM, ProjectORM.id == RegisterEntryORM.project_id)
            .where(*filtered)
        )
        triage_order = (
            case(
                (RegisterEntryORM.severity == RegisterEntrySeverity.CRITICAL, 0),
                (RegisterEntryORM.severity == RegisterEntrySeverity.HIGH, 1),
                (RegisterEntryORM.severity == RegisterEntrySeverity.MEDIUM, 2),
                else_=3,
            ),
            case((overdue, 0), else_=1),
            RegisterEntryORM.due_date.is_(None),
            RegisterEntryORM.due_date,
            func.lower(RegisterEntryORM.title),
            RegisterEntryORM.id,
        )
        sort_expressions = {
            "title": (func.lower(RegisterEntryORM.title),),
            "entryCode": (func.lower(func.coalesce(RegisterEntryORM.entry_code, "")),),
            "typeLabel": (RegisterEntryORM.entry_type,),
            "projectTitle": (func.lower(ProjectORM.name),),
            "ownerName": (func.lower(func.coalesce(RegisterEntryORM.owner_name, "")),),
            "severityLabel": (RegisterEntryORM.severity,),
            "statusLabel": (RegisterEntryORM.status,),
            "dueDateLabel": (RegisterEntryORM.due_date,),
        }
        page_order = (
            triage_order
            if sort.key == "triage"
            else stable_order_by(
                sort=sort,
                expressions=sort_expressions,
                default_key="title",
                tie_breakers=(RegisterEntryORM.id,),
            )
        )
        page_rows = self._session.execute(
            base_rows.order_by(*page_order)
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        urgent_rows = self._session.execute(
            base_rows.where(active).order_by(*triage_order).limit(5)
        ).all()

        def to_item(row) -> RegisterCatalogReadItem:
            return RegisterCatalogReadItem(
                entry=register_entry_from_orm(row[0]),
                project_name=str(row[1] or ""),
            )

        return RegisterCatalogReadPage(
            items=tuple(to_item(row) for row in page_rows),
            urgent_items=tuple(to_item(row) for row in urgent_rows),
            filtered_total=filtered_total,
            page=page,
            page_size=page_size,
            summary=summary,
            sort=sort,
        )


__all__ = ["SqlAlchemyRegisterCatalogReader"]

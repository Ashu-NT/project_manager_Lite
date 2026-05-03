from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from src.core.modules.project_management.application.financials import (
    CostService,
    FinanceService,
)
from src.core.modules.project_management.application.projects import ProjectService
from src.core.modules.project_management.application.tasks import TaskService
from src.core.modules.project_management.domain.enums import CostType


@dataclass(frozen=True)
class FinancialProjectOptionDescriptor:
    value: str
    label: str


@dataclass(frozen=True)
class FinancialTaskOptionDescriptor:
    value: str
    label: str


@dataclass(frozen=True)
class FinancialCostTypeDescriptor:
    value: str
    label: str


@dataclass(frozen=True)
class FinancialCostItemDto:
    id: str
    project_id: str
    task_id: str | None
    task_name: str
    description: str
    planned_amount: float
    planned_amount_label: str
    committed_amount: float
    committed_amount_label: str
    actual_amount: float
    actual_amount_label: str
    cost_type: str
    cost_type_label: str
    incurred_date: date | None
    incurred_date_label: str
    currency_code: str | None
    version: int


@dataclass(frozen=True)
class FinancialCreateCommand:
    project_id: str
    description: str
    planned_amount: float
    task_id: str | None = None
    cost_type: str = CostType.OVERHEAD.value
    committed_amount: float = 0.0
    actual_amount: float = 0.0
    incurred_date: date | None = None
    currency_code: str | None = None


@dataclass(frozen=True)
class FinancialUpdateCommand:
    cost_id: str
    description: str
    planned_amount: float
    task_id: str | None = None
    cost_type: str = CostType.OVERHEAD.value
    committed_amount: float = 0.0
    actual_amount: float = 0.0
    incurred_date: date | None = None
    currency_code: str | None = None
    expected_version: int | None = None


@dataclass(frozen=True)
class FinancialLedgerRowDto:
    source_label: str
    stage: str
    amount: float
    amount_label: str
    reference_label: str
    task_name: str
    resource_name: str
    occurred_on: date | None
    occurred_on_label: str
    included_in_policy: bool


@dataclass(frozen=True)
class FinancialPeriodRowDto:
    period_key: str
    planned: float
    planned_label: str
    committed: float
    committed_label: str
    actual: float
    actual_label: str
    forecast: float
    forecast_label: str
    exposure: float
    exposure_label: str


@dataclass(frozen=True)
class FinancialAnalyticsRowDto:
    dimension: str
    key: str
    label: str
    planned: float
    planned_label: str
    committed: float
    committed_label: str
    actual: float
    actual_label: str
    forecast: float
    forecast_label: str
    exposure: float
    exposure_label: str


@dataclass(frozen=True)
class FinancialSnapshotDto:
    project_id: str
    project_currency: str | None
    budget: float
    budget_label: str
    planned: float
    planned_label: str
    committed: float
    committed_label: str
    actual: float
    actual_label: str
    exposure: float
    exposure_label: str
    available: float | None
    available_label: str
    ledger: tuple[FinancialLedgerRowDto, ...]
    cashflow: tuple[FinancialPeriodRowDto, ...]
    by_source: tuple[FinancialAnalyticsRowDto, ...]
    by_cost_type: tuple[FinancialAnalyticsRowDto, ...]
    by_resource: tuple[FinancialAnalyticsRowDto, ...]
    by_task: tuple[FinancialAnalyticsRowDto, ...]
    notes: tuple[str, ...]


class ProjectManagementFinancialsDesktopApi:
    def __init__(
        self,
        *,
        project_service: ProjectService | None = None,
        task_service: TaskService | None = None,
        cost_service: CostService | None = None,
        finance_service: FinanceService | None = None,
    ) -> None:
        self._project_service = project_service
        self._task_service = task_service
        self._cost_service = cost_service
        self._finance_service = finance_service

    def list_projects(self) -> tuple[FinancialProjectOptionDescriptor, ...]:
        if self._project_service is None:
            return ()
        projects = sorted(
            self._project_service.list_projects(),
            key=lambda project: (project.name or "").casefold(),
        )
        return tuple(
            FinancialProjectOptionDescriptor(value=project.id, label=project.name)
            for project in projects
        )

    def list_cost_types(self) -> tuple[FinancialCostTypeDescriptor, ...]:
        return tuple(
            FinancialCostTypeDescriptor(
                value=cost_type.value,
                label=_format_enum_label(cost_type.value),
            )
            for cost_type in CostType
        )

    def list_tasks(self, project_id: str) -> tuple[FinancialTaskOptionDescriptor, ...]:
        if self._task_service is None or not project_id:
            return ()
        tasks = sorted(
            self._task_service.list_tasks_for_project(project_id),
            key=lambda task: (
                task.start_date or date.max,
                (task.name or "").casefold(),
            ),
        )
        return tuple(
            FinancialTaskOptionDescriptor(value=task.id, label=task.name)
            for task in tasks
        )

    def list_cost_items(self, project_id: str) -> tuple[FinancialCostItemDto, ...]:
        if self._cost_service is None or not project_id:
            return ()
        task_lookup = self._task_lookup(project_id)
        items = sorted(
            self._cost_service.list_cost_items_for_project(project_id),
            key=lambda item: (
                item.incurred_date or date.max,
                (item.description or "").casefold(),
            ),
        )
        return tuple(
            self._serialize_cost_item(item, task_lookup=task_lookup)
            for item in items
        )

    def create_cost_item(self, command: FinancialCreateCommand) -> FinancialCostItemDto:
        service = self._require_cost_service()
        item = service.add_cost_item(
            command.project_id,
            description=command.description,
            planned_amount=command.planned_amount,
            task_id=command.task_id,
            cost_type=_coerce_cost_type(command.cost_type),
            committed_amount=command.committed_amount,
            actual_amount=command.actual_amount,
            incurred_date=command.incurred_date,
            currency_code=command.currency_code,
        )
        return self._serialize_cost_item(
            item,
            task_lookup=self._task_lookup(command.project_id),
        )

    def update_cost_item(self, command: FinancialUpdateCommand) -> FinancialCostItemDto:
        service = self._require_cost_service()
        item = service.update_cost_item(
            command.cost_id,
            description=command.description,
            planned_amount=command.planned_amount,
            committed_amount=command.committed_amount,
            actual_amount=command.actual_amount,
            cost_type=_coerce_cost_type(command.cost_type),
            incurred_date=command.incurred_date,
            currency_code=command.currency_code,
            expected_version=command.expected_version,
        )
        return self._serialize_cost_item(
            item,
            task_lookup=self._task_lookup(item.project_id),
        )

    def delete_cost_item(self, cost_id: str) -> None:
        self._require_cost_service().delete_cost_item(cost_id)

    def get_finance_snapshot(self, project_id: str) -> FinancialSnapshotDto:
        if not project_id:
            return _empty_snapshot(project_id="")
        if self._finance_service is None:
            return _empty_snapshot(
                project_id=project_id,
                notes=("Project management financials desktop API is not connected.",),
            )
        snapshot = self._finance_service.get_finance_snapshot(project_id)
        currency = (snapshot.project_currency or "").strip().upper() or None
        return FinancialSnapshotDto(
            project_id=project_id,
            project_currency=currency,
            budget=float(snapshot.budget or 0.0),
            budget_label=_format_money(snapshot.budget, currency),
            planned=float(snapshot.planned or 0.0),
            planned_label=_format_money(snapshot.planned, currency),
            committed=float(snapshot.committed or 0.0),
            committed_label=_format_money(snapshot.committed, currency),
            actual=float(snapshot.actual or 0.0),
            actual_label=_format_money(snapshot.actual, currency),
            exposure=float(snapshot.exposure or 0.0),
            exposure_label=_format_money(snapshot.exposure, currency),
            available=(
                None if snapshot.available is None else float(snapshot.available)
            ),
            available_label=(
                "Open"
                if snapshot.available is None
                else _format_money(snapshot.available, currency)
            ),
            ledger=tuple(
                FinancialLedgerRowDto(
                    source_label=row.source_label,
                    stage=_format_enum_label(row.stage),
                    amount=float(row.amount or 0.0),
                    amount_label=_format_money(row.amount, row.currency or currency),
                    reference_label=row.reference_label,
                    task_name=row.task_name or "Not linked to a task",
                    resource_name=row.resource_name or "No resource",
                    occurred_on=row.occurred_on,
                    occurred_on_label=_format_date(row.occurred_on),
                    included_in_policy=bool(row.included_in_policy),
                )
                for row in snapshot.ledger
            ),
            cashflow=tuple(
                FinancialPeriodRowDto(
                    period_key=row.period_key,
                    planned=float(row.planned or 0.0),
                    planned_label=_format_money(row.planned, currency),
                    committed=float(row.committed or 0.0),
                    committed_label=_format_money(row.committed, currency),
                    actual=float(row.actual or 0.0),
                    actual_label=_format_money(row.actual, currency),
                    forecast=float(row.forecast or 0.0),
                    forecast_label=_format_money(row.forecast, currency),
                    exposure=float(row.exposure or 0.0),
                    exposure_label=_format_money(row.exposure, currency),
                )
                for row in snapshot.cashflow
            ),
            by_source=_serialize_analytics(snapshot.by_source, currency),
            by_cost_type=_serialize_analytics(snapshot.by_cost_type, currency),
            by_resource=_serialize_analytics(snapshot.by_resource, currency),
            by_task=_serialize_analytics(snapshot.by_task, currency),
            notes=tuple(snapshot.notes or ()),
        )

    def _require_cost_service(self) -> CostService:
        if self._cost_service is None:
            raise RuntimeError("Project management financials desktop API is not connected.")
        return self._cost_service

    def _task_lookup(self, project_id: str) -> dict[str, str]:
        return {
            option.value: option.label
            for option in self.list_tasks(project_id)
        }

    @staticmethod
    def _serialize_cost_item(
        item,
        *,
        task_lookup: dict[str, str],
    ) -> FinancialCostItemDto:
        resolved_currency = (getattr(item, "currency_code", None) or "").strip().upper() or None
        cost_type = _coerce_cost_type(getattr(item, "cost_type", None))
        task_id = str(getattr(item, "task_id", "") or "").strip() or None
        return FinancialCostItemDto(
            id=item.id,
            project_id=item.project_id,
            task_id=task_id,
            task_name=task_lookup.get(task_id or "", "Not linked to a task"),
            description=(item.description or "").strip(),
            planned_amount=float(getattr(item, "planned_amount", 0.0) or 0.0),
            planned_amount_label=_format_money(
                getattr(item, "planned_amount", 0.0),
                resolved_currency,
            ),
            committed_amount=float(getattr(item, "committed_amount", 0.0) or 0.0),
            committed_amount_label=_format_money(
                getattr(item, "committed_amount", 0.0),
                resolved_currency,
            ),
            actual_amount=float(getattr(item, "actual_amount", 0.0) or 0.0),
            actual_amount_label=_format_money(
                getattr(item, "actual_amount", 0.0),
                resolved_currency,
            ),
            cost_type=cost_type.value,
            cost_type_label=_format_enum_label(cost_type.value),
            incurred_date=getattr(item, "incurred_date", None),
            incurred_date_label=_format_date(getattr(item, "incurred_date", None)),
            currency_code=resolved_currency,
            version=int(getattr(item, "version", 1) or 1),
        )


def build_project_management_financials_desktop_api(
    *,
    project_service: ProjectService | None = None,
    task_service: TaskService | None = None,
    cost_service: CostService | None = None,
    finance_service: FinanceService | None = None,
) -> ProjectManagementFinancialsDesktopApi:
    return ProjectManagementFinancialsDesktopApi(
        project_service=project_service,
        task_service=task_service,
        cost_service=cost_service,
        finance_service=finance_service,
    )


def _serialize_analytics(
    rows,
    currency: str | None,
) -> tuple[FinancialAnalyticsRowDto, ...]:
    return tuple(
        FinancialAnalyticsRowDto(
            dimension=row.dimension,
            key=row.key,
            label=row.label,
            planned=float(row.planned or 0.0),
            planned_label=_format_money(row.planned, currency),
            committed=float(row.committed or 0.0),
            committed_label=_format_money(row.committed, currency),
            actual=float(row.actual or 0.0),
            actual_label=_format_money(row.actual, currency),
            forecast=float(row.forecast or 0.0),
            forecast_label=_format_money(row.forecast, currency),
            exposure=float(row.exposure or 0.0),
            exposure_label=_format_money(row.exposure, currency),
        )
        for row in rows
    )


def _empty_snapshot(
    *,
    project_id: str,
    notes: tuple[str, ...] = (),
) -> FinancialSnapshotDto:
    return FinancialSnapshotDto(
        project_id=project_id,
        project_currency=None,
        budget=0.0,
        budget_label="0.00",
        planned=0.0,
        planned_label="0.00",
        committed=0.0,
        committed_label="0.00",
        actual=0.0,
        actual_label="0.00",
        exposure=0.0,
        exposure_label="0.00",
        available=None,
        available_label="Open",
        ledger=(),
        cashflow=(),
        by_source=(),
        by_cost_type=(),
        by_resource=(),
        by_task=(),
        notes=notes,
    )


def _coerce_cost_type(value: str | CostType | None) -> CostType:
    if isinstance(value, CostType):
        return value
    normalized_value = str(value or CostType.OVERHEAD.value).strip().upper()
    try:
        return CostType(normalized_value)
    except ValueError as exc:
        raise ValueError(f"Unsupported cost type: {normalized_value}.") from exc


def _format_enum_label(value: str) -> str:
    return value.replace("_", " ").title()


def _format_money(value: float | None, currency: str | None) -> str:
    amount = float(value or 0.0)
    resolved_currency = (currency or "").strip().upper()
    if resolved_currency:
        return f"{resolved_currency} {amount:,.2f}"
    return f"{amount:,.2f}"


def _format_date(value: date | None) -> str:
    if value is None:
        return "Not set"
    return value.isoformat()


__all__ = [
    "FinancialAnalyticsRowDto",
    "FinancialCostItemDto",
    "FinancialCostTypeDescriptor",
    "FinancialCreateCommand",
    "FinancialLedgerRowDto",
    "FinancialPeriodRowDto",
    "FinancialProjectOptionDescriptor",
    "FinancialSnapshotDto",
    "FinancialTaskOptionDescriptor",
    "FinancialUpdateCommand",
    "ProjectManagementFinancialsDesktopApi",
    "build_project_management_financials_desktop_api",
]

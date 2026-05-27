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
    forecast_amount: float
    forecast_amount_label: str
    commitment_status: str
    commitment_status_label: str
    vendor_reference: str | None
    cost_type: str
    cost_type_label: str
    incurred_date: date | None
    incurred_date_label: str
    currency_code: str | None
    version: int


@dataclass(frozen=True)
class FinancialForecastDto:
    project_id: str
    method: str
    bac: float
    bac_label: str
    ac: float
    ac_label: str
    ev: float
    ev_label: str
    etc: float
    etc_label: str
    eac: float
    eac_label: str
    vac: float
    vac_label: str
    cpi: float
    cpi_label: str
    is_over_budget: bool
    exceeds_threshold: bool
    threshold_percent: float


@dataclass(frozen=True)
class FinancialCommitmentSummaryDto:
    project_id: str
    planned_total: float
    planned_label: str
    uncommitted_total: float
    uncommitted_label: str
    committed_total: float
    committed_label: str
    invoiced_total: float
    invoiced_label: str
    paid_total: float
    paid_label: str
    exposure: float
    exposure_label: str
    commitment_rate_pct: float


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
class ProjectRequisitionDesktopDto:
    id: str
    requisition_number: str
    status: str
    status_label: str
    purpose: str
    needed_by_date: date | None
    priority: str
    notes: str


@dataclass(frozen=True)
class ProjectProcurementCommitmentSummary:
    project_id: str
    total_requisitions: int
    open_count: int
    approved_count: int
    closed_count: int
    cancelled_count: int


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
        procurement_service: object | None = None,
    ) -> None:
        self._project_service = project_service
        self._task_service = task_service
        self._cost_service = cost_service
        self._finance_service = finance_service
        self._procurement_service = procurement_service

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

    def get_cost_forecast(
        self,
        project_id: str,
        percent_complete: float = 0.0,
        method: str = "bac_over_cpi",
        threshold_percent: float = 10.0,
    ) -> FinancialForecastDto:
        currency = self._project_currency(project_id)
        if not project_id or self._cost_service is None:
            return _empty_forecast(project_id, currency)
        items = self._cost_service.list_cost_items_for_project(project_id)
        bac = sum(getattr(i, "planned_amount", 0.0) or 0.0 for i in items)
        ac = sum(getattr(i, "actual_amount", 0.0) or 0.0 for i in items)
        pct = max(0.0, min(1.0, percent_complete))
        ev = bac * pct
        cpi = (ev / ac) if ac > 0 else 0.0
        etc, eac = _compute_etc_eac(method, bac, ac, ev, cpi, items)
        vac = bac - eac
        threshold = bac * (1.0 + threshold_percent / 100.0)
        exceeds = (eac > threshold) if bac > 0 else False
        return FinancialForecastDto(
            project_id=project_id,
            method=method,
            bac=bac, bac_label=_format_money(bac, currency),
            ac=ac, ac_label=_format_money(ac, currency),
            ev=ev, ev_label=_format_money(ev, currency),
            etc=etc, etc_label=_format_money(etc, currency),
            eac=eac, eac_label=_format_money(eac, currency),
            vac=vac, vac_label=_format_money(vac, currency),
            cpi=round(cpi, 3), cpi_label=f"{cpi:.3f}",
            is_over_budget=eac > bac,
            exceeds_threshold=exceeds,
            threshold_percent=threshold_percent,
        )

    def get_commitment_summary(self, project_id: str) -> FinancialCommitmentSummaryDto:
        currency = self._project_currency(project_id)
        if not project_id or self._cost_service is None:
            return _empty_commitment_summary(project_id, currency)
        items = self._cost_service.list_cost_items_for_project(project_id)
        uncommitted = sum(
            getattr(i, "planned_amount", 0.0) or 0.0 for i in items
            if _commitment_status_value(i) == "UNCOMMITTED"
        )
        committed = sum(
            getattr(i, "committed_amount", 0.0) or 0.0 for i in items
            if _commitment_status_value(i) == "COMMITTED"
        )
        invoiced = sum(
            getattr(i, "committed_amount", 0.0) or 0.0 for i in items
            if _commitment_status_value(i) == "INVOICED"
        )
        paid = sum(
            getattr(i, "actual_amount", 0.0) or 0.0 for i in items
            if _commitment_status_value(i) == "PAID"
        )
        planned = sum(getattr(i, "planned_amount", 0.0) or 0.0 for i in items)
        actual = sum(getattr(i, "actual_amount", 0.0) or 0.0 for i in items)
        exposure = max(0.0, committed - actual)
        rate_pct = round((committed / planned * 100.0) if planned > 0 else 0.0, 1)
        return FinancialCommitmentSummaryDto(
            project_id=project_id,
            planned_total=planned, planned_label=_format_money(planned, currency),
            uncommitted_total=uncommitted, uncommitted_label=_format_money(uncommitted, currency),
            committed_total=committed, committed_label=_format_money(committed, currency),
            invoiced_total=invoiced, invoiced_label=_format_money(invoiced, currency),
            paid_total=paid, paid_label=_format_money(paid, currency),
            exposure=exposure, exposure_label=_format_money(exposure, currency),
            commitment_rate_pct=rate_pct,
        )

    def list_project_requisitions(self, project_id: str) -> tuple[ProjectRequisitionDesktopDto, ...]:
        if not project_id or self._procurement_service is None:
            return ()
        list_requisitions = getattr(self._procurement_service, "list_requisitions", None)
        if not callable(list_requisitions):
            return ()
        try:
            all_requisitions = list_requisitions(limit=500)
        except Exception:
            return ()
        project_requisitions = [
            r for r in all_requisitions
            if getattr(r, "source_reference_type", "") == "project"
            and getattr(r, "source_reference_id", "") == project_id
        ]
        return tuple(
            self._serialize_requisition(r)
            for r in sorted(
                project_requisitions,
                key=lambda r: getattr(r, "needed_by_date", None) or date.max,
            )
        )

    def get_project_procurement_commitments(self, project_id: str) -> ProjectProcurementCommitmentSummary:
        requisitions = self.list_project_requisitions(project_id)
        open_statuses = {"DRAFT", "SUBMITTED", "UNDER_REVIEW", "PARTIALLY_SOURCED"}
        approved_statuses = {"APPROVED"}
        closed_statuses = {"FULLY_SOURCED", "CLOSED"}
        cancelled_statuses = {"REJECTED", "CANCELLED"}
        return ProjectProcurementCommitmentSummary(
            project_id=project_id,
            total_requisitions=len(requisitions),
            open_count=sum(1 for r in requisitions if r.status in open_statuses),
            approved_count=sum(1 for r in requisitions if r.status in approved_statuses),
            closed_count=sum(1 for r in requisitions if r.status in closed_statuses),
            cancelled_count=sum(1 for r in requisitions if r.status in cancelled_statuses),
        )

    def _project_currency(self, project_id: str) -> str | None:
        if not project_id or self._project_service is None:
            return None
        project = self._project_service.get_project(project_id)
        if project is None:
            return None
        return (getattr(project, "currency", None) or "").strip().upper() or None

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
        planned = float(getattr(item, "planned_amount", 0.0) or 0.0)
        committed = float(getattr(item, "committed_amount", 0.0) or 0.0)
        actual = float(getattr(item, "actual_amount", 0.0) or 0.0)
        raw_forecast = getattr(item, "forecast_amount", None)
        effective_forecast = float(raw_forecast) if raw_forecast is not None else planned
        commitment_status = _commitment_status_value(item)
        return FinancialCostItemDto(
            id=item.id,
            project_id=item.project_id,
            task_id=task_id,
            task_name=task_lookup.get(task_id or "", "Not linked to a task"),
            description=(item.description or "").strip(),
            planned_amount=planned,
            planned_amount_label=_format_money(planned, resolved_currency),
            committed_amount=committed,
            committed_amount_label=_format_money(committed, resolved_currency),
            actual_amount=actual,
            actual_amount_label=_format_money(actual, resolved_currency),
            forecast_amount=effective_forecast,
            forecast_amount_label=_format_money(effective_forecast, resolved_currency),
            commitment_status=commitment_status,
            commitment_status_label=_format_enum_label(commitment_status),
            vendor_reference=str(getattr(item, "vendor_reference", None) or "").strip() or None,
            cost_type=cost_type.value,
            cost_type_label=_format_enum_label(cost_type.value),
            incurred_date=getattr(item, "incurred_date", None),
            incurred_date_label=_format_date(getattr(item, "incurred_date", None)),
            currency_code=resolved_currency,
            version=int(getattr(item, "version", 1) or 1),
        )


    @staticmethod
    def _serialize_requisition(requisition) -> ProjectRequisitionDesktopDto:
        status_value = str(
            getattr(getattr(requisition, "status", None), "value", None)
            or getattr(requisition, "status", "")
            or ""
        )
        return ProjectRequisitionDesktopDto(
            id=requisition.id,
            requisition_number=str(getattr(requisition, "requisition_number", "") or ""),
            status=status_value,
            status_label=status_value.replace("_", " ").title(),
            purpose=str(getattr(requisition, "purpose", "") or ""),
            needed_by_date=getattr(requisition, "needed_by_date", None),
            priority=str(getattr(requisition, "priority", "") or ""),
            notes=str(getattr(requisition, "notes", "") or ""),
        )


def build_project_management_financials_desktop_api(
    *,
    project_service: ProjectService | None = None,
    task_service: TaskService | None = None,
    cost_service: CostService | None = None,
    finance_service: FinanceService | None = None,
    procurement_service: object | None = None,
) -> ProjectManagementFinancialsDesktopApi:
    return ProjectManagementFinancialsDesktopApi(
        project_service=project_service,
        task_service=task_service,
        cost_service=cost_service,
        finance_service=finance_service,
        procurement_service=procurement_service,
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


def _commitment_status_value(item) -> str:
    raw = getattr(item, "commitment_status", None)
    if raw is None:
        return "UNCOMMITTED"
    if hasattr(raw, "value"):
        return str(raw.value).upper()
    return str(raw).upper()


def _compute_etc_eac(
    method: str,
    bac: float,
    ac: float,
    ev: float,
    cpi: float,
    items,
) -> tuple[float, float]:
    if method == "manual":
        forecast_sum = sum(
            (getattr(i, "forecast_amount", None) or getattr(i, "planned_amount", 0.0) or 0.0)
            for i in items
        )
        etc = max(0.0, forecast_sum - ac)
        return etc, ac + etc
    if method == "bac_over_cpi":
        eac = (bac / cpi) if cpi > 0 else bac
        return eac - ac, eac
    if method == "ac_etc_plan":
        etc = max(0.0, bac - ev)
        return etc, ac + etc
    if method == "ac_etc_cpi":
        remaining = max(0.0, bac - ev)
        etc = (remaining / cpi) if cpi > 0 else remaining
        return etc, ac + etc
    etc = max(0.0, bac - ac)
    return etc, bac


def _empty_forecast(project_id: str, currency: str | None) -> FinancialForecastDto:
    return FinancialForecastDto(
        project_id=project_id, method="bac_over_cpi",
        bac=0.0, bac_label=_format_money(0.0, currency),
        ac=0.0, ac_label=_format_money(0.0, currency),
        ev=0.0, ev_label=_format_money(0.0, currency),
        etc=0.0, etc_label=_format_money(0.0, currency),
        eac=0.0, eac_label=_format_money(0.0, currency),
        vac=0.0, vac_label=_format_money(0.0, currency),
        cpi=0.0, cpi_label="0.000",
        is_over_budget=False, exceeds_threshold=False, threshold_percent=10.0,
    )


def _empty_commitment_summary(project_id: str, currency: str | None) -> FinancialCommitmentSummaryDto:
    z = _format_money(0.0, currency)
    return FinancialCommitmentSummaryDto(
        project_id=project_id,
        planned_total=0.0, planned_label=z,
        uncommitted_total=0.0, uncommitted_label=z,
        committed_total=0.0, committed_label=z,
        invoiced_total=0.0, invoiced_label=z,
        paid_total=0.0, paid_label=z,
        exposure=0.0, exposure_label=z,
        commitment_rate_pct=0.0,
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
    "FinancialCommitmentSummaryDto",
    "FinancialCostItemDto",
    "FinancialCostTypeDescriptor",
    "FinancialCreateCommand",
    "FinancialForecastDto",
    "FinancialLedgerRowDto",
    "FinancialPeriodRowDto",
    "FinancialProjectOptionDescriptor",
    "FinancialSnapshotDto",
    "FinancialTaskOptionDescriptor",
    "FinancialUpdateCommand",
    "ProjectManagementFinancialsDesktopApi",
    "ProjectProcurementCommitmentSummary",
    "ProjectRequisitionDesktopDto",
    "build_project_management_financials_desktop_api",
]

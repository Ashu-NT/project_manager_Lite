from datetime import date
from types import SimpleNamespace

from src.ui_qml.modules.project_management.context import ProjectManagementWorkspaceCatalog
from src.ui_qml.modules.project_management.presenters import (
    ProjectFinancialsWorkspacePresenter,
)
from src.core.modules.project_management.api.desktop import (
    build_project_management_financials_desktop_api,
)
from src.core.modules.project_management.domain.enums import CostType
from src.core.modules.project_management.application.financials import (
    CommitmentSummary,
    CostForecastResult,
)


class _FakeTaskOptionService:
    def __init__(self, tasks_by_project: dict[str, list[SimpleNamespace]]) -> None:
        self._tasks_by_project = tasks_by_project

    def list_tasks_for_project(self, project_id: str) -> list[SimpleNamespace]:
        return list(self._tasks_by_project.get(project_id, []))


class _FakeFinancialCostService:
    def __init__(self, costs_by_project: dict[str, list[SimpleNamespace]]) -> None:
        self._costs_by_project = costs_by_project

    def list_cost_items_for_project(self, project_id: str) -> list[SimpleNamespace]:
        return list(self._costs_by_project.get(project_id, []))


class _FakeFinanceDesktopService:
    def __init__(self, snapshots_by_project: dict[str, SimpleNamespace]) -> None:
        self._snapshots_by_project = snapshots_by_project

    def get_finance_snapshot(self, project_id: str) -> SimpleNamespace:
        return self._snapshots_by_project[project_id]


class _FakeForecastService:
    def compute_forecast(
        self,
        project_id,
        percent_complete,
        *,
        method,
        threshold_percent,
    ) -> CostForecastResult:
        return CostForecastResult(
            project_id=project_id,
            method=method,
            bac=2300.0,
            ac=650.0,
            ev=2300.0 * max(0.0, min(1.0, percent_complete)),
            etc=1650.0,
            eac=2300.0,
            vac=0.0,
            cpi=0.0,
            exceeds_threshold=False,
            threshold_percent=threshold_percent,
        )

    def get_commitment_summary(self, project_id) -> CommitmentSummary:
        return CommitmentSummary(
            project_id=project_id,
            planned_total=2300.0,
            uncommitted_total=900.0,
            committed_total=1400.0,
            invoiced_total=0.0,
            paid_total=0.0,
            actual_total=650.0,
        )


def _build_cost_record(
    *,
    cost_id,
    project_id,
    task_id,
    description,
    planned_amount,
    committed_amount,
    actual_amount,
    cost_type,
    incurred_date,
    currency_code,
    version,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=cost_id,
        project_id=project_id,
        task_id=task_id,
        description=description,
        planned_amount=planned_amount,
        committed_amount=committed_amount,
        actual_amount=actual_amount,
        cost_type=cost_type,
        incurred_date=incurred_date,
        currency_code=currency_code,
        version=version,
    )


def test_project_management_workspace_catalog_exposes_typed_financials_controller() -> None:
    _financials_projects = [
        SimpleNamespace(id="proj-1", name="Plant Upgrade", planned_budget=5000.0, currency="EUR"),
        SimpleNamespace(id="proj-2", name="Warehouse Retrofit", planned_budget=3200.0, currency="USD"),
    ]
    financials_api = build_project_management_financials_desktop_api(
        project_service=SimpleNamespace(
            list_projects=lambda: _financials_projects,
            get_project=lambda pid: next((p for p in _financials_projects if p.id == pid), None),
        ),
        task_service=_FakeTaskOptionService(
            {
                "proj-1": [SimpleNamespace(id="task-1", name="Cable Pull", start_date=date(2026, 5, 3))],
                "proj-2": [],
            }
        ),
        cost_service=_FakeFinancialCostService(
            {
                "proj-1": [
                    _build_cost_record(
                        cost_id="cost-1",
                        project_id="proj-1",
                        task_id="task-1",
                        description="Electrical material package",
                        planned_amount=1500.0,
                        committed_amount=900.0,
                        actual_amount=450.0,
                        cost_type=CostType.MATERIAL,
                        incurred_date=date(2026, 5, 4),
                        currency_code="EUR",
                        version=2,
                    ),
                    _build_cost_record(
                        cost_id="cost-2",
                        project_id="proj-1",
                        task_id=None,
                        description="Scaffold labor support",
                        planned_amount=800.0,
                        committed_amount=500.0,
                        actual_amount=200.0,
                        cost_type=CostType.LABOR,
                        incurred_date=date(2026, 5, 5),
                        currency_code="EUR",
                        version=1,
                    ),
                ],
                "proj-2": [],
            }
        ),
        finance_service=_FakeFinanceDesktopService(
            {
                "proj-1": SimpleNamespace(
                    project_currency="EUR",
                    budget=5000.0,
                    planned=2300.0,
                    committed=1400.0,
                    actual=650.0,
                    exposure=1400.0,
                    available=3600.0,
                    ledger=[
                        SimpleNamespace(
                            source_label="Direct Cost",
                            stage="actual",
                            amount=450.0,
                            currency="EUR",
                            reference_label="Electrical material package",
                            task_name="Cable Pull",
                            resource_name=None,
                            occurred_on=date(2026, 5, 4),
                            included_in_policy=True,
                        )
                    ],
                    cashflow=[
                        SimpleNamespace(
                            period_key="2026-05",
                            planned=2300.0,
                            committed=1400.0,
                            actual=650.0,
                            forecast=2300.0,
                            exposure=1400.0,
                        )
                    ],
                    by_source=[
                        SimpleNamespace(
                            dimension="source",
                            key="direct_cost",
                            label="Direct Cost",
                            planned=2300.0,
                            committed=1400.0,
                            actual=650.0,
                            forecast=2300.0,
                            exposure=1400.0,
                        )
                    ],
                    by_cost_type=[
                        SimpleNamespace(
                            dimension="cost_type",
                            key="MATERIAL",
                            label="Material",
                            planned=1500.0,
                            committed=900.0,
                            actual=450.0,
                            forecast=1500.0,
                            exposure=900.0,
                        )
                    ],
                    by_resource=[],
                    by_task=[],
                    notes=["Finance snapshot preview generated from PM financial services."],
                ),
                "proj-2": SimpleNamespace(
                    project_currency="USD",
                    budget=3200.0,
                    planned=0.0,
                    committed=0.0,
                    actual=0.0,
                    exposure=0.0,
                    available=3200.0,
                    ledger=[],
                    cashflow=[],
                    by_source=[],
                    by_cost_type=[],
                    by_resource=[],
                    by_task=[],
                    notes=[],
                ),
            }
        ),
        forecast_service=_FakeForecastService(),
    )
    catalog = ProjectManagementWorkspaceCatalog(
        desktop_api_registry=SimpleNamespace(project_management_financials=financials_api)
    )

    controller = catalog.financialsWorkspace

    assert controller.workspace["routeId"] == "project_management.financials"
    assert controller.overview["title"] == "Financials"
    assert controller.projectOptions[0]["label"] == "Plant Upgrade"
    assert controller.projectOptions[1]["label"] == "Warehouse Retrofit"
    assert controller.costTypeOptions[1]["value"] == "LABOR"
    assert controller.costs["items"][0]["title"] == "Electrical material package"
    assert controller.selectedCost["title"] == "Electrical material package"
    assert controller.cashflow["items"][0]["title"] == "2026-05"

    controller.setCostTypeFilter("LABOR")

    assert controller.selectedCostType == "LABOR"
    assert [item["title"] for item in controller.costs["items"]] == ["Scaffold labor support"]

    controller.setSearchText("cable")

    assert controller.costs["items"] == []
    assert controller.emptyState == "No cost items match the current filters."


def test_financials_presenter_computes_forecast_via_public_desktop_api() -> None:
    class _FakeFinancialsDesktopApi:
        def __init__(self) -> None:
            self.forecast_calls: list[tuple[str | None, str]] = []

        def get_cost_forecast(self, project_id, *, method="bac_over_cpi") -> SimpleNamespace:
            self.forecast_calls.append((project_id, method))
            return SimpleNamespace(
                method=method,
                bac_label="EUR 10,000.00",
                ac_label="EUR 4,000.00",
                ev_label="EUR 5,000.00",
                etc_label="EUR 4,500.00",
                eac_label="EUR 8,500.00",
                vac_label="EUR 1,500.00",
                cpi_label="1.25",
                cpi=1.25,
                vac=1500.0,
                is_over_budget=False,
                exceeds_threshold=False,
                threshold_percent=10.0,
            )

    desktop_api = _FakeFinancialsDesktopApi()
    presenter = ProjectFinancialsWorkspacePresenter(desktop_api=desktop_api)

    forecast = presenter.compute_forecast("proj-1", method=" AC_ETC_CPI ")

    assert desktop_api.forecast_calls == [("proj-1", "ac_etc_cpi")]
    assert forecast.method == "ac_etc_cpi"
    assert forecast.method_label == "AC + ETC at CPI rate"
    assert forecast.eac_label == "EUR 8,500.00"

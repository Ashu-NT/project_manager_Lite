from __future__ import annotations

import logging
from time import perf_counter

from PySide6.QtCore import Property, QObject, Signal, Slot
from PySide6.QtQml import QmlElement, QmlUncreatable

from src.ui_qml.modules.project_management.controllers.common import (
    ProjectManagementWorkspaceControllerBase,
    serialize_portfolio_collection_view_model,
    serialize_portfolio_overview_view_model,
    serialize_portfolio_summary_view_model,
    serialize_selector_options,
    serialize_workspace_view_model,
)
from src.ui_qml.modules.project_management.presenters import (
    ProjectManagementWorkspacePresenter,
    ProjectPortfolioWorkspacePresenter,
)
from src.ui_qml.shared.models.data_table_model import DynamicTableModel

from .domain_event_binder import bind_portfolio_domain_events, portfolio_request_domain_refresh
from .heatmap_table_controller import HeatmapTableController
from .mutation_handler import PortfolioMutationHandler
from .state import default_collection, default_overview, default_summary
from .table_models import create_portfolio_table_models
from .utils import normalize_intake_status

QML_IMPORT_NAME = "ProjectManagement.Controllers"
QML_IMPORT_MAJOR_VERSION = 1

logger = logging.getLogger(__name__)


@QmlElement
@QmlUncreatable("Project management workspace controllers are provided by the shell runtime.")
class ProjectManagementPortfolioWorkspaceController(
    ProjectManagementWorkspaceControllerBase
):
    overviewChanged = Signal()
    intakeStatusOptionsChanged = Signal()
    templateOptionsChanged = Signal()
    projectOptionsChanged = Signal()
    scenarioOptionsChanged = Signal()
    dependencyTypeOptionsChanged = Signal()
    selectedIntakeStatusFilterChanged = Signal()
    selectedScenarioIdChanged = Signal()
    selectedBaseScenarioIdChanged = Signal()
    selectedCompareScenarioIdChanged = Signal()
    intakeItemsChanged = Signal()
    templatesChanged = Signal()
    scenariosChanged = Signal()
    evaluationChanged = Signal()
    comparisonChanged = Signal()
    heatmapChanged = Signal()
    dependenciesChanged = Signal()
    recentActionsChanged = Signal()
    capacityPoolChanged = Signal()
    activeTemplateSummaryChanged = Signal()
    heatmapSearchTextChanged = Signal()
    heatmapPageChanged = Signal()
    heatmapPageSizeChanged = Signal()
    heatmapTotalCountChanged = Signal()
    heatmapVisibleRowIdsChanged = Signal()

    def __init__(
        self,
        *,
        workspace_presenter: ProjectManagementWorkspacePresenter | None = None,
        portfolio_workspace_presenter: ProjectPortfolioWorkspacePresenter | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._workspace_presenter = workspace_presenter or ProjectManagementWorkspacePresenter(
            "project_management.portfolio"
        )
        self._portfolio_workspace_presenter = (
            portfolio_workspace_presenter or ProjectPortfolioWorkspacePresenter()
        )
        self._table_models = create_portfolio_table_models(self)
        self._heatmap_ctrl = HeatmapTableController()
        self._mutations = PortfolioMutationHandler(
            presenter=self._portfolio_workspace_presenter,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
            request_domain_refresh=self._request_domain_refresh,
        )
        self._overview: dict[str, object] = default_overview()
        self._intake_status_options: list[dict[str, str]] = []
        self._template_options: list[dict[str, str]] = []
        self._project_options: list[dict[str, str]] = []
        self._scenario_options: list[dict[str, str]] = []
        self._dependency_type_options: list[dict[str, str]] = []
        self._selected_intake_status_filter = "all"
        self._selected_scenario_id = ""
        self._selected_base_scenario_id = ""
        self._selected_compare_scenario_id = ""
        self._intake_items: dict[str, object] = default_collection()
        self._templates: dict[str, object] = default_collection()
        self._scenarios: dict[str, object] = default_collection()
        self._evaluation: dict[str, object] = default_summary()
        self._comparison: dict[str, object] = default_summary()
        self._heatmap: dict[str, object] = default_collection()
        self._dependencies: dict[str, object] = default_collection()
        self._recent_actions: dict[str, object] = default_collection()
        self._capacity_pool: dict[str, object] = default_collection()
        self._active_template_summary = ""
        bind_portfolio_domain_events(self)
        self.refresh()

    # ── Overview and option list properties ──────────────────────────

    @Property("QVariantMap", notify=overviewChanged)
    def overview(self) -> dict[str, object]:
        return self._overview

    @Property("QVariantList", notify=intakeStatusOptionsChanged)
    def intakeStatusOptions(self) -> list[dict[str, str]]:
        return self._intake_status_options

    @Property("QVariantList", notify=templateOptionsChanged)
    def templateOptions(self) -> list[dict[str, str]]:
        return self._template_options

    @Property("QVariantList", notify=projectOptionsChanged)
    def projectOptions(self) -> list[dict[str, str]]:
        return self._project_options

    @Property("QVariantList", notify=scenarioOptionsChanged)
    def scenarioOptions(self) -> list[dict[str, str]]:
        return self._scenario_options

    @Property("QVariantList", notify=dependencyTypeOptionsChanged)
    def dependencyTypeOptions(self) -> list[dict[str, str]]:
        return self._dependency_type_options

    # ── Selection state properties ────────────────────────────────────

    @Property(str, notify=selectedIntakeStatusFilterChanged)
    def selectedIntakeStatusFilter(self) -> str:
        return self._selected_intake_status_filter

    @Property(str, notify=selectedScenarioIdChanged)
    def selectedScenarioId(self) -> str:
        return self._selected_scenario_id

    @Property(str, notify=selectedBaseScenarioIdChanged)
    def selectedBaseScenarioId(self) -> str:
        return self._selected_base_scenario_id

    @Property(str, notify=selectedCompareScenarioIdChanged)
    def selectedCompareScenarioId(self) -> str:
        return self._selected_compare_scenario_id

    # ── Collection properties ─────────────────────────────────────────

    @Property("QVariantMap", notify=intakeItemsChanged)
    def intakeItems(self) -> dict[str, object]:
        return self._intake_items

    @Property("QVariantMap", notify=templatesChanged)
    def templates(self) -> dict[str, object]:
        return self._templates

    @Property("QVariantMap", notify=scenariosChanged)
    def scenarios(self) -> dict[str, object]:
        return self._scenarios

    @Property("QVariantMap", notify=evaluationChanged)
    def evaluation(self) -> dict[str, object]:
        return self._evaluation

    @Property("QVariantMap", notify=comparisonChanged)
    def comparison(self) -> dict[str, object]:
        return self._comparison

    @Property("QVariantMap", notify=heatmapChanged)
    def heatmap(self) -> dict[str, object]:
        return self._heatmap

    @Property("QVariantMap", notify=dependenciesChanged)
    def dependencies(self) -> dict[str, object]:
        return self._dependencies

    @Property("QVariantMap", notify=recentActionsChanged)
    def recentActions(self) -> dict[str, object]:
        return self._recent_actions

    @Property("QVariantMap", notify=capacityPoolChanged)
    def capacityPool(self) -> dict[str, object]:
        return self._capacity_pool

    @Property(str, notify=activeTemplateSummaryChanged)
    def activeTemplateSummary(self) -> str:
        return self._active_template_summary

    # ── Table model properties ────────────────────────────────────────

    @Property(QObject, constant=True)
    def heatmapTableModel(self) -> DynamicTableModel:
        return self._table_models.heatmap

    @Property(QObject, constant=True)
    def intakeItemsTableModel(self) -> DynamicTableModel:
        return self._table_models.intake_items

    @Property(QObject, constant=True)
    def portfolioDependenciesTableModel(self) -> DynamicTableModel:
        return self._table_models.dependencies

    # ── Heatmap pagination/search properties ─────────────────────────

    @Property(str, notify=heatmapSearchTextChanged)
    def heatmapSearchText(self) -> str:
        return self._heatmap_ctrl.search_text

    @Property(int, notify=heatmapPageChanged)
    def heatmapPage(self) -> int:
        return self._heatmap_ctrl.page

    @Property(int, notify=heatmapPageSizeChanged)
    def heatmapPageSize(self) -> int:
        return self._heatmap_ctrl.page_size

    @Property(int, notify=heatmapTotalCountChanged)
    def heatmapTotalCount(self) -> int:
        return self._heatmap_ctrl.total_count

    @Property("QVariantList", notify=heatmapVisibleRowIdsChanged)
    def heatmapVisibleRowIds(self) -> list[str]:
        return self._heatmap_ctrl.visible_row_ids

    # ── Slots ─────────────────────────────────────────────────────────

    @Slot()
    def refresh(self) -> None:
        started = perf_counter()
        logger.info(
            "PM portfolio refresh begin intake_filter=%s scenario=%s compare_base=%s compare=%s heatmap_page=%s heatmap_page_size=%s heatmap_search=%s",
            self._selected_intake_status_filter,
            self._selected_scenario_id,
            self._selected_base_scenario_id,
            self._selected_compare_scenario_id,
            self._heatmap_ctrl.page,
            self._heatmap_ctrl.page_size,
            self._heatmap_ctrl.search_text,
        )
        self._set_is_loading(True)
        success = False
        try:
            self._set_error_message("")
            self._set_feedback_message("")
            self._set_workspace(
                serialize_workspace_view_model(self._workspace_presenter.build_view_model())
            )
            ws = self._portfolio_workspace_presenter.build_workspace_state(
                intake_status_filter=self._selected_intake_status_filter,
                selected_scenario_id=self._selected_scenario_id or None,
                base_compare_scenario_id=self._selected_base_scenario_id or None,
                compare_scenario_id=self._selected_compare_scenario_id or None,
            )
            self._set_overview(serialize_portfolio_overview_view_model(ws.overview))
            self._set_intake_status_options(
                serialize_selector_options(ws.intake_status_options)
            )
            self._set_template_options(serialize_selector_options(ws.template_options))
            self._set_project_options(serialize_selector_options(ws.project_options))
            self._set_scenario_options(serialize_selector_options(ws.scenario_options))
            self._set_dependency_type_options(
                serialize_selector_options(ws.dependency_type_options)
            )
            self._set_selected_intake_status_filter(ws.selected_intake_status_filter)
            self._set_selected_scenario_id(ws.selected_scenario_id)
            self._set_selected_base_scenario_id(ws.selected_base_scenario_id)
            self._set_selected_compare_scenario_id(ws.selected_compare_scenario_id)
            self._set_intake_items(
                serialize_portfolio_collection_view_model(ws.intake_items)
            )
            self._set_templates(serialize_portfolio_collection_view_model(ws.templates))
            self._set_scenarios(serialize_portfolio_collection_view_model(ws.scenarios))
            self._set_evaluation(serialize_portfolio_summary_view_model(ws.evaluation))
            self._set_comparison(serialize_portfolio_summary_view_model(ws.comparison))
            self._set_heatmap(serialize_portfolio_collection_view_model(ws.heatmap))
            self._set_dependencies(
                serialize_portfolio_collection_view_model(ws.dependencies)
            )
            self._set_recent_actions(
                serialize_portfolio_collection_view_model(ws.recent_actions)
            )
            self._set_capacity_pool(
                serialize_portfolio_collection_view_model(ws.capacity_pool)
            )
            self._set_active_template_summary(ws.active_template_summary)
            self._set_empty_state(ws.empty_state)
            success = True
        except Exception as exc:  # pragma: no cover - defensive fallback
            logger.exception("PM portfolio refresh failed")
            self._set_error_message(str(exc))
        finally:
            duration_ms = (perf_counter() - started) * 1000
            log_method = logger.warning if duration_ms > 500 else logger.info
            log_method(
                "PM portfolio refresh complete success=%s duration_ms=%.1f intake_count=%s heatmap_total=%s scenario=%s",
                success,
                duration_ms,
                len(self._intake_items.get("items", []) or []),
                self._heatmap_ctrl.total_count,
                self._selected_scenario_id,
            )
            self._set_is_loading(False)

    @Slot(str)
    def setIntakeStatusFilter(self, intake_status_filter: str) -> None:
        normalized = normalize_intake_status(intake_status_filter)
        if normalized.lower() == self._selected_intake_status_filter.lower():
            return
        self._set_selected_intake_status_filter(normalized)
        self.refresh()

    @Slot(str)
    def selectScenario(self, scenario_id: str) -> None:
        normalized = (scenario_id or "").strip()
        if normalized == self._selected_scenario_id:
            return
        self._set_selected_scenario_id(normalized)
        self.refresh()

    @Slot(str)
    def selectCompareBase(self, scenario_id: str) -> None:
        normalized = (scenario_id or "").strip()
        if normalized == self._selected_base_scenario_id:
            return
        self._set_selected_base_scenario_id(normalized)
        self.refresh()

    @Slot(str)
    def selectCompareScenario(self, scenario_id: str) -> None:
        normalized = (scenario_id or "").strip()
        if normalized == self._selected_compare_scenario_id:
            return
        self._set_selected_compare_scenario_id(normalized)
        self.refresh()

    @Slot(str)
    def setHeatmapSearchText(self, search_text: str) -> None:
        normalized = (search_text or "").strip()
        if normalized == self._heatmap_ctrl.search_text:
            return
        self._heatmap_ctrl.search_text = normalized
        self._heatmap_ctrl.page = 1
        self.heatmapSearchTextChanged.emit()
        self.heatmapPageChanged.emit()
        self._rebuild_heatmap_table_model()

    @Slot(int)
    def setHeatmapPage(self, page: int) -> None:
        normalized = max(1, int(page or 1))
        if normalized == self._heatmap_ctrl.page:
            return
        self._heatmap_ctrl.page = normalized
        self.heatmapPageChanged.emit()
        self._rebuild_heatmap_table_model()

    @Slot(int)
    def setHeatmapPageSize(self, page_size: int) -> None:
        normalized = max(1, int(page_size or 25))
        if normalized == self._heatmap_ctrl.page_size:
            return
        self._heatmap_ctrl.page_size = normalized
        self._heatmap_ctrl.page = 1
        self.heatmapPageSizeChanged.emit()
        self.heatmapPageChanged.emit()
        self._rebuild_heatmap_table_model()

    @Slot()
    def exportPortfolio(self) -> None:
        self._set_error_message("")
        self._set_feedback_message(
            "Export is not available here. Open the Reports section to generate portfolio summaries and scenario exports."
        )

    @Slot("QVariantMap", result="QVariantMap")
    def createTemplate(self, payload: dict[str, object]) -> dict[str, object]:
        return self._mutations.create_template(payload)

    @Slot(str, result="QVariantMap")
    def activateTemplate(self, template_id: str) -> dict[str, object]:
        return self._mutations.activate_template(template_id)

    @Slot("QVariantMap", result="QVariantMap")
    def createIntakeItem(self, payload: dict[str, object]) -> dict[str, object]:
        return self._mutations.create_intake_item(payload)

    @Slot("QVariantMap", result="QVariantMap")
    def createScenario(self, payload: dict[str, object]) -> dict[str, object]:
        return self._mutations.create_scenario(payload)

    @Slot("QVariantMap", result="QVariantMap")
    def createDependency(self, payload: dict[str, object]) -> dict[str, object]:
        return self._mutations.create_dependency(payload)

    @Slot(str, result="QVariantMap")
    def removeDependency(self, dependency_id: str) -> dict[str, object]:
        return self._mutations.remove_dependency(dependency_id)

    @Slot(str, str, result="QVariantMap")
    def updateIntakeItemStatus(self, item_id: str, status: str) -> dict[str, object]:
        return self._mutations.update_intake_item_status(item_id, status)

    # ── Domain event overrides ────────────────────────────────────────

    def _request_domain_refresh(self) -> None:
        portfolio_request_domain_refresh(self, super()._request_domain_refresh)

    # ── Internal state management ─────────────────────────────────────

    def _rebuild_heatmap_table_model(self) -> None:
        self._heatmap_ctrl.rebuild(
            heatmap_items=self._heatmap.get("items", []) or [],
            table_model=self._table_models.heatmap,
            emit_page_changed=self.heatmapPageChanged.emit,
            emit_total_count_changed=self.heatmapTotalCountChanged.emit,
            emit_visible_ids_changed=self.heatmapVisibleRowIdsChanged.emit,
        )

    def _set_overview(self, overview: dict[str, object]) -> None:
        if overview == self._overview:
            return
        self._overview = overview
        self.overviewChanged.emit()

    def _set_intake_status_options(self, intake_status_options: list[dict[str, str]]) -> None:
        if intake_status_options == self._intake_status_options:
            return
        self._intake_status_options = intake_status_options
        self.intakeStatusOptionsChanged.emit()

    def _set_template_options(self, template_options: list[dict[str, str]]) -> None:
        if template_options == self._template_options:
            return
        self._template_options = template_options
        self.templateOptionsChanged.emit()

    def _set_project_options(self, project_options: list[dict[str, str]]) -> None:
        if project_options == self._project_options:
            return
        self._project_options = project_options
        self.projectOptionsChanged.emit()

    def _set_scenario_options(self, scenario_options: list[dict[str, str]]) -> None:
        if scenario_options == self._scenario_options:
            return
        self._scenario_options = scenario_options
        self.scenarioOptionsChanged.emit()

    def _set_dependency_type_options(
        self, dependency_type_options: list[dict[str, str]]
    ) -> None:
        if dependency_type_options == self._dependency_type_options:
            return
        self._dependency_type_options = dependency_type_options
        self.dependencyTypeOptionsChanged.emit()

    def _set_selected_intake_status_filter(self, value: str) -> None:
        if value == self._selected_intake_status_filter:
            return
        self._selected_intake_status_filter = value
        self.selectedIntakeStatusFilterChanged.emit()

    def _set_selected_scenario_id(self, value: str) -> None:
        if value == self._selected_scenario_id:
            return
        self._selected_scenario_id = value
        self.selectedScenarioIdChanged.emit()

    def _set_selected_base_scenario_id(self, value: str) -> None:
        if value == self._selected_base_scenario_id:
            return
        self._selected_base_scenario_id = value
        self.selectedBaseScenarioIdChanged.emit()

    def _set_selected_compare_scenario_id(self, value: str) -> None:
        if value == self._selected_compare_scenario_id:
            return
        self._selected_compare_scenario_id = value
        self.selectedCompareScenarioIdChanged.emit()

    def _set_intake_items(self, intake_items: dict[str, object]) -> None:
        if intake_items == self._intake_items:
            return
        self._intake_items = intake_items
        self._table_models.intake_items.set_rows(intake_items.get("items", []))
        self.intakeItemsChanged.emit()

    def _set_templates(self, templates: dict[str, object]) -> None:
        if templates == self._templates:
            return
        self._templates = templates
        self.templatesChanged.emit()

    def _set_scenarios(self, scenarios: dict[str, object]) -> None:
        if scenarios == self._scenarios:
            return
        self._scenarios = scenarios
        self.scenariosChanged.emit()

    def _set_evaluation(self, evaluation: dict[str, object]) -> None:
        if evaluation == self._evaluation:
            return
        self._evaluation = evaluation
        self.evaluationChanged.emit()

    def _set_comparison(self, comparison: dict[str, object]) -> None:
        if comparison == self._comparison:
            return
        self._comparison = comparison
        self.comparisonChanged.emit()

    def _set_heatmap(self, heatmap: dict[str, object]) -> None:
        if heatmap == self._heatmap:
            return
        self._heatmap = heatmap
        self._rebuild_heatmap_table_model()
        self.heatmapChanged.emit()

    def _set_dependencies(self, dependencies: dict[str, object]) -> None:
        if dependencies == self._dependencies:
            return
        self._dependencies = dependencies
        self._table_models.dependencies.set_rows(dependencies.get("items", []))
        self.dependenciesChanged.emit()

    def _set_recent_actions(self, recent_actions: dict[str, object]) -> None:
        if recent_actions == self._recent_actions:
            return
        self._recent_actions = recent_actions
        self.recentActionsChanged.emit()

    def _set_capacity_pool(self, capacity_pool: dict[str, object]) -> None:
        if capacity_pool == self._capacity_pool:
            return
        self._capacity_pool = capacity_pool
        self.capacityPoolChanged.emit()

    def _set_active_template_summary(self, active_template_summary: str) -> None:
        if active_template_summary == self._active_template_summary:
            return
        self._active_template_summary = active_template_summary
        self.activeTemplateSummaryChanged.emit()


__all__ = ["ProjectManagementPortfolioWorkspaceController"]

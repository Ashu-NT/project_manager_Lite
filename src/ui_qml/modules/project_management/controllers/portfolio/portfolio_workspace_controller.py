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

from .collection_page_state import PortfolioCollectionPageState
from .domain_event_binder import bind_portfolio_domain_events, portfolio_request_domain_refresh
from .mutation_handler import PortfolioMutationHandler
from .state import default_collection, default_overview, default_summary
from .table_models import create_portfolio_table_models
from .filter_normalization import normalize_intake_status

QML_IMPORT_NAME = "ProjectManagement.Controllers"
QML_IMPORT_MAJOR_VERSION = 1

logger = logging.getLogger(__name__)

_ACTIVE_TABS = ("executive", "heatmap", "intake", "scenarios", "capacity", "dependencies")


@QmlElement
@QmlUncreatable("Project management workspace controllers are provided by the shell runtime.")
class ProjectManagementPortfolioWorkspaceController(
    ProjectManagementWorkspaceControllerBase
):
    overviewChanged = Signal()
    activeTabChanged = Signal()
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
    topAtRiskProjectsChanged = Signal()
    hotProjectCountChanged = Signal()
    dependencyCountChanged = Signal()
    activeTemplateSummaryChanged = Signal()
    heatmapSearchTextChanged = Signal()
    heatmapPageChanged = Signal()
    heatmapPageSizeChanged = Signal()
    intakeSearchTextChanged = Signal()
    intakePageChanged = Signal()
    intakePageSizeChanged = Signal()
    dependencySearchTextChanged = Signal()
    dependencyPageChanged = Signal()
    dependencyPageSizeChanged = Signal()

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
        self._heatmap_page = PortfolioCollectionPageState(sort_key="projectName", sort_direction="asc")
        self._intake_page = PortfolioCollectionPageState(sort_key="updatedAt", sort_direction="desc")
        self._dependency_page = PortfolioCollectionPageState(sort_key="updatedAt", sort_direction="desc")
        self._mutations = PortfolioMutationHandler(
            presenter=self._portfolio_workspace_presenter,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
            request_domain_refresh=self._request_domain_refresh,
        )
        self._active_tab = "executive"
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
        self._top_at_risk_projects: dict[str, object] = default_collection()
        self._hot_project_count = 0
        self._dependency_count = 0
        self._active_template_summary = ""
        bind_portfolio_domain_events(self)
        self.refresh()

    # ── Overview and option list properties ──────────────────────────

    @Property("QVariantMap", notify=overviewChanged)
    def overview(self) -> dict[str, object]:
        return self._overview

    @Property(str, notify=activeTabChanged)
    def activeTab(self) -> str:
        return self._active_tab

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

    @Property("QVariantMap", notify=topAtRiskProjectsChanged)
    def topAtRiskProjects(self) -> dict[str, object]:
        return self._top_at_risk_projects

    @Property(int, notify=hotProjectCountChanged)
    def hotProjectCount(self) -> int:
        return self._hot_project_count

    @Property(int, notify=dependencyCountChanged)
    def dependencyCount(self) -> int:
        return self._dependency_count

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

    # ── Heatmap pagination/search properties (server-authoritative) ──

    @Property(str, notify=heatmapSearchTextChanged)
    def heatmapSearchText(self) -> str:
        return self._heatmap_page.search_text

    @Property(int, notify=heatmapPageChanged)
    def heatmapPage(self) -> int:
        return self._heatmap_page.page

    @Property(int, notify=heatmapPageSizeChanged)
    def heatmapPageSize(self) -> int:
        return self._heatmap_page.page_size

    @Property(int, notify=heatmapChanged)
    def heatmapTotalCount(self) -> int:
        return self._heatmap_page.total_count

    # ── Intake pagination/search properties (server-authoritative) ───

    @Property(str, notify=intakeSearchTextChanged)
    def intakeSearchText(self) -> str:
        return self._intake_page.search_text

    @Property(int, notify=intakePageChanged)
    def intakePage(self) -> int:
        return self._intake_page.page

    @Property(int, notify=intakePageSizeChanged)
    def intakePageSize(self) -> int:
        return self._intake_page.page_size

    @Property(int, notify=intakeItemsChanged)
    def intakeTotalCount(self) -> int:
        return self._intake_page.total_count

    # ── Dependency pagination/search properties (server-authoritative)

    @Property(str, notify=dependencySearchTextChanged)
    def dependencySearchText(self) -> str:
        return self._dependency_page.search_text

    @Property(int, notify=dependencyPageChanged)
    def dependencyPage(self) -> int:
        return self._dependency_page.page

    @Property(int, notify=dependencyPageSizeChanged)
    def dependencyPageSize(self) -> int:
        return self._dependency_page.page_size

    @Property(int, notify=dependenciesChanged)
    def dependencyTotalCount(self) -> int:
        return self._dependency_page.total_count

    # ── Slots ─────────────────────────────────────────────────────────

    @Slot()
    def refresh(self) -> None:
        started = perf_counter()
        logger.info(
            "PM portfolio refresh begin tab=%s intake_filter=%s scenario=%s compare_base=%s compare=%s "
            "heatmap_page=%s/%s search=%r intake_page=%s/%s search=%r dependency_page=%s/%s search=%r",
            self._active_tab,
            self._selected_intake_status_filter,
            self._selected_scenario_id,
            self._selected_base_scenario_id,
            self._selected_compare_scenario_id,
            self._heatmap_page.page, self._heatmap_page.page_size, self._heatmap_page.search_text,
            self._intake_page.page, self._intake_page.page_size, self._intake_page.search_text,
            self._dependency_page.page, self._dependency_page.page_size, self._dependency_page.search_text,
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
                active_tab=self._active_tab,
                intake_status_filter=self._selected_intake_status_filter,
                intake_search_text=self._intake_page.search_text,
                intake_page=self._intake_page.page,
                intake_page_size=self._intake_page.page_size,
                intake_sort_key=self._intake_page.sort_key,
                intake_sort_direction=self._intake_page.sort_direction,
                heatmap_search_text=self._heatmap_page.search_text,
                heatmap_page=self._heatmap_page.page,
                heatmap_page_size=self._heatmap_page.page_size,
                heatmap_sort_key=self._heatmap_page.sort_key,
                heatmap_sort_direction=self._heatmap_page.sort_direction,
                dependencies_search_text=self._dependency_page.search_text,
                dependencies_page=self._dependency_page.page,
                dependencies_page_size=self._dependency_page.page_size,
                dependencies_sort_key=self._dependency_page.sort_key,
                dependencies_sort_direction=self._dependency_page.sort_direction,
                selected_scenario_id=self._selected_scenario_id,
                base_compare_scenario_id=self._selected_base_scenario_id,
                compare_scenario_id=self._selected_compare_scenario_id,
            )
            self._set_active_tab(ws.active_tab)
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
            self._intake_page.page = ws.intake_items.page
            self._intake_page.total_count = ws.intake_items.total
            self._set_templates(serialize_portfolio_collection_view_model(ws.templates))
            self._set_scenarios(serialize_portfolio_collection_view_model(ws.scenarios))
            self._set_evaluation(serialize_portfolio_summary_view_model(ws.evaluation))
            self._set_comparison(serialize_portfolio_summary_view_model(ws.comparison))
            self._set_heatmap(serialize_portfolio_collection_view_model(ws.heatmap))
            self._heatmap_page.page = ws.heatmap.page
            self._heatmap_page.total_count = ws.heatmap.total
            self._set_dependencies(
                serialize_portfolio_collection_view_model(ws.dependencies)
            )
            self._dependency_page.page = ws.dependencies.page
            self._dependency_page.total_count = ws.dependencies.total
            self._set_recent_actions(
                serialize_portfolio_collection_view_model(ws.recent_actions)
            )
            self._set_capacity_pool(
                serialize_portfolio_collection_view_model(ws.capacity_pool)
            )
            self._set_top_at_risk_projects(
                serialize_portfolio_collection_view_model(ws.top_at_risk_projects)
            )
            self._set_hot_project_count(ws.hot_project_count)
            self._set_dependency_count(ws.dependency_count)
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
                "PM portfolio refresh complete success=%s duration_ms=%.1f intake_total=%s heatmap_total=%s "
                "dependency_total=%s scenario=%s",
                success,
                duration_ms,
                self._intake_page.total_count,
                self._heatmap_page.total_count,
                self._dependency_page.total_count,
                self._selected_scenario_id,
            )
            self._set_is_loading(False)

    @Slot(str)
    def setActiveTab(self, tab: str) -> None:
        normalized = str(tab or "executive").strip().lower()
        if normalized not in _ACTIVE_TABS or normalized == self._active_tab:
            return
        self._set_active_tab(normalized)
        self.refresh()

    @Slot(str)
    def setIntakeStatusFilter(self, intake_status_filter: str) -> None:
        normalized = normalize_intake_status(intake_status_filter)
        if normalized.lower() == self._selected_intake_status_filter.lower():
            return
        self._set_selected_intake_status_filter(normalized)
        self._intake_page.page = 1
        self.intakePageChanged.emit()
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
        if normalized == self._heatmap_page.search_text:
            return
        self._heatmap_page.search_text = normalized
        self._heatmap_page.page = 1
        self.heatmapSearchTextChanged.emit()
        self.heatmapPageChanged.emit()
        self.refresh()

    @Slot(int)
    def setHeatmapPage(self, page: int) -> None:
        normalized = max(1, int(page or 1))
        if normalized == self._heatmap_page.page:
            return
        self._heatmap_page.page = normalized
        self.heatmapPageChanged.emit()
        self.refresh()

    @Slot(int)
    def setHeatmapPageSize(self, page_size: int) -> None:
        normalized = max(1, int(page_size or 25))
        if normalized == self._heatmap_page.page_size:
            return
        self._heatmap_page.page_size = normalized
        self._heatmap_page.page = 1
        self.heatmapPageSizeChanged.emit()
        self.heatmapPageChanged.emit()
        self.refresh()

    @Slot(str)
    def setIntakeSearchText(self, search_text: str) -> None:
        normalized = (search_text or "").strip()
        if normalized == self._intake_page.search_text:
            return
        self._intake_page.search_text = normalized
        self._intake_page.page = 1
        self.intakeSearchTextChanged.emit()
        self.intakePageChanged.emit()
        self.refresh()

    @Slot(int)
    def setIntakePage(self, page: int) -> None:
        normalized = max(1, int(page or 1))
        if normalized == self._intake_page.page:
            return
        self._intake_page.page = normalized
        self.intakePageChanged.emit()
        self.refresh()

    @Slot(int)
    def setIntakePageSize(self, page_size: int) -> None:
        normalized = max(1, int(page_size or 25))
        if normalized == self._intake_page.page_size:
            return
        self._intake_page.page_size = normalized
        self._intake_page.page = 1
        self.intakePageSizeChanged.emit()
        self.intakePageChanged.emit()
        self.refresh()

    @Slot(str)
    def setDependencySearchText(self, search_text: str) -> None:
        normalized = (search_text or "").strip()
        if normalized == self._dependency_page.search_text:
            return
        self._dependency_page.search_text = normalized
        self._dependency_page.page = 1
        self.dependencySearchTextChanged.emit()
        self.dependencyPageChanged.emit()
        self.refresh()

    @Slot(int)
    def setDependencyPage(self, page: int) -> None:
        normalized = max(1, int(page or 1))
        if normalized == self._dependency_page.page:
            return
        self._dependency_page.page = normalized
        self.dependencyPageChanged.emit()
        self.refresh()

    @Slot(int)
    def setDependencyPageSize(self, page_size: int) -> None:
        normalized = max(1, int(page_size or 25))
        if normalized == self._dependency_page.page_size:
            return
        self._dependency_page.page_size = normalized
        self._dependency_page.page = 1
        self.dependencyPageSizeChanged.emit()
        self.dependencyPageChanged.emit()
        self.refresh()

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

    def _set_active_tab(self, tab: str) -> None:
        if tab == self._active_tab:
            return
        self._active_tab = tab
        self.activeTabChanged.emit()

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
        self._table_models.heatmap.set_rows(heatmap.get("items", []))
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

    def _set_top_at_risk_projects(self, top_at_risk_projects: dict[str, object]) -> None:
        if top_at_risk_projects == self._top_at_risk_projects:
            return
        self._top_at_risk_projects = top_at_risk_projects
        self.topAtRiskProjectsChanged.emit()

    def _set_hot_project_count(self, value: int) -> None:
        if value == self._hot_project_count:
            return
        self._hot_project_count = value
        self.hotProjectCountChanged.emit()

    def _set_dependency_count(self, value: int) -> None:
        if value == self._dependency_count:
            return
        self._dependency_count = value
        self.dependencyCountChanged.emit()

    def _set_active_template_summary(self, active_template_summary: str) -> None:
        if active_template_summary == self._active_template_summary:
            return
        self._active_template_summary = active_template_summary
        self.activeTemplateSummaryChanged.emit()


__all__ = ["ProjectManagementPortfolioWorkspaceController"]

from __future__ import annotations

from PySide6.QtCore import Property, QObject, Signal, Slot

from src.ui_qml.modules.project_management.controllers.common import (
    ProjectManagementWorkspaceControllerBase,
    run_mutation,
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
    activeTemplateSummaryChanged = Signal()

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
        self._overview: dict[str, object] = {"title": "", "subtitle": "", "metrics": []}
        self._intake_status_options: list[dict[str, str]] = []
        self._template_options: list[dict[str, str]] = []
        self._project_options: list[dict[str, str]] = []
        self._scenario_options: list[dict[str, str]] = []
        self._dependency_type_options: list[dict[str, str]] = []
        self._selected_intake_status_filter = "all"
        self._selected_scenario_id = ""
        self._selected_base_scenario_id = ""
        self._selected_compare_scenario_id = ""
        self._intake_items: dict[str, object] = {"title": "", "subtitle": "", "emptyState": "", "items": []}
        self._templates: dict[str, object] = {"title": "", "subtitle": "", "emptyState": "", "items": []}
        self._scenarios: dict[str, object] = {"title": "", "subtitle": "", "emptyState": "", "items": []}
        self._evaluation: dict[str, object] = {"title": "", "subtitle": "", "emptyState": "", "fields": []}
        self._comparison: dict[str, object] = {"title": "", "subtitle": "", "emptyState": "", "fields": []}
        self._heatmap: dict[str, object] = {"title": "", "subtitle": "", "emptyState": "", "items": []}
        self._dependencies: dict[str, object] = {"title": "", "subtitle": "", "emptyState": "", "items": []}
        self._recent_actions: dict[str, object] = {"title": "", "subtitle": "", "emptyState": "", "items": []}
        self._active_template_summary = ""
        self._bind_domain_events()
        self.refresh()

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

    @Property(str, notify=activeTemplateSummaryChanged)
    def activeTemplateSummary(self) -> str:
        return self._active_template_summary

    @Slot()
    def refresh(self) -> None:
        self._set_is_loading(True)
        try:
            self._set_error_message("")
            self._set_feedback_message("")
            self._set_workspace(
                serialize_workspace_view_model(self._workspace_presenter.build_view_model())
            )
            workspace_state = self._portfolio_workspace_presenter.build_workspace_state(
                intake_status_filter=self._selected_intake_status_filter,
                selected_scenario_id=self._selected_scenario_id or None,
                base_compare_scenario_id=self._selected_base_scenario_id or None,
                compare_scenario_id=self._selected_compare_scenario_id or None,
            )
            self._set_overview(
                serialize_portfolio_overview_view_model(workspace_state.overview)
            )
            self._set_intake_status_options(
                serialize_selector_options(workspace_state.intake_status_options)
            )
            self._set_template_options(
                serialize_selector_options(workspace_state.template_options)
            )
            self._set_project_options(
                serialize_selector_options(workspace_state.project_options)
            )
            self._set_scenario_options(
                serialize_selector_options(workspace_state.scenario_options)
            )
            self._set_dependency_type_options(
                serialize_selector_options(workspace_state.dependency_type_options)
            )
            self._set_selected_intake_status_filter(
                workspace_state.selected_intake_status_filter
            )
            self._set_selected_scenario_id(workspace_state.selected_scenario_id)
            self._set_selected_base_scenario_id(
                workspace_state.selected_base_scenario_id
            )
            self._set_selected_compare_scenario_id(
                workspace_state.selected_compare_scenario_id
            )
            self._set_intake_items(
                serialize_portfolio_collection_view_model(workspace_state.intake_items)
            )
            self._set_templates(
                serialize_portfolio_collection_view_model(workspace_state.templates)
            )
            self._set_scenarios(
                serialize_portfolio_collection_view_model(workspace_state.scenarios)
            )
            self._set_evaluation(
                serialize_portfolio_summary_view_model(workspace_state.evaluation)
            )
            self._set_comparison(
                serialize_portfolio_summary_view_model(workspace_state.comparison)
            )
            self._set_heatmap(
                serialize_portfolio_collection_view_model(workspace_state.heatmap)
            )
            self._set_dependencies(
                serialize_portfolio_collection_view_model(workspace_state.dependencies)
            )
            self._set_recent_actions(
                serialize_portfolio_collection_view_model(workspace_state.recent_actions)
            )
            self._set_active_template_summary(workspace_state.active_template_summary)
            self._set_empty_state(workspace_state.empty_state)
        except Exception as exc:  # pragma: no cover - defensive fallback
            self._set_error_message(str(exc))
        finally:
            self._set_is_loading(False)

    @Slot(str)
    def setIntakeStatusFilter(self, intake_status_filter: str) -> None:
        normalized_value = (intake_status_filter or "").strip().upper() or "ALL"
        if normalized_value.lower() == self._selected_intake_status_filter.lower():
            return
        self._set_selected_intake_status_filter(normalized_value.lower() if normalized_value == "ALL" else normalized_value)
        self.refresh()

    @Slot(str)
    def selectScenario(self, scenario_id: str) -> None:
        normalized_value = (scenario_id or "").strip()
        if normalized_value == self._selected_scenario_id:
            return
        self._set_selected_scenario_id(normalized_value)
        self.refresh()

    @Slot(str)
    def selectCompareBase(self, scenario_id: str) -> None:
        normalized_value = (scenario_id or "").strip()
        if normalized_value == self._selected_base_scenario_id:
            return
        self._set_selected_base_scenario_id(normalized_value)
        self.refresh()

    @Slot(str)
    def selectCompareScenario(self, scenario_id: str) -> None:
        normalized_value = (scenario_id or "").strip()
        if normalized_value == self._selected_compare_scenario_id:
            return
        self._set_selected_compare_scenario_id(normalized_value)
        self.refresh()

    @Slot("QVariantMap", result="QVariantMap")
    def createTemplate(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._portfolio_workspace_presenter.create_template(dict(payload)),
            success_message="Scoring template created.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot(str, result="QVariantMap")
    def activateTemplate(self, template_id: str) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._portfolio_workspace_presenter.activate_template(template_id),
            success_message="Scoring template activated.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def createIntakeItem(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._portfolio_workspace_presenter.create_intake_item(dict(payload)),
            success_message="Intake item created.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def createScenario(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._portfolio_workspace_presenter.create_scenario(dict(payload)),
            success_message="Scenario saved.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def createDependency(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._portfolio_workspace_presenter.create_dependency(dict(payload)),
            success_message="Dependency created.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot(str, result="QVariantMap")
    def removeDependency(self, dependency_id: str) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._portfolio_workspace_presenter.remove_dependency(dependency_id),
            success_message="Dependency removed.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    def _bind_domain_events(self) -> None:
        self._subscribe_domain_change(
            "portfolio_entity",
            "project",
            "project_tasks",
            "project_costs",
            "resource",
            scope_code="project_management",
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

    def _set_dependency_type_options(self, dependency_type_options: list[dict[str, str]]) -> None:
        if dependency_type_options == self._dependency_type_options:
            return
        self._dependency_type_options = dependency_type_options
        self.dependencyTypeOptionsChanged.emit()

    def _set_selected_intake_status_filter(self, selected_intake_status_filter: str) -> None:
        if selected_intake_status_filter == self._selected_intake_status_filter:
            return
        self._selected_intake_status_filter = selected_intake_status_filter
        self.selectedIntakeStatusFilterChanged.emit()

    def _set_selected_scenario_id(self, selected_scenario_id: str) -> None:
        if selected_scenario_id == self._selected_scenario_id:
            return
        self._selected_scenario_id = selected_scenario_id
        self.selectedScenarioIdChanged.emit()

    def _set_selected_base_scenario_id(self, selected_base_scenario_id: str) -> None:
        if selected_base_scenario_id == self._selected_base_scenario_id:
            return
        self._selected_base_scenario_id = selected_base_scenario_id
        self.selectedBaseScenarioIdChanged.emit()

    def _set_selected_compare_scenario_id(self, selected_compare_scenario_id: str) -> None:
        if selected_compare_scenario_id == self._selected_compare_scenario_id:
            return
        self._selected_compare_scenario_id = selected_compare_scenario_id
        self.selectedCompareScenarioIdChanged.emit()

    def _set_intake_items(self, intake_items: dict[str, object]) -> None:
        if intake_items == self._intake_items:
            return
        self._intake_items = intake_items
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
        self.heatmapChanged.emit()

    def _set_dependencies(self, dependencies: dict[str, object]) -> None:
        if dependencies == self._dependencies:
            return
        self._dependencies = dependencies
        self.dependenciesChanged.emit()

    def _set_recent_actions(self, recent_actions: dict[str, object]) -> None:
        if recent_actions == self._recent_actions:
            return
        self._recent_actions = recent_actions
        self.recentActionsChanged.emit()

    def _set_active_template_summary(self, active_template_summary: str) -> None:
        if active_template_summary == self._active_template_summary:
            return
        self._active_template_summary = active_template_summary
        self.activeTemplateSummaryChanged.emit()


__all__ = ["ProjectManagementPortfolioWorkspaceController"]

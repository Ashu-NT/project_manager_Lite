import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Layouts 1.0 as AppLayouts
import App.Theme 1.0 as Theme
import App.Widgets 1.0 as AppWidgets
import ProjectManagement.Controllers 1.0 as ProjectManagementControllers

AppLayouts.WorkspaceFrame {
    id: root

    property var shellModel: null
    property ProjectManagementControllers.ProjectManagementWorkspaceCatalog pmCatalog
    property ProjectManagementControllers.ProjectManagementDashboardWorkspaceController workspaceController: root.pmCatalog
        ? root.pmCatalog.dashboardWorkspace
        : null
    readonly property var workspaceModel: root.workspaceController
        ? root.workspaceController.workspace
        : ({
            "routeId": "project_management.dashboard",
            "title": "Dashboard",
            "summary": "Project KPIs, health summaries, and executive delivery views.",
            "migrationStatus": "QML read-only dashboard slice active",
            "legacyRuntimeStatus": "Existing QWidget dashboard remains active"
        })
    readonly property var overviewModel: root.workspaceController
        ? root.workspaceController.overview
        : ({
            "title": root.workspaceModel.title,
            "subtitle": "Select a project to see schedule and cost health.",
            "metrics": []
        })

    title: root.overviewModel.title || root.workspaceModel.title
    subtitle: root.overviewModel.subtitle || root.workspaceModel.summary

    ColumnLayout {
        anchors.fill: parent
        spacing: Theme.AppTheme.spacingSm

        DashboardSelectionBar {
            Layout.fillWidth: true
            projectOptions: root.workspaceController ? (root.workspaceController.projectOptions || []) : []
            selectedProjectId: root.workspaceController ? root.workspaceController.selectedProjectId : ""
            baselineOptions: root.workspaceController ? (root.workspaceController.baselineOptions || []) : []
            selectedBaselineId: root.workspaceController ? root.workspaceController.selectedBaselineId : ""
            periodOptions: root.workspaceController ? (root.workspaceController.periodOptions || []) : []
            selectedPeriodKey: root.workspaceController ? root.workspaceController.selectedPeriodKey : ""
            viewOptions: root.workspaceController ? (root.workspaceController.viewOptions || []) : []
            selectedViewKey: root.workspaceController ? root.workspaceController.selectedViewKey : ""
            isLoading: root.workspaceController ? root.workspaceController.isLoading : false

            onProjectSelected: function(projectId) {
                if (root.workspaceController !== null) {
                    root.workspaceController.selectProject(projectId)
                }
            }

            onBaselineSelected: function(baselineId) {
                if (root.workspaceController !== null) {
                    root.workspaceController.selectBaseline(baselineId)
                }
            }

            onPeriodSelected: function(periodKey) {
                if (root.workspaceController !== null) {
                    root.workspaceController.selectPeriod(periodKey)
                }
            }

            onViewSelected: function(viewKey) {
                if (root.workspaceController !== null) {
                    root.workspaceController.selectView(viewKey)
                }
            }

            onRefreshRequested: function() {
                if (root.workspaceController !== null) {
                    root.workspaceController.refresh()
                }
            }

            onExportRequested: function() {
                if (root.workspaceController !== null) {
                    root.workspaceController.exportDashboard()
                }
            }
        }

        AppWidgets.InlineMessage {
            Layout.fillWidth: true
            visible: root.workspaceController !== null
                && root.workspaceController.errorMessage.length === 0
                && (root.workspaceController.isLoading || root.workspaceController.isBusy)
            tone: "info"
            message: root.workspaceController && root.workspaceController.isBusy
                ? "Refreshing dashboard state..."
                : "Loading dashboard data..."
        }

        AppWidgets.InlineMessage {
            Layout.fillWidth: true
            visible: root.workspaceController !== null
                && root.workspaceController.errorMessage.length > 0
            tone: "danger"
            message: root.workspaceController ? root.workspaceController.errorMessage : ""
        }

        AppWidgets.InlineMessage {
            Layout.fillWidth: true
            visible: root.workspaceController !== null
                && root.workspaceController.errorMessage.length === 0
                && root.workspaceController.feedbackMessage.length > 0
            tone: "success"
            message: root.workspaceController ? root.workspaceController.feedbackMessage : ""
        }

        AppWidgets.KpiStrip {
            Layout.fillWidth: true
            metrics: root.overviewModel.metrics || []
        }

        ScrollView {
            id: dashboardScrollArea

            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

            ColumnLayout {
                id: dashboardScrollContent

                width: dashboardScrollArea.availableWidth
                spacing: Theme.AppTheme.spacingSm

                DashboardAnalysisPanels {
                    Layout.fillWidth: true
                    workspaceController: root.workspaceController
                    shellModel: root.shellModel
                }

                DashboardChartsSection {
                    Layout.fillWidth: true
                    workspaceController: root.workspaceController
                }

                DashboardOverviewSections {
                    Layout.fillWidth: true
                    Layout.preferredHeight: width >= 1360 ? 520 : 760
                    workspaceController: root.workspaceController
                    shellModel: root.shellModel
                }
            }
        }
    }
}

import QtQuick
import QtQuick.Layouts
import App.Layouts 1.0 as AppLayouts
import App.Theme 1.0 as Theme
import ProjectManagement.Controllers 1.0 as ProjectManagementControllers
import ProjectManagement.Widgets 1.0 as ProjectManagementWidgets

AppLayouts.WorkspaceFrame {
    id: root

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
            "migrationStatus": "QML landing zone ready",
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

    Flickable {
        anchors.fill: parent
        contentWidth: width
        contentHeight: contentColumn.implicitHeight
        clip: true

        ColumnLayout {
            id: contentColumn

            width: parent.width
            spacing: Theme.AppTheme.spacingMd

            DashboardSelectionBar {
                Layout.fillWidth: true
                projectOptions: root.workspaceController ? (root.workspaceController.projectOptions || []) : []
                selectedProjectId: root.workspaceController ? root.workspaceController.selectedProjectId : ""
                baselineOptions: root.workspaceController ? (root.workspaceController.baselineOptions || []) : []
                selectedBaselineId: root.workspaceController ? root.workspaceController.selectedBaselineId : ""
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

                onRefreshRequested: function() {
                    if (root.workspaceController !== null) {
                        root.workspaceController.refresh()
                    }
                }
            }

            ProjectManagementWidgets.WorkspaceStateBanner {
                Layout.fillWidth: true
                isLoading: root.workspaceController ? root.workspaceController.isLoading : false
                isBusy: root.workspaceController ? root.workspaceController.isBusy : false
                errorMessage: root.workspaceController ? root.workspaceController.errorMessage : ""
                feedbackMessage: root.workspaceController ? root.workspaceController.feedbackMessage : ""
            }

            DashboardMetricsSection {
                Layout.fillWidth: true
                metrics: root.overviewModel.metrics || []
            }

            ProjectManagementWidgets.WorkspaceStatusSection {
                Layout.fillWidth: true
                migrationStatus: root.workspaceController
                    ? "QML read-only dashboard slice active"
                    : (root.workspaceModel.migrationStatus || "")
                legacyRuntimeStatus: root.workspaceModel.legacyRuntimeStatus || ""
                architectureStatus: "Desktop API dashboard"
                architectureSummary: "Project selection, baseline selection, KPI cards, and read-only delivery sections flow through a typed controller backed by the PM desktop API."
            }

            DashboardOverviewSections {
                Layout.fillWidth: true
                workspaceController: root.workspaceController
                emptyState: root.workspaceController ? root.workspaceController.emptyState : ""
            }
        }
    }
}

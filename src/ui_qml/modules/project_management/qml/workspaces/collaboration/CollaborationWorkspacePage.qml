import QtQuick
import QtQuick.Layouts
import App.Layouts 1.0 as AppLayouts
import ProjectManagement.Controllers 1.0 as ProjectManagementControllers
import ProjectManagement.Widgets 1.0 as ProjectManagementWidgets

AppLayouts.WorkspaceFrame {
    id: root

    property ProjectManagementControllers.ProjectManagementWorkspaceCatalog pmCatalog
    property ProjectManagementControllers.ProjectManagementCollaborationWorkspaceController workspaceController: root.pmCatalog
        ? root.pmCatalog.collaborationWorkspace
        : null
    readonly property var workspaceModel: root.workspaceController
        ? root.workspaceController.workspace
        : ({
            "routeId": "project_management.collaboration",
            "title": "Collaboration",
            "summary": "Notes, shared discussions, import collaboration, and team coordination.",
            "migrationStatus": "QML landing zone ready",
            "legacyRuntimeStatus": "Existing QWidget collaboration workspace remains active"
        })
    readonly property var overviewModel: root.workspaceController
        ? root.workspaceController.overview
        : ({
            "title": root.workspaceModel.title,
            "subtitle": root.workspaceModel.summary,
            "metrics": []
        })
    readonly property var notificationsModel: root.workspaceController
        ? root.workspaceController.notifications
        : ({
            "title": "Notifications",
            "subtitle": "Workflow notifications for PM activity, approvals, and timesheet review.",
            "emptyState": "Project-management collaboration desktop API is not connected in this QML preview.",
            "items": []
        })
    readonly property var inboxModel: root.workspaceController
        ? root.workspaceController.inbox
        : ({
            "title": "Mentions",
            "subtitle": "Mentions needing review. Mark a task as read after follow-up.",
            "emptyState": "Project-management collaboration desktop API is not connected in this QML preview.",
            "items": []
        })
    readonly property var recentActivityModel: root.workspaceController
        ? root.workspaceController.recentActivity
        : ({
            "title": "Recent Activity",
            "subtitle": "Recent PM collaboration updates across the accessible project set.",
            "emptyState": "Project-management collaboration desktop API is not connected in this QML preview.",
            "items": []
        })
    readonly property var activePresenceModel: root.workspaceController
        ? root.workspaceController.activePresence
        : ({
            "title": "Active Now",
            "subtitle": "People currently active in PM task collaboration and review flows.",
            "emptyState": "Project-management collaboration desktop API is not connected in this QML preview.",
            "items": []
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
            spacing: 12

            CollaborationMetricsSection {
                Layout.fillWidth: true
                metrics: root.overviewModel.metrics || []
            }

            ProjectManagementWidgets.WorkspaceStateBanner {
                Layout.fillWidth: true
                isLoading: root.workspaceController ? root.workspaceController.isLoading : false
                isBusy: root.workspaceController ? root.workspaceController.isBusy : false
                errorMessage: root.workspaceController ? root.workspaceController.errorMessage : ""
                feedbackMessage: root.workspaceController ? root.workspaceController.feedbackMessage : ""
            }

            ProjectManagementWidgets.WorkspaceStatusSection {
                Layout.fillWidth: true
                migrationStatus: root.workspaceController
                    ? "QML collaboration inbox slice active"
                    : (root.workspaceModel.migrationStatus || "")
                legacyRuntimeStatus: root.workspaceModel.legacyRuntimeStatus || ""
                architectureStatus: "Desktop API + typed controller"
                architectureSummary: "Mentions, approval and timesheet notifications, recent activity, and active collaboration presence now flow through a typed PM collaboration controller backed by the collaboration desktop API."
            }

            CollaborationToolbarSection {
                Layout.fillWidth: true
                isBusy: root.workspaceController ? root.workspaceController.isBusy : false
                onRefreshRequested: function() {
                    if (root.workspaceController !== null) {
                        root.workspaceController.refresh()
                    }
                }
            }

            GridLayout {
                Layout.fillWidth: true
                columns: root.width > 1180 ? 2 : 1
                columnSpacing: 12
                rowSpacing: 12

                ProjectManagementWidgets.RecordListCard {
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignTop
                    title: String(root.notificationsModel.title || "")
                    subtitle: String(root.notificationsModel.subtitle || "")
                    emptyState: String(root.notificationsModel.emptyState || "")
                    items: root.notificationsModel.items || []
                }

                ProjectManagementWidgets.RecordListCard {
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignTop
                    title: String(root.inboxModel.title || "")
                    subtitle: String(root.inboxModel.subtitle || "")
                    emptyState: String(root.inboxModel.emptyState || "")
                    items: root.inboxModel.items || []
                    primaryActionLabel: "Mark Read"
                    actionsEnabled: root.workspaceController ? !root.workspaceController.isBusy : false

                    onPrimaryActionRequested: function(itemData) {
                        if (
                            root.workspaceController !== null
                            && itemData
                            && itemData.state
                            && itemData.state.taskId
                        ) {
                            root.workspaceController.markTaskRead(String(itemData.state.taskId || ""))
                        }
                    }
                }

                ProjectManagementWidgets.RecordListCard {
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignTop
                    title: String(root.recentActivityModel.title || "")
                    subtitle: String(root.recentActivityModel.subtitle || "")
                    emptyState: String(root.recentActivityModel.emptyState || "")
                    items: root.recentActivityModel.items || []
                }

                ProjectManagementWidgets.RecordListCard {
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignTop
                    title: String(root.activePresenceModel.title || "")
                    subtitle: String(root.activePresenceModel.subtitle || "")
                    emptyState: String(root.activePresenceModel.emptyState || "")
                    items: root.activePresenceModel.items || []
                }
            }
        }
    }
}

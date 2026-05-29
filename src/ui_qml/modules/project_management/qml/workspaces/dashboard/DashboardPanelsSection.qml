pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Theme 1.0 as Theme
import ProjectManagement.Controllers 1.0 as ProjectManagementControllers

Item {
    id: root

    property ProjectManagementControllers.ProjectManagementDashboardWorkspaceController workspaceController

    readonly property var panelsModel: root.workspaceController
        ? (root.workspaceController.panels || [])
        : []
    readonly property int panelColumns: width >= 1360
        ? 3
        : width >= 900
            ? 2
            : 1

    implicitHeight: panelsGrid.implicitHeight
    visible: root.panelsModel.length > 0

    GridLayout {
        id: panelsGrid

        anchors.fill: parent
        columns: root.panelColumns
        columnSpacing: Theme.AppTheme.spacingSm
        rowSpacing: Theme.AppTheme.spacingSm

        Repeater {
            model: root.panelsModel

            delegate: DashboardPanelFrame {
                required property var modelData
                required property int index

                Layout.fillWidth: true
                Layout.alignment: Qt.AlignTop
                title: modelData.title || ""
                subtitle: modelData.subtitle || ""

                DashboardInsightPanel {
                    Layout.fillWidth: true
                    hint: modelData.hint || ""
                    emptyState: modelData.emptyState || ""
                    metrics: modelData.metrics || []
                }
            }
        }
    }
}

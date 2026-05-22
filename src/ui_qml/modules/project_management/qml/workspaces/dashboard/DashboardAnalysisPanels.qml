pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Theme 1.0 as Theme
import ProjectManagement.Controllers 1.0 as ProjectManagementControllers

Item {
    id: root

    property ProjectManagementControllers.ProjectManagementDashboardWorkspaceController workspaceController
    property var shellModel: null

    readonly property var healthCardsModel: root.workspaceController
        ? (root.workspaceController.healthCards || [])
        : []
    readonly property int cardColumns: width >= 1320
        ? 4
        : width >= 900
            ? 2
            : 1

    implicitHeight: healthGrid.implicitHeight

    GridLayout {
        id: healthGrid

        anchors.fill: parent
        columns: root.cardColumns
        columnSpacing: Theme.AppTheme.spacingSm
        rowSpacing: Theme.AppTheme.spacingSm

        Repeater {
            model: root.healthCardsModel

            delegate: DashboardHealthCard {
                required property var modelData

                Layout.fillWidth: true
                model: modelData
                shellModel: root.shellModel
            }
        }
    }
}

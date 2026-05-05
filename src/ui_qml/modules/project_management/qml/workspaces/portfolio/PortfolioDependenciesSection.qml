import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme
import ProjectManagement.Widgets 1.0 as ProjectManagementWidgets

Rectangle {
    id: root

    property var projectOptions: []
    property var dependencyTypeOptions: []
    property var dependenciesModel: ({
        "title": "",
        "subtitle": "",
        "emptyState": "",
        "items": []
    })
    property bool isBusy: false

    signal createRequested(var payload)
    signal removeRequested(string dependencyId)

    radius: Theme.AppTheme.radiusLg
    color: Theme.AppTheme.surface
    border.color: Theme.AppTheme.border
    implicitHeight: contentColumn.implicitHeight + (Theme.AppTheme.marginLg * 2)

    ColumnLayout {
        id: contentColumn

        anchors.fill: parent
        anchors.margins: Theme.AppTheme.marginLg
        spacing: Theme.AppTheme.spacingMd

        GridLayout {
            Layout.fillWidth: true
            columns: root.width > 760 ? 2 : 1
            columnSpacing: Theme.AppTheme.spacingMd
            rowSpacing: Theme.AppTheme.spacingSm

            ComboBox {
                id: predecessorCombo
                Layout.fillWidth: true
                model: root.projectOptions
                textRole: "label"
                enabled: !root.isBusy
            }

            ComboBox {
                id: successorCombo
                Layout.fillWidth: true
                model: root.projectOptions
                textRole: "label"
                enabled: !root.isBusy
            }

            ComboBox {
                id: dependencyTypeCombo
                Layout.fillWidth: true
                model: root.dependencyTypeOptions
                textRole: "label"
                enabled: !root.isBusy
            }

            TextField {
                id: summaryField
                Layout.fillWidth: true
                enabled: !root.isBusy
                placeholderText: "Shared commissioning gate"
            }
        }

        AppControls.PrimaryButton {
            text: "Add Dependency"
            enabled: !root.isBusy
            onClicked: {
                var predecessor = predecessorCombo.currentIndex >= 0 ? root.projectOptions[predecessorCombo.currentIndex] : null
                var successor = successorCombo.currentIndex >= 0 ? root.projectOptions[successorCombo.currentIndex] : null
                var dependencyType = dependencyTypeCombo.currentIndex >= 0 ? root.dependencyTypeOptions[dependencyTypeCombo.currentIndex] : null
                root.createRequested({
                    "predecessorProjectId": predecessor ? predecessor.value : "",
                    "successorProjectId": successor ? successor.value : "",
                    "dependencyType": dependencyType ? dependencyType.value : "FINISH_TO_START",
                    "summary": summaryField.text
                })
                summaryField.text = ""
            }
        }

        ProjectManagementWidgets.RecordListCard {
            Layout.fillWidth: true
            title: root.dependenciesModel.title || "Cross-project Dependencies"
            subtitle: root.dependenciesModel.subtitle || ""
            emptyState: root.dependenciesModel.emptyState || ""
            items: root.dependenciesModel.items || []
            primaryActionLabel: "Remove"
            primaryDanger: true
            actionsEnabled: !root.isBusy

            onPrimaryActionRequested: function(itemData) {
                var state = itemData && itemData.state ? itemData.state : {}
                if (state.dependencyId) {
                    root.removeRequested(String(state.dependencyId))
                }
            }
        }
    }
}

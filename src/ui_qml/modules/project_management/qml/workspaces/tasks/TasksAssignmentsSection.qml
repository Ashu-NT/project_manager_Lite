import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Mock 1.0 as AppMock
import App.Theme 1.0 as Theme
import ProjectManagement.Widgets 1.0 as ProjectManagementWidgets

Item {
    id: root

    property var assignmentsModel: AppMock.MockFactory.catalog()
    property string selectedAssignmentId: ""
    property bool isBusy: false
    property bool canCreate: false

    signal createRequested()
    signal assignmentSelected(string assignmentId)
    signal editAllocationRequested(var assignmentData)
    signal setHoursRequested(var assignmentData)
    signal deleteRequested(var assignmentData)

    implicitHeight: sectionLayout.implicitHeight

    ColumnLayout {
        id: sectionLayout

        anchors.fill: parent
        spacing: Theme.AppTheme.spacingMd

        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.AppTheme.spacingSm

            ColumnLayout {
                Layout.fillWidth: true
                spacing: Theme.AppTheme.spacingXs

                Text {
                    Layout.fillWidth: true
                    text: String(root.assignmentsModel.title || "Assignments")
                    color: Theme.AppTheme.textPrimary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.bodySize
                    font.bold: true
                    wrapMode: Text.WordWrap
                }

                Text {
                    Layout.fillWidth: true
                    text: String(root.assignmentsModel.subtitle || "")
                    color: Theme.AppTheme.textSecondary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                    wrapMode: Text.WordWrap
                    visible: text.length > 0
                }
            }

            AppControls.PrimaryButton {
                text: "Assign Resource"
                iconName: "resources"
                enabled: root.canCreate && !root.isBusy
                onClicked: root.createRequested()
            }
        }

        ProjectManagementWidgets.RecordListCard {
            Layout.fillWidth: true
            title: ""
            subtitle: ""
            emptyState: root.assignmentsModel.emptyState || ""
            items: root.assignmentsModel.items || []
            selectedItemId: root.selectedAssignmentId
            primaryActionLabel: "Allocation"
            secondaryActionLabel: "Hours"
            tertiaryActionLabel: "Remove"
            tertiaryDanger: true
            actionsEnabled: !root.isBusy

            onItemSelected: function(itemId) {
                root.assignmentSelected(itemId)
            }

            onPrimaryActionRequested: function(itemData) {
                root.editAllocationRequested(itemData)
            }

            onSecondaryActionRequested: function(itemData) {
                root.setHoursRequested(itemData)
            }

            onTertiaryActionRequested: function(itemData) {
                root.deleteRequested(itemData)
            }
        }
    }
}

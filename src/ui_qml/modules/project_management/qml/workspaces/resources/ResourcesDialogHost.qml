import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Theme 1.0 as Theme
import ProjectManagement.Dialogs 1.0 as ProjectManagementDialogs

Item {
    id: root

    property var workerTypeOptions: []
    property var categoryOptions: []
    property var employeeOptions: []
    property var editTarget: ({})
    property var deleteTarget: ({})

    signal createRequested(var payload)
    signal updateRequested(var payload)
    signal deleteRequested(string resourceId)

    function openCreateDialog() {
        root.editTarget = {
            "state": {
                "workerType": "EXTERNAL",
                "costType": "LABOR",
                "isActive": true,
                "capacityPercent": "100.0"
            }
        }
        editorDialog.modeTitle = "Create Resource"
        editorDialog.resourceData = root.editTarget
        editorDialog.open()
    }

    function openEditDialog(resourceData) {
        root.editTarget = resourceData || ({})
        editorDialog.modeTitle = "Edit Resource"
        editorDialog.resourceData = root.editTarget
        editorDialog.open()
    }

    function openDeleteDialog(resourceData) {
        root.deleteTarget = resourceData || ({})
        deleteDialog.open()
    }

    ProjectManagementDialogs.ResourceEditorDialog {
        id: editorDialog

        workerTypeOptions: root.workerTypeOptions
        categoryOptions: root.categoryOptions
        employeeOptions: root.employeeOptions

        onSubmitted: function(payload) {
            var state = root.editTarget && root.editTarget.state ? root.editTarget.state : (root.editTarget || {})
            if (state.resourceId) {
                payload.resourceId = state.resourceId
                payload.expectedVersion = state.version
                root.updateRequested(payload)
            } else {
                root.createRequested(payload)
            }
            editorDialog.close()
        }
    }

    Dialog {
        id: deleteDialog

        modal: true
        title: "Delete Resource"
        standardButtons: Dialog.Cancel | Dialog.Ok
        closePolicy: Popup.CloseOnEscape

        background: Rectangle {
            radius: Theme.AppTheme.radiusLg
            color: Theme.AppTheme.surface
            border.color: Theme.AppTheme.border
        }

        contentItem: ColumnLayout {
            spacing: Theme.AppTheme.spacingSm

            Label {
                Layout.fillWidth: true
                text: root.deleteTarget && root.deleteTarget.title
                    ? "Delete " + root.deleteTarget.title + " and its related assignments?"
                    : "Delete the selected resource and its related assignments?"
                color: Theme.AppTheme.textPrimary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.bodySize
                wrapMode: Text.WordWrap
            }

            Label {
                Layout.fillWidth: true
                text: "This action removes the resource record and any PM assignments or linked allocation history that depends on it."
                color: Theme.AppTheme.textSecondary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.smallSize
                wrapMode: Text.WordWrap
            }
        }

        onAccepted: {
            var state = root.deleteTarget && root.deleteTarget.state ? root.deleteTarget.state : (root.deleteTarget || {})
            if (state.resourceId) {
                root.deleteRequested(String(state.resourceId))
            }
        }
    }
}

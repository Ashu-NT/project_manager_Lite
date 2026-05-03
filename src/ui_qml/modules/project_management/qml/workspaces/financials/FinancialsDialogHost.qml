import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Theme 1.0 as Theme
import ProjectManagement.Dialogs 1.0 as ProjectManagementDialogs

Item {
    id: root

    property string selectedProjectId: ""
    property var taskOptions: []
    property var costTypeOptions: []
    property var editTarget: ({})
    property var deleteTarget: ({})

    signal createRequested(var payload)
    signal updateRequested(var payload)
    signal deleteRequested(string costId)

    function openCreateDialog() {
        root.editTarget = {
            "state": {
                "costType": "OVERHEAD",
                "plannedAmount": "0.00",
                "committedAmount": "0.00",
                "actualAmount": "0.00"
            }
        }
        editorDialog.modeTitle = "Create Cost Item"
        editorDialog.costData = root.editTarget
        editorDialog.open()
    }

    function openEditDialog(costData) {
        root.editTarget = costData || ({})
        editorDialog.modeTitle = "Edit Cost Item"
        editorDialog.costData = root.editTarget
        editorDialog.open()
    }

    function openDeleteDialog(costData) {
        root.deleteTarget = costData || ({})
        deleteDialog.open()
    }

    ProjectManagementDialogs.CostItemEditorDialog {
        id: editorDialog

        taskOptions: root.taskOptions
        costTypeOptions: root.costTypeOptions

        onSubmitted: function(payload) {
            var state = root.editTarget && root.editTarget.state ? root.editTarget.state : (root.editTarget || {})
            if (state.costId) {
                payload.costId = state.costId
                payload.expectedVersion = state.version
                root.updateRequested(payload)
            } else {
                payload.projectId = root.selectedProjectId
                root.createRequested(payload)
            }
            editorDialog.close()
        }
    }

    Dialog {
        id: deleteDialog

        modal: true
        title: "Delete Cost Item"
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
                    ? "Delete " + root.deleteTarget.title + " from the selected project?"
                    : "Delete the selected cost item from the selected project?"
                color: Theme.AppTheme.textPrimary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.bodySize
                wrapMode: Text.WordWrap
            }

            Label {
                Layout.fillWidth: true
                text: "This removes the financial line from cost control, finance snapshots, and related project reporting."
                color: Theme.AppTheme.textSecondary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.smallSize
                wrapMode: Text.WordWrap
            }
        }

        onAccepted: {
            var state = root.deleteTarget && root.deleteTarget.state ? root.deleteTarget.state : (root.deleteTarget || {})
            if (state.costId) {
                root.deleteRequested(String(state.costId))
            }
        }
    }
}

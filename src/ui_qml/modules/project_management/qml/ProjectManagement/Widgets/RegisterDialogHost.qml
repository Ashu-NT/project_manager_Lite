import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Theme 1.0 as Theme
import ProjectManagement.Dialogs 1.0 as ProjectManagementDialogs

Item {
    id: root

    property var projectOptions: []
    property var typeOptions: []
    property var statusOptions: []
    property var severityOptions: []
    property bool typeFieldVisible: true
    property string fixedTypeValue: "RISK"
    property string entryLabel: "Register Entry"
    property var editTarget: ({})
    property var deleteTarget: ({})

    signal createRequested(var payload)
    signal updateRequested(var payload)
    signal deleteRequested(string entryId)

    function openCreateDialog() {
        root.editTarget = {
            "state": {
                "type": root.fixedTypeValue,
                "status": "OPEN",
                "severity": "MEDIUM"
            }
        }
        editorDialog.modeTitle = "Create " + root.entryLabel
        editorDialog.entryData = root.editTarget
        editorDialog.open()
    }

    function openEditDialog(entryData) {
        root.editTarget = entryData || ({})
        editorDialog.modeTitle = "Edit " + root.entryLabel
        editorDialog.entryData = root.editTarget
        editorDialog.open()
    }

    function openDeleteDialog(entryData) {
        root.deleteTarget = entryData || ({})
        deleteDialog.open()
    }

    ProjectManagementDialogs.RegisterEntryEditorDialog {
        id: editorDialog

        projectOptions: root.projectOptions
        typeOptions: root.typeOptions
        statusOptions: root.statusOptions
        severityOptions: root.severityOptions
        typeFieldVisible: root.typeFieldVisible
        fixedTypeValue: root.fixedTypeValue

        onSubmitted: function(payload) {
            var state = root.editTarget && root.editTarget.state ? root.editTarget.state : (root.editTarget || {})
            if (state.entryId) {
                payload.entryId = state.entryId
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
        title: "Delete " + root.entryLabel
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
                    ? "Delete " + root.deleteTarget.title + " from the project register?"
                    : "Delete the selected project register entry?"
                color: Theme.AppTheme.textPrimary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.bodySize
                wrapMode: Text.WordWrap
            }

            Label {
                Layout.fillWidth: true
                text: "This removes the entry, its mitigation notes, and its current governance state from the PM register."
                color: Theme.AppTheme.textSecondary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.smallSize
                wrapMode: Text.WordWrap
            }
        }

        onAccepted: {
            var state = root.deleteTarget && root.deleteTarget.state ? root.deleteTarget.state : (root.deleteTarget || {})
            if (state.entryId) {
                root.deleteRequested(String(state.entryId))
            }
        }
    }
}

import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

AppWidgets.EntityDialog {
    id: root
    objectName: "costCodeEditorDialog"

    property string selectedProjectId: ""

    signal submitted(var payload)

    title: "Create Cost Code"
    subtitle: "Add an organization Finance code and make it available to the selected project."
    primaryText: "Create Cost Code"
    primaryIcon: "add"
    primaryEnabled: root.selectedProjectId.length > 0
    infoMessage: root.selectedProjectId.length === 0
        ? "Select a project before creating a cost code."
        : "The code is organization-owned and will be available to the selected project."

    onRejected: root.close()
    onOpened: {
        codeField.text = ""
        nameField.text = ""
        descriptionField.text = ""
        root.errorMessage = ""
        codeField.forceActiveFocus()
    }

    function submitDialog() {
        const code = codeField.text.trim().toUpperCase()
        const name = nameField.text.trim()
        if (code.length === 0) {
            root.errorMessage = "Cost code is required."
            codeField.forceActiveFocus()
            return
        }
        if (!/^[A-Z0-9._-]{1,64}$/.test(code)) {
            root.errorMessage = "Cost code must use only letters, numbers, dots, underscores, or hyphens."
            codeField.forceActiveFocus()
            return
        }
        if (name.length === 0) {
            root.errorMessage = "Cost-code name is required."
            nameField.forceActiveFocus()
            return
        }
        root.errorMessage = ""
        root.submitted({
            "projectId": root.selectedProjectId,
            "code": code,
            "name": name,
            "description": descriptionField.text.trim()
        })
    }

    GridLayout {
        Layout.fillWidth: true
        columns: width >= 520 ? 2 : 1
        columnSpacing: Theme.AppTheme.spacingMd
        rowSpacing: Theme.AppTheme.spacingSm

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Code"
            required: true
            AppControls.TextField {
                id: codeField
                Layout.fillWidth: true
                placeholderText: "LABOR.INTERNAL"
            }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Name"
            required: true
            AppControls.TextField {
                id: nameField
                Layout.fillWidth: true
                placeholderText: "Internal labor"
            }
        }

        AppWidgets.FormField {
            Layout.columnSpan: parent.columns
            Layout.fillWidth: true
            label: "Description"
            AppControls.TextArea {
                id: descriptionField
                Layout.fillWidth: true
                Layout.preferredHeight: 88
                placeholderText: "Optional usage guidance"
                wrapMode: TextEdit.WordWrap
            }
        }
    }
}

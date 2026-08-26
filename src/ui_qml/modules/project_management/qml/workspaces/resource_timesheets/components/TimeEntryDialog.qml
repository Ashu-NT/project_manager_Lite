pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme
import App.Widgets 1.0 as AppWidgets

AppWidgets.EntityDialog {
    id: root

    property var assignmentOptions: []
    property var entry: ({})
    property string defaultDate: ""
    property bool editing: Boolean(root.entry && root.entry.entryId)
    signal submitted(var payload)

    title: root.editing ? "Edit Time Entry" : "Add Time Entry"
    subtitle: root.editing
        ? "Correct the authoritative recorded-work entry."
        : "Record actual work against one of your task assignments."
    primaryText: root.editing ? "Save Changes" : "Add Time"
    primaryIcon: root.editing ? "save" : "add"
    showDestructive: root.editing && root.entry.canDelete === true
    destructiveText: "Delete Entry"
    busy: false

    function optionIndex(value) {
        for (let i = 0; i < root.assignmentOptions.length; i += 1) {
            if (String(root.assignmentOptions[i].value || "") === String(value || "")) return i
        }
        return root.assignmentOptions.length === 1 ? 0 : -1
    }

    function prepare(value) {
        root.entry = value || ({})
        assignmentField.currentIndex = root.optionIndex(root.entry.assignmentId || "")
        dateField.text = String(root.entry.workDate || root.defaultDate || "")
        hoursField.text = root.entry.hoursValue === undefined ? "" : String(root.entry.hoursValue)
        noteField.text = String(root.entry.description || "")
        root.errorMessage = ""
    }

    function submitDialog() {
        const option = assignmentField.currentIndex >= 0
            ? root.assignmentOptions[assignmentField.currentIndex]
            : null
        if (!root.editing && !option) {
            root.errorMessage = "Choose a task assignment."
            return
        }
        if (dateField.text.trim().length === 0 || hoursField.text.trim().length === 0) {
            root.errorMessage = "Date and hours are required."
            return
        }
        root.submitted({
            "entryId": String(root.entry.entryId || ""),
            "expectedVersion": Number(root.entry.version || 0),
            "assignmentId": option ? String(option.value || "") : String(root.entry.assignmentId || ""),
            "entryDate": dateField.text.trim(),
            "hours": hoursField.text.trim(),
            "note": noteField.text.trim()
        })
    }

    GridLayout {
        Layout.fillWidth: true
        Layout.leftMargin: Theme.AppTheme.dialogPadding
        Layout.rightMargin: Theme.AppTheme.dialogPadding
        columns: width >= 480 ? 2 : 1
        columnSpacing: Theme.AppTheme.spacingMd
        rowSpacing: Theme.AppTheme.spacingMd

        AppWidgets.FormField {
            Layout.fillWidth: true
            Layout.columnSpan: parent.columns
            label: "Task assignment"
            required: true

            AppControls.ComboBox {
                id: assignmentField
                Layout.fillWidth: true
                model: root.assignmentOptions
                textRole: "label"
                enabled: !root.editing
            }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Date"
            required: true

            AppControls.DateField {
                id: dateField
                Layout.fillWidth: true
                placeholderText: "YYYY-MM-DD"
            }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Hours"
            required: true

            AppControls.TextField {
                id: hoursField
                Layout.fillWidth: true
                placeholderText: "8.00"
            }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            Layout.columnSpan: parent.columns
            label: "Description"

            AppControls.TextArea {
                id: noteField
                Layout.fillWidth: true
                Layout.preferredHeight: 110
                wrapMode: TextEdit.WordWrap
                placeholderText: "Describe the work completed."
            }
        }
    }
}

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme

Dialog {
    id: root

    property string modeTitle: "Create Task"
    property var statusOptions: []
    property var taskData: ({})
    readonly property var workflowStatusOptions: (root.statusOptions || []).filter(function(option) {
        return String(option.value || "").toLowerCase() !== "all"
    })

    signal submitted(var payload)

    modal: true
    width: 560
    height: Math.min(640, parent ? parent.height - (Theme.AppTheme.marginLg * 2) : 640)
    title: root.modeTitle
    closePolicy: Popup.CloseOnEscape

    function statusIndexForValue(statusValue) {
        for (var index = 0; index < root.workflowStatusOptions.length; index += 1) {
            if (String(root.workflowStatusOptions[index].value || "") === String(statusValue || "")) {
                return index
            }
        }
        return 0
    }

    function populateFromTask() {
        var state = root.taskData && root.taskData.state ? root.taskData.state : (root.taskData || {})
        nameField.text = String(state.name || "")
        startDateField.text = String(state.startDate || "")
        durationField.text = String(state.durationDays || "")
        deadlineField.text = String(state.deadline || "")
        priorityField.text = String(state.priority || "")
        descriptionField.text = String(state.description || "")
        statusCombo.currentIndex = root.statusIndexForValue(state.status || "TODO")
    }

    function buildPayload() {
        var statusOption = root.workflowStatusOptions[statusCombo.currentIndex] || { "value": "TODO" }
        return {
            "name": nameField.text,
            "startDate": startDateField.text,
            "durationDays": durationField.text,
            "deadline": deadlineField.text,
            "priority": priorityField.text,
            "description": descriptionField.text,
            "status": statusOption.value || "TODO"
        }
    }

    onOpened: root.populateFromTask()

    background: Rectangle {
        radius: Theme.AppTheme.radiusLg
        color: Theme.AppTheme.surface
        border.color: Theme.AppTheme.border
    }

    contentItem: Flickable {
        id: dialogFlickable

        contentWidth: width
        contentHeight: formLayout.implicitHeight
        clip: true

        ColumnLayout {
            id: formLayout

            width: dialogFlickable.width
            spacing: Theme.AppTheme.spacingMd

            Label {
                Layout.fillWidth: true
                text: root.modeTitle === "Create Task"
                    ? "Add a delivery task inside the currently selected project."
                    : "Adjust dates, duration, status, and execution metadata for this task."
                color: Theme.AppTheme.textSecondary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.bodySize
                wrapMode: Text.WordWrap
            }

            GridLayout {
                Layout.fillWidth: true
                columns: root.width > 520 ? 2 : 1
                columnSpacing: Theme.AppTheme.spacingMd
                rowSpacing: Theme.AppTheme.spacingSm

                Label { text: "Task name"; color: Theme.AppTheme.textPrimary; font.family: Theme.AppTheme.fontFamily }
                TextField { id: nameField; Layout.fillWidth: true; placeholderText: "Cable Pull" }

                Label { text: "Status"; color: Theme.AppTheme.textPrimary; font.family: Theme.AppTheme.fontFamily }
                ComboBox {
                    id: statusCombo
                    Layout.fillWidth: true
                    model: root.workflowStatusOptions
                    textRole: "label"
                }

                Label { text: "Start date"; color: Theme.AppTheme.textPrimary; font.family: Theme.AppTheme.fontFamily }
                TextField { id: startDateField; Layout.fillWidth: true; placeholderText: "YYYY-MM-DD" }

                Label { text: "Duration"; color: Theme.AppTheme.textPrimary; font.family: Theme.AppTheme.fontFamily }
                TextField { id: durationField; Layout.fillWidth: true; placeholderText: "Working days" }

                Label { text: "Deadline"; color: Theme.AppTheme.textPrimary; font.family: Theme.AppTheme.fontFamily }
                TextField { id: deadlineField; Layout.fillWidth: true; placeholderText: "YYYY-MM-DD" }

                Label { text: "Priority"; color: Theme.AppTheme.textPrimary; font.family: Theme.AppTheme.fontFamily }
                TextField { id: priorityField; Layout.fillWidth: true; placeholderText: "0-100" }
            }

            Label {
                Layout.fillWidth: true
                text: "Description"
                color: Theme.AppTheme.textPrimary
                font.family: Theme.AppTheme.fontFamily
            }

            TextArea {
                id: descriptionField
                Layout.fillWidth: true
                Layout.preferredHeight: 150
                placeholderText: "Execution notes, scope, and completion criteria."
                wrapMode: TextEdit.WordWrap
            }
        }
    }

    footer: RowLayout {
        spacing: Theme.AppTheme.spacingSm

        Item { Layout.fillWidth: true }

        Button {
            text: "Cancel"
            onClicked: root.close()
        }

        AppControls.PrimaryButton {
            text: root.modeTitle === "Create Task" ? "Create Task" : "Save Changes"
            onClicked: root.submitted(root.buildPayload())
        }
    }
}

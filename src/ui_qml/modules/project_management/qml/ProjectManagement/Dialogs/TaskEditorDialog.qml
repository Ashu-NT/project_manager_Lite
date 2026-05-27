import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme

AppControls.CenteredDialog {
    id: root

    property string modeTitle: "Create Task"
    property var projectOptions: []
    property string selectedProjectId: ""
    property var statusOptions: []
    property var taskData: ({})
    property string validationMessage: ""
    readonly property bool editingExistingTask: {
        var state = root.taskData && root.taskData.state ? root.taskData.state : (root.taskData || {})
        return String(state.taskId || "").length > 0
    }
    readonly property var editableProjectOptions: (root.projectOptions || []).filter(function(option) {
        return String(option.value || "").toLowerCase() !== "all"
    })
    readonly property var workflowStatusOptions: (root.statusOptions || []).filter(function(option) {
        return String(option.value || "").toLowerCase() !== "all"
    })

    signal submitted(var payload)

    modal: true
    width: 560
    height: Math.min(640, parent ? parent.height - (Theme.AppTheme.marginLg * 2) : 640)
    title: root.modeTitle
    closePolicy: Popup.CloseOnEscape
    padding: Theme.AppTheme.marginMd

    function statusIndexForValue(statusValue) {
        for (let index = 0; index < root.workflowStatusOptions.length; index += 1) {
            if (String(root.workflowStatusOptions[index].value || "") === String(statusValue || "")) {
                return index
            }
        }
        return 0
    }

    function populateFromTask() {
        var state = root.taskData && root.taskData.state ? root.taskData.state : (root.taskData || {})
        projectCombo.currentIndex = root.indexForValue(root.editableProjectOptions, state.projectId || root.selectedProjectId || "")
        nameField.text = String(state.name || "")
        startDateField.text = String(state.startDate || "")
        durationField.text = String(state.durationDays || "")
        deadlineField.text = String(state.deadline || "")
        priorityField.text = String(state.priority || "")
        descriptionField.text = String(state.description || "")
        statusCombo.currentIndex = root.statusIndexForValue(state.status || "TODO")
        root.validationMessage = ""
    }

    function buildPayload() {
        var statusOption = root.workflowStatusOptions[statusCombo.currentIndex] || { "value": "TODO" }
        return {
            "projectId": String((root.editableProjectOptions[projectCombo.currentIndex] || { "value": "" }).value || ""),
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

    function indexForValue(options, targetValue) {
        for (let index = 0; index < options.length; index += 1) {
            if (String(options[index].value || "") === String(targetValue || "")) {
                return index
            }
        }
        return 0
    }

    function submitDialog() {
        if (!root.editingExistingTask
                && String((root.editableProjectOptions[projectCombo.currentIndex] || { "value": "" }).value || "").length === 0) {
            root.validationMessage = "Choose a project before creating a task."
            return
        }
        if (nameField.text.trim().length === 0) {
            root.validationMessage = "Task name is required."
            return
        }
        root.validationMessage = ""
        root.submitted(root.buildPayload())
    }

    background: Rectangle {
        radius: Theme.AppTheme.radiusLg
        color: Theme.AppTheme.surfaceRaised
        border.color: Theme.AppTheme.divider
        border.width: 1
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

            AppControls.Label {
                Layout.fillWidth: true
                text: root.modeTitle === "Create Task"
                    ? "Add a delivery task and choose the project context when needed."
                    : "Adjust dates, duration, status, and execution metadata for this task."
                color: Theme.AppTheme.textSecondary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.bodySize
                wrapMode: Text.WordWrap
            }

            AppControls.Label {
                Layout.fillWidth: true
                visible: root.validationMessage.length > 0
                text: root.validationMessage
                color: "#8B1E1E"
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.smallSize
                wrapMode: Text.WordWrap
            }

            AppControls.Label {
                Layout.fillWidth: true
                visible: !root.editingExistingTask && root.editableProjectOptions.length === 0
                text: "Create a project before adding a task."
                color: Theme.AppTheme.textSecondary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.smallSize
                wrapMode: Text.WordWrap
            }

            GridLayout {
                Layout.fillWidth: true
                columns: root.width > 520 ? 2 : 1
                columnSpacing: Theme.AppTheme.spacingMd
                rowSpacing: Theme.AppTheme.spacingSm

                AppControls.Label { text: "Task name"; color: Theme.AppTheme.textPrimary; font.family: Theme.AppTheme.fontFamily }
                AppControls.TextField { id: nameField; Layout.fillWidth: true; placeholderText: "Cable Pull" }

                AppControls.Label { text: "Project"; color: Theme.AppTheme.textPrimary; font.family: Theme.AppTheme.fontFamily }
                AppControls.ComboBox {
                    id: projectCombo
                    Layout.fillWidth: true
                    model: root.editableProjectOptions
                    textRole: "label"
                    enabled: !root.editingExistingTask
                }

                AppControls.Label { text: "Status"; color: Theme.AppTheme.textPrimary; font.family: Theme.AppTheme.fontFamily }
                AppControls.ComboBox {
                    id: statusCombo
                    Layout.fillWidth: true
                    model: root.workflowStatusOptions
                    textRole: "label"
                }

                AppControls.Label { text: "Start date"; color: Theme.AppTheme.textPrimary; font.family: Theme.AppTheme.fontFamily }
                AppControls.DateField { id: startDateField; Layout.fillWidth: true; placeholderText: "YYYY-MM-DD" }

                AppControls.Label { text: "Duration"; color: Theme.AppTheme.textPrimary; font.family: Theme.AppTheme.fontFamily }
                AppControls.TextField { id: durationField; Layout.fillWidth: true; placeholderText: "Working days" }

                AppControls.Label { text: "Deadline"; color: Theme.AppTheme.textPrimary; font.family: Theme.AppTheme.fontFamily }
                AppControls.DateField { id: deadlineField; Layout.fillWidth: true; placeholderText: "YYYY-MM-DD" }

                AppControls.Label { text: "Priority"; color: Theme.AppTheme.textPrimary; font.family: Theme.AppTheme.fontFamily }
                AppControls.TextField { id: priorityField; Layout.fillWidth: true; placeholderText: "0-100" }
            }

            AppControls.Label {
                Layout.fillWidth: true
                text: "Description"
                color: Theme.AppTheme.textPrimary
                font.family: Theme.AppTheme.fontFamily
            }

            AppControls.TextArea {
                id: descriptionField
                Layout.fillWidth: true
                Layout.preferredHeight: 150
                placeholderText: "Execution notes, scope, and completion criteria."
                wrapMode: TextEdit.WordWrap
            }
        }
    }

    footer: AppControls.DialogActionFooter {

        Item { Layout.fillWidth: true }

        AppControls.SecondaryButton {
            objectName: "dialogCancelButton"
            text: "Cancel"
            iconName: "close"
            onClicked: root.close()
        }

        AppControls.PrimaryButton {
            objectName: "dialogSubmitButton"
            text: root.modeTitle === "Create Task" ? "Create Task" : "Save Changes"
            iconName: root.modeTitle === "Create Task" ? "add" : "save"
            enabled: root.editingExistingTask || root.editableProjectOptions.length > 0
            onClicked: root.submitDialog()
        }
    }
}


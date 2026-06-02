import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

AppWidgets.EntityDialog {
    id: root

    property string modeTitle: "Create Task"
    property var projectOptions: []
    property string selectedProjectId: ""
    property var statusOptions: []
    property var taskData: ({})
    property var workspaceController: null
    property string taskCode: ""
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

    title:        root.modeTitle
    subtitle:     root.modeTitle === "Create Task"
        ? "Add a delivery task and choose the project context when needed."
        : "Adjust dates, duration, status, and execution metadata for this task."
    primaryText:  root.modeTitle === "Create Task" ? "Create Task" : "Save Changes"
    primaryIcon:  root.modeTitle === "Create Task" ? "add" : "save"
    primaryEnabled: root.editingExistingTask || root.editableProjectOptions.length > 0
    width: 560

    onOpened:   root.populateFromTask()
    onAccepted: root.submitDialog()
    onRejected: root.close()

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
        root.taskCode = String(state.taskCode || "")
        nameField.text = String(state.name || "")
        startDateField.text = String(state.startDate || "")
        durationField.text = String(state.durationDays || "")
        deadlineField.text = String(state.deadline || "")
        priorityField.text = String(state.priority || "")
        descriptionField.text = String(state.description || "")
        statusCombo.currentIndex = root.statusIndexForValue(state.status || "TODO")
        root.errorMessage = ""
    }

    function buildPayload() {
        var statusOption = root.workflowStatusOptions[statusCombo.currentIndex] || { "value": "TODO" }
        return {
            "projectId": String((root.editableProjectOptions[projectCombo.currentIndex] || { "value": "" }).value || ""),
            "name": nameField.text,
            "taskCode": root.taskCode,
            "startDate": startDateField.text,
            "durationDays": durationField.text,
            "deadline": deadlineField.text,
            "priority": priorityField.text,
            "description": descriptionField.text,
            "status": statusOption.value || "TODO"
        }
    }

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
            root.errorMessage = "Choose a project before creating a task."
            return
        }
        if (nameField.text.trim().length === 0) {
            root.errorMessage = "Task name is required."
            return
        }
        root.errorMessage = ""
        root.submitted(root.buildPayload())
    }

    // ── Form content ──────────────────────────────────────────────────────────

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

        AppWidgets.CodeFieldRow {
            Layout.columnSpan: parent.columns
            Layout.fillWidth: true
            label: "Task code"
            value: root.taskCode
            placeholderText: "Auto-generated if empty"
            required: true
            generateVisible: true
            busy: root.workspaceController ? root.workspaceController.isBusy : false
            onValueEdited: function(code) { root.taskCode = code }
            onGenerateRequested: {
                if (root.workspaceController) {
                    const suggested = root.workspaceController.generateEntityCode("task", root.buildPayload())
                    if (suggested && suggested.length > 0) {
                        root.taskCode = suggested
                    }
                }
            }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Task name"
            required: true
            AppControls.TextField { id: nameField; Layout.fillWidth: true; placeholderText: "Cable Pull" }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Project"
            required: true
            AppControls.ComboBox { id: projectCombo; Layout.fillWidth: true; model: root.editableProjectOptions; textRole: "label"; enabled: !root.editingExistingTask }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Status"
            AppControls.ComboBox { id: statusCombo; Layout.fillWidth: true; model: root.workflowStatusOptions; textRole: "label" }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Start date"
            AppControls.DateField { id: startDateField; Layout.fillWidth: true; placeholderText: "YYYY-MM-DD" }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Duration"
            AppControls.TextField { id: durationField; Layout.fillWidth: true; placeholderText: "Working days" }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Deadline"
            AppControls.DateField { id: deadlineField; Layout.fillWidth: true; placeholderText: "YYYY-MM-DD" }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Priority"
            AppControls.TextField { id: priorityField; Layout.fillWidth: true; placeholderText: "0-100" }
        }
    }

    AppWidgets.FormField {
        Layout.fillWidth: true
        label: "Description"
        AppControls.TextArea {
            id: descriptionField
            Layout.fillWidth: true
            Layout.preferredHeight: 150
            placeholderText: "Execution notes, scope, and completion criteria."
            wrapMode: TextEdit.WordWrap
        }
    }
}

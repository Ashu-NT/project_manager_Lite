import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import App.Icons 1.0 as AppIcons

AppWidgets.EntityDialog {
    id: root

    property string modeTitle: "Create Task"
    property var projectOptions: []
    property string selectedProjectId: ""
    property var statusOptions: []
    property var parentTaskOptions: []
    property var taskData: ({})
    property var workspaceController: null
    property string taskCode: ""
    readonly property bool editingExistingTask: {
        var state = root.taskData && root.taskData.state ? root.taskData.state : (root.taskData || {})
        return String(state.taskId || "").length > 0
    }
    readonly property bool editingSummaryTask: {
        var state = root.taskData && root.taskData.state ? root.taskData.state : (root.taskData || {})
        return root.editingExistingTask && Boolean(state.isSummary)
    }
    readonly property var editableProjectOptions: (root.projectOptions || []).filter(function(option) {
        return String(option.value || "").toLowerCase() !== "all"
    })
    readonly property var workflowStatusOptions: (root.statusOptions || []).filter(function(option) {
        return String(option.value || "").toLowerCase() !== "all"
    })
    readonly property var constraintOptions: root.workspaceController ? (root.workspaceController.constraintOptions || []) : []
    readonly property int formColumns: root.width > 760 ? 3 : (root.width > 520 ? 2 : 1)
    readonly property var selectedConstraintOption: root.constraintOptions[constraintTypeCombo.currentIndex] || { "value": "", "requiresDate": false, "category": "flexible", "label": "" }
    property bool advancedSchedulingExpanded: false
    property string _initialConstraintType: ""
    property string _initialConstraintDate: ""

    signal submitted(var payload)

    title:        root.modeTitle
    subtitle:     root.modeTitle === "Create Task"
        ? "Add a delivery task and choose the project context when needed."
        : "Adjust dates, duration, status, and execution metadata for this task."
    primaryText:  root.modeTitle === "Create Task" ? "Create Task" : "Save Changes"
    primaryIcon:  root.modeTitle === "Create Task" ? "add" : "save"
    primaryEnabled: root.editingExistingTask || root.editableProjectOptions.length > 0
    width: 860

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
        parentTaskCombo.currentIndex = root.indexForValue(root.parentTaskOptions, state.parentTaskId || "")
        wbsCodeField.text = String(state.wbsCode || "")
        milestoneCheck.checked = Boolean(state.isMilestone)
        constraintTypeCombo.currentIndex = root.indexForValue(root.constraintOptions, state.constraintType || "")
        constraintDateField.text = String(state.constraintDate || "")
        root._initialConstraintType = String(state.constraintType || "")
        root._initialConstraintDate = String(state.constraintDate || "")
        root.advancedSchedulingExpanded = root._initialConstraintType.length > 0
        root.errorMessage = ""
    }

    function buildPayload() {
        var statusOption = root.workflowStatusOptions[statusCombo.currentIndex] || { "value": "TODO" }
        var constraintOption = root.selectedConstraintOption
        var constraintTypeValue = String(constraintOption.value || "")
        var constraintDateValue = constraintOption.requiresDate ? constraintDateField.text : ""
        return {
            "projectId": String((root.editableProjectOptions[projectCombo.currentIndex] || { "value": "" }).value || ""),
            "name": nameField.text,
            "taskCode": root.taskCode,
            "parentTaskId": String((root.parentTaskOptions[parentTaskCombo.currentIndex] || { "value": "" }).value || ""),
            "wbsCode": wbsCodeField.text,
            "startDate": startDateField.text,
            "durationDays": milestoneCheck.checked ? "0" : durationField.text,
            "deadline": deadlineField.text,
            "priority": priorityField.text,
            "description": descriptionField.text,
            "status": statusOption.value || "TODO",
            "isMilestone": milestoneCheck.checked,
            "constraintType": constraintTypeValue,
            "constraintDate": constraintDateValue,
            "constraintChanged": constraintTypeValue !== root._initialConstraintType
                || constraintDateValue !== root._initialConstraintDate
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
        if (root.selectedConstraintOption.requiresDate && constraintDateField.text.trim().length === 0) {
            root.errorMessage = "Choose a date for the " + (root.selectedConstraintOption.label || "selected") + " constraint."
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
        columns: root.formColumns
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
            AppControls.ComboBox { id: statusCombo; Layout.fillWidth: true; model: root.workflowStatusOptions; textRole: "label"; enabled: !root.editingSummaryTask }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "WBS parent"
            AppControls.ComboBox {
                id: parentTaskCombo
                Layout.fillWidth: true
                model: root.parentTaskOptions
                textRole: "label"
                enabled: !root.editingExistingTask
            }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "WBS code"
            AppControls.TextField {
                id: wbsCodeField
                Layout.fillWidth: true
                placeholderText: "Auto-numbered if empty"
                enabled: !root.editingExistingTask
            }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Start date"
            AppControls.DateField { id: startDateField; Layout.fillWidth: true; placeholderText: "YYYY-MM-DD"; enabled: !root.editingSummaryTask }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Duration"
            AppControls.TextField {
                id: durationField
                Layout.fillWidth: true
                placeholderText: "Working days"
                enabled: !root.editingSummaryTask && !milestoneCheck.checked
            }
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

        AppControls.CheckBox {
            id: milestoneCheck
            objectName: "milestoneCheck"
            Layout.columnSpan: parent.columns
            text: "This is a milestone (zero-duration)"
            enabled: !root.editingSummaryTask
            onCheckedChanged: {
                if (milestoneCheck.checked) {
                    durationField.text = "0"
                }
            }
        }
    }

    ColumnLayout {
        Layout.fillWidth: true
        spacing: Theme.AppTheme.spacingSm

        Item {
            Layout.fillWidth: true
            implicitHeight: advancedHeaderRow.implicitHeight

            RowLayout {
                id: advancedHeaderRow
                anchors.left: parent.left
                anchors.right: parent.right
                spacing: Theme.AppTheme.spacingSm

                AppIcons.AppIcon {
                    name: root.advancedSchedulingExpanded ? "chevron_down" : "chevron_right"
                    size: Theme.AppTheme.navIconSize
                    iconColor: Theme.AppTheme.textMuted
                }

                AppControls.Label {
                    Layout.fillWidth: true
                    text: "Advanced scheduling"
                        + (root._initialConstraintType.length > 0 && !root.advancedSchedulingExpanded
                            ? " · " + (root.constraintOptions[root.indexForValue(root.constraintOptions, root._initialConstraintType)] || {}).code
                            : "")
                    color: Theme.AppTheme.textSecondary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                    font.bold: true
                }
            }

            MouseArea {
                anchors.fill: parent
                cursorShape: Qt.PointingHandCursor
                onClicked: root.advancedSchedulingExpanded = !root.advancedSchedulingExpanded
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            visible: root.advancedSchedulingExpanded
            spacing: Theme.AppTheme.spacingSm

            GridLayout {
                Layout.fillWidth: true
                columns: root.formColumns
                columnSpacing: Theme.AppTheme.spacingMd
                rowSpacing: Theme.AppTheme.spacingSm

                AppWidgets.FormField {
                    Layout.fillWidth: true
                    label: "Scheduling constraint"
                    AppControls.ComboBox {
                        id: constraintTypeCombo
                        objectName: "constraintTypeCombo"
                        Layout.fillWidth: true
                        model: root.constraintOptions
                        textRole: "label"
                        enabled: !root.editingSummaryTask
                    }
                }

                AppWidgets.FormField {
                    Layout.fillWidth: true
                    label: "Constraint date"
                    visible: root.selectedConstraintOption.requiresDate
                    AppControls.DateField {
                        id: constraintDateField
                        objectName: "constraintDateField"
                        Layout.fillWidth: true
                        placeholderText: "YYYY-MM-DD"
                        enabled: !root.editingSummaryTask
                    }
                }
            }

            AppControls.Label {
                Layout.fillWidth: true
                visible: root.selectedConstraintOption.description.length > 0
                text: root.selectedConstraintOption.description
                color: Theme.AppTheme.textSecondary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.smallSize
                wrapMode: Text.WordWrap
            }

            AppWidgets.InlineMessage {
                Layout.fillWidth: true
                visible: root.selectedConstraintOption.category === "fixed_date"
                tone: "warning"
                message: "This fixes the task to an exact date and can override dependency-driven scheduling. "
                    + "Check Schedule Impact after saving for any resulting conflicts."
            }
        }
    }

    AppWidgets.FormField {
        Layout.fillWidth: true
        label: "Description"
        AppControls.TextArea {
            id: descriptionField
            Layout.fillWidth: true
            Layout.preferredHeight: 75
            placeholderText: "Execution notes, scope, and completion criteria."
            wrapMode: TextEdit.WordWrap
        }
    }
}

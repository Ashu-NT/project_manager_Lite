import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

AppWidgets.EntityDialog {
    id: root

    property string mode: "create"
    property string modeTitle: root.mode === "create" ? "Assign Resource" : "Adjust Allocation"
    property var resourceOptions: []
    property var taskData: ({})
    property var assignmentData: ({})
    property var workspaceController: null
    property var _skillValidation: ({})
    property var _availabilityPreview: ({})

    readonly property bool _checksBlocked: root._skillValidation.isBlocked === true
        || root._availabilityPreview.isBlocked === true

    signal submitted(var payload)

    modal: true
    width: 520
    closePolicy: Popup.CloseOnEscape

    title: root.modeTitle
    subtitle: root.mode === "create"
        ? "Link a project resource to the selected task and set the starting allocation."
        : "Adjust the active allocation commitment for this task assignment."
    primaryText: root.mode === "create" ? "Assign Resource" : "Save Allocation"
    primaryIcon: root.mode === "create" ? "resources" : "save"
    primaryEnabled: root.mode !== "create"
        || ((root.resourceOptions || []).length > 0 && !root._checksBlocked)

    onAccepted: root.submitDialog()
    onRejected: root.close()

    function indexForValue(options, targetValue) {
        for (let index = 0; index < options.length; index += 1) {
            if (String(options[index].value || "") === String(targetValue || "")) {
                return index
            }
        }
        return 0
    }

    function selectedTaskState() {
        return root.taskData && root.taskData.state ? root.taskData.state : (root.taskData || {})
    }

    function selectedAssignmentState() {
        return root.assignmentData && root.assignmentData.state
            ? root.assignmentData.state
            : (root.assignmentData || {})
    }

    function populateForm() {
        const taskState = root.selectedTaskState()
        const assignmentState = root.selectedAssignmentState()
        taskLabel.text = String(root.taskData.title || taskState.name || "Selected task")
        resourceCombo.currentIndex = root.indexForValue(
            root.resourceOptions || [],
            assignmentState.projectResourceId || ""
        )
        allocationField.text = String(
            assignmentState.allocationPercent !== undefined
                ? assignmentState.allocationPercent
                : "100.0"
        )
        plannedHoursField.text = ""
        root.errorMessage = ""
        root._skillValidation = {}
        root._availabilityPreview = {}
        Qt.callLater(root.runAssignmentChecks)
    }

    function runAssignmentChecks() {
        if (root.mode !== "create" || root.workspaceController === null) {
            root._skillValidation = {}
            root._availabilityPreview = {}
            return
        }
        const taskState = root.selectedTaskState()
        const option = (root.resourceOptions || [])[resourceCombo.currentIndex] || {}
        const projectResourceId = String(option.value || "")
        const taskId = String(taskState.taskId || "")
        if (!taskId || !projectResourceId) {
            root._skillValidation = {}
            root._availabilityPreview = {}
            return
        }
        const payload = {
            "taskId": taskId,
            "projectResourceId": projectResourceId
        }
        root._skillValidation = root.workspaceController.validateAssignment(payload) || {}
        const assignmentController = root.workspaceController.assignmentsController
        root._availabilityPreview = assignmentController
            ? (assignmentController.previewAssignment(payload) || {})
            : ({})
    }

    function buildPayload() {
        const assignmentState = root.selectedAssignmentState()
        const option = root.resourceOptions[resourceCombo.currentIndex] || {}
        const payload = {
            "taskId": String(root.selectedTaskState().taskId || ""),
            "assignmentId": String(assignmentState.assignmentId || ""),
            "projectResourceId": String(option.value || ""),
            "allocationPercent": allocationField.text,
            "version": assignmentState.version !== undefined ? String(assignmentState.version) : ""
        }
        if (root.mode === "create") {
            payload["plannedHours"] = plannedHoursField.text.trim().length > 0
                ? plannedHoursField.text
                : "0"
        }
        return payload
    }

    function submitDialog() {
        if (root.mode === "create"
                && String((root.resourceOptions[resourceCombo.currentIndex] || { "value": "" }).value || "").length === 0) {
            root.errorMessage = "Select a project resource before creating the assignment."
            return
        }
        if (allocationField.text.trim().length === 0) {
            root.errorMessage = "Allocation percentage is required."
            return
        }
        if (root.mode === "create" && root._checksBlocked) {
            root.errorMessage = "Assignment is blocked by availability, skill, or certification policy."
            return
        }
        root.errorMessage = ""
        root.submitted(root.buildPayload())
    }

    onOpened: root.populateForm()

    AppWidgets.FormField {
        Layout.fillWidth: true
        label: "Task"

        AppControls.Label {
            id: taskLabel

            Layout.fillWidth: true
            color: Theme.AppTheme.textPrimary
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.bodySize
            font.bold: true
            wrapMode: Text.WordWrap
        }
    }

    AppWidgets.FormField {
        Layout.fillWidth: true
        visible: root.mode === "create"
        label: "Project resource"
        required: true

        AppControls.ComboBox {
            id: resourceCombo

            Layout.fillWidth: true
            visible: root.mode === "create"
            model: root.resourceOptions
            textRole: "label"
            onCurrentIndexChanged: Qt.callLater(root.runAssignmentChecks)
        }
    }

    Rectangle {
        id: availabilityPanel

        readonly property bool _hasResult: Object.keys(root._availabilityPreview).length > 0
        readonly property bool _isBlocked: root._availabilityPreview.isBlocked === true
        readonly property real _overallocation: Number(root._availabilityPreview.overallocationPct || 0)
        readonly property bool _hasWarnings: root._availabilityPreview.hasWarnings === true
            || _overallocation > 0
        readonly property var _conflicts: root._availabilityPreview.conflictProjects || []

        Layout.fillWidth: true
        visible: root.mode === "create" && _hasResult
        implicitHeight: visible ? _availabilityCol.implicitHeight + 16 : 0
        radius: Theme.AppTheme.radiusSm
        color: _isBlocked
            ? Theme.AppTheme.dangerSoft
            : _hasWarnings ? Theme.AppTheme.warningSoft : Theme.AppTheme.successSoft
        border.color: _isBlocked
            ? Theme.AppTheme.dangerSoftBorder
            : _hasWarnings ? Theme.AppTheme.warningSoftBorder : Theme.AppTheme.successSoftBorder
        border.width: 1

        ColumnLayout {
            id: _availabilityCol
            anchors { left: parent.left; right: parent.right; top: parent.top; margins: 8 }
            spacing: 4

            AppControls.Label {
                Layout.fillWidth: true
                text: availabilityPanel._isBlocked
                    ? "Availability check blocked this assignment"
                    : availabilityPanel._overallocation > 0
                        ? "Resource would be overallocated by " + availabilityPanel._overallocation + "%"
                        : "Resource availability check passed"
                color: availabilityPanel._isBlocked
                    ? Theme.AppTheme.danger
                    : availabilityPanel._hasWarnings ? Theme.AppTheme.warning : Theme.AppTheme.success
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.smallSize
                font.bold: true
                wrapMode: Text.WordWrap
            }

            AppControls.Label {
                Layout.fillWidth: true
                visible: availabilityPanel._conflicts.length > 0
                text: "Conflicting projects: " + availabilityPanel._conflicts.join(", ")
                color: availabilityPanel._isBlocked ? Theme.AppTheme.danger : Theme.AppTheme.warning
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.smallSize
                wrapMode: Text.WordWrap
            }

            Repeater {
                model: (root._availabilityPreview.blockMessages || [])
                    .concat(root._availabilityPreview.warningMessages || [])
                AppControls.Label {
                    Layout.fillWidth: true
                    text: String(modelData)
                    color: availabilityPanel._isBlocked ? Theme.AppTheme.danger : Theme.AppTheme.warning
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                    wrapMode: Text.WordWrap
                }
            }
        }
    }

    AppControls.Label {
        Layout.fillWidth: true
        visible: root.mode !== "create"
        text: String(root.selectedAssignmentState().resourceName || "")
        color: Theme.AppTheme.textSecondary
        font.family: Theme.AppTheme.fontFamily
        font.pixelSize: Theme.AppTheme.smallSize
        wrapMode: Text.WordWrap
    }

    // Skill/cert validation panel — only shown in create mode when a resource is selected
    Rectangle {
        id: validationPanel

        readonly property bool _hasResult: Object.keys(root._skillValidation).length > 0
        readonly property bool _isBlocked: root._skillValidation.isBlocked === true
        readonly property bool _requiresApproval: root._skillValidation.requiresApproval === true
        readonly property bool _hasWarnings: root._skillValidation.hasWarnings === true
        readonly property bool _isValid: root._skillValidation.isValid !== false

        Layout.fillWidth: true
        visible: root.mode === "create" && _hasResult && (!_isValid || _hasWarnings)
        implicitHeight: visible ? _panelCol.implicitHeight + 16 : 0
        radius: Theme.AppTheme.radiusSm
        color: _isBlocked
            ? Theme.AppTheme.dangerSoft
            : Theme.AppTheme.warningSoft
        border.color: _isBlocked
            ? Theme.AppTheme.dangerSoftBorder
            : Theme.AppTheme.warningSoftBorder
        border.width: 1

        ColumnLayout {
            id: _panelCol
            anchors { left: parent.left; right: parent.right; top: parent.top; margins: 8 }
            spacing: 4

            AppControls.Label {
                Layout.fillWidth: true
                text: validationPanel._isBlocked
                    ? "Assignment blocked — skill requirements not met"
                    : validationPanel._requiresApproval
                        ? "Approval required — override violations present"
                        : "Skill warnings — resource may not meet all requirements"
                color: validationPanel._isBlocked ? Theme.AppTheme.danger : Theme.AppTheme.warning
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.smallSize
                font.bold: true
                wrapMode: Text.WordWrap
            }

            Repeater {
                model: (root._skillValidation.violationMessages || []).concat(root._skillValidation.warningMessages || [])
                AppControls.Label {
                    Layout.fillWidth: true
                    text: "• " + modelData
                    color: validationPanel._isBlocked ? Theme.AppTheme.danger : Theme.AppTheme.warning
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                    wrapMode: Text.WordWrap
                }
            }
        }
    }

    AppWidgets.FormField {
        Layout.fillWidth: true
        label: "Allocation (%)"
        required: true

        AppControls.TextField {
            id: allocationField

            Layout.fillWidth: true
            placeholderText: "0.1 - 100.0"
        }
    }

    AppWidgets.FormField {
        Layout.fillWidth: true
        visible: root.mode === "create"
        label: "Planned Work (h)"

        AppControls.TextField {
            id: plannedHoursField

            Layout.fillWidth: true
            visible: root.mode === "create"
            placeholderText: "0.00 (optional)"
        }
    }

    AppControls.Label {
        Layout.fillWidth: true
        visible: root.mode === "create" && (root.resourceOptions || []).length === 0
        text: "No active project resources are available for this project yet."
        color: Theme.AppTheme.textSecondary
        font.family: Theme.AppTheme.fontFamily
        font.pixelSize: Theme.AppTheme.smallSize
        wrapMode: Text.WordWrap
    }
}

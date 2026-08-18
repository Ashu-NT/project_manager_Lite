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
        if (root.workspaceController === null) {
            root._skillValidation = {}
            root._availabilityPreview = {}
            return
        }
        const taskState = root.selectedTaskState()
        const assignmentState = root.selectedAssignmentState()
        const taskId = String(taskState.taskId || "")
        let projectResourceId = ""
        let excludeAssignmentId = ""
        if (root.mode === "create") {
            const option = (root.resourceOptions || [])[resourceCombo.currentIndex] || {}
            projectResourceId = String(option.value || "")
        } else {
            // Edit mode previews REPLACING the current commitment, not
            // adding a second one alongside it (§17) -- the assignment
            // being edited is excluded from "existing" on the backend side.
            projectResourceId = String(assignmentState.projectResourceId || "")
            excludeAssignmentId = String(assignmentState.assignmentId || "")
        }
        if (!taskId || !projectResourceId) {
            root._skillValidation = {}
            root._availabilityPreview = {}
            return
        }
        const assignmentController = root.workspaceController.assignmentsController
        const previewPayload = {
            "taskId": taskId,
            "projectResourceId": projectResourceId,
            // The preview must reflect what the user actually typed, not a
            // hardcoded 100% -- otherwise preview and enforcement (which
            // uses this same field at submit time) can disagree.
            "proposedAllocationPercent": parseFloat(allocationField.text) || 0,
            "excludeAssignmentId": excludeAssignmentId
        }
        root._availabilityPreview = assignmentController
            ? (assignmentController.previewAssignment(previewPayload) || {})
            : ({})
        if (assignmentController) {
            assignmentController.loadProjectResourceUsage(projectResourceId)
        }
        if (root.mode === "create") {
            root._skillValidation = root.workspaceController.validateAssignment({
                "taskId": taskId,
                "projectResourceId": projectResourceId
            }) || {}
        } else {
            root._skillValidation = {}
        }
    }

    readonly property var _projectResourceUsage: (root.workspaceController && root.workspaceController.assignmentsController)
        ? (root.workspaceController.assignmentsController.projectResourceUsage || {})
        : ({})

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
        readonly property bool _capacityKnown: root._availabilityPreview.capacityKnown === true
        readonly property string _capacityStatus: String(root._availabilityPreview.capacityStatus || "UNKNOWN")
        readonly property bool _overCapacity: _capacityStatus === "OVER_CAPACITY"
        readonly property bool _nearCapacity: _capacityStatus === "NEAR_CAPACITY"
        readonly property bool _hasWarnings: root._availabilityPreview.hasWarnings === true
            || _overCapacity || _nearCapacity
        readonly property var _conflicts: root._availabilityPreview.conflictProjects || []
        readonly property var _usage: root._projectResourceUsage

        Layout.fillWidth: true
        visible: _hasResult
        implicitHeight: visible ? _availabilityCol.implicitHeight + 16 : 0
        radius: Theme.AppTheme.radiusSm
        color: _isBlocked || _overCapacity
            ? Theme.AppTheme.dangerSoft
            : _hasWarnings ? Theme.AppTheme.warningSoft : Theme.AppTheme.successSoft
        border.color: _isBlocked || _overCapacity
            ? Theme.AppTheme.dangerSoftBorder
            : _hasWarnings ? Theme.AppTheme.warningSoftBorder : Theme.AppTheme.successSoftBorder
        border.width: 1

        ColumnLayout {
            id: _availabilityCol
            anchors { left: parent.left; right: parent.right; top: parent.top; margins: 8 }
            spacing: 4

            AppControls.Label {
                Layout.fillWidth: true
                text: !availabilityPanel._capacityKnown
                    ? "Capacity unavailable — a calendar could not be resolved for this resource/period."
                    : availabilityPanel._isBlocked
                        ? "Availability check blocked this assignment"
                        : availabilityPanel._overCapacity
                            ? "⚠ Resource is overallocated during part of this task period."
                            : availabilityPanel._nearCapacity
                                ? "Resource is near capacity for this task period."
                                : "Resource availability check passed"
                color: availabilityPanel._isBlocked || availabilityPanel._overCapacity
                    ? Theme.AppTheme.danger
                    : availabilityPanel._hasWarnings ? Theme.AppTheme.warning
                        : (!availabilityPanel._capacityKnown ? Theme.AppTheme.textMuted : Theme.AppTheme.success)
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.smallSize
                font.bold: true
                wrapMode: Text.WordWrap
            }

            AppControls.Label {
                Layout.fillWidth: true
                visible: availabilityPanel._capacityKnown && availabilityPanel._overCapacity
                text: "Peak utilization: " + availabilityPanel._overallocation.toFixed(0) + "%"
                color: Theme.AppTheme.danger
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.smallSize
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

            AppControls.Label {
                Layout.fillWidth: true
                visible: availabilityPanel._overCapacity && availabilityPanel._conflicts.length === 0
                text: "Resource has another capacity conflict."
                color: Theme.AppTheme.warning
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.smallSize
                wrapMode: Text.WordWrap
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.topMargin: 2
                Layout.preferredHeight: Theme.AppTheme.borderWidthThin
                color: Theme.AppTheme.divider
                visible: availabilityPanel._capacityKnown
            }

            GridLayout {
                Layout.fillWidth: true
                visible: availabilityPanel._capacityKnown
                columns: 2
                columnSpacing: Theme.AppTheme.spacingMd
                rowSpacing: 2

                AppControls.Label {
                    text: "Available capacity"
                    color: Theme.AppTheme.textMuted
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                }
                AppControls.Label {
                    text: String(root._availabilityPreview.availableCapacityHoursLabel || "")
                    color: Theme.AppTheme.textPrimary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                    font.bold: true
                }
                AppControls.Label {
                    text: "Current commitment"
                    color: Theme.AppTheme.textMuted
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                }
                AppControls.Label {
                    text: String(root._availabilityPreview.existingCommittedHoursLabel || "")
                    color: Theme.AppTheme.textPrimary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                    font.bold: true
                }
                AppControls.Label {
                    text: "Proposed commitment"
                    color: Theme.AppTheme.textMuted
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                }
                AppControls.Label {
                    text: String(root._availabilityPreview.proposedCommittedHoursLabel || "")
                    color: Theme.AppTheme.textPrimary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                    font.bold: true
                }
                AppControls.Label {
                    text: "Resulting commitment"
                    color: Theme.AppTheme.textMuted
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                }
                AppControls.Label {
                    text: String(root._availabilityPreview.resultingCommittedHoursLabel || "")
                    color: Theme.AppTheme.textPrimary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                    font.bold: true
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.topMargin: 2
                Layout.preferredHeight: Theme.AppTheme.borderWidthThin
                color: Theme.AppTheme.divider
                visible: !!availabilityPanel._usage.projectResourceId
            }

            AppControls.Label {
                Layout.fillWidth: true
                visible: !!availabilityPanel._usage.projectResourceId
                text: "PROJECT RESOURCE PLAN"
                color: Theme.AppTheme.textMuted
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.captionSize
                font.bold: true
            }

            GridLayout {
                Layout.fillWidth: true
                visible: !!availabilityPanel._usage.projectResourceId
                columns: 2
                columnSpacing: Theme.AppTheme.spacingMd
                rowSpacing: 2

                AppControls.Label {
                    text: "Project planned hours"
                    color: Theme.AppTheme.textMuted
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                }
                AppControls.Label {
                    text: String(availabilityPanel._usage.plannedHoursLabel || "")
                    color: Theme.AppTheme.textPrimary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                    font.bold: true
                }
                AppControls.Label {
                    text: "Already distributed"
                    color: Theme.AppTheme.textMuted
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                }
                AppControls.Label {
                    text: String(availabilityPanel._usage.allocatedToTasksHoursLabel || "")
                    color: Theme.AppTheme.textPrimary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                    font.bold: true
                }
                AppControls.Label {
                    text: "Unallocated"
                    color: Theme.AppTheme.textMuted
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                }
                AppControls.Label {
                    text: String(availabilityPanel._usage.unallocatedPlannedHoursLabel || "")
                    color: Theme.AppTheme.textPrimary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                    font.bold: true
                }
                AppControls.Label {
                    text: "This request"
                    color: Theme.AppTheme.textMuted
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                }
                AppControls.Label {
                    text: (root.mode === "create" ? (plannedHoursField.text || "0") : "—") + " h"
                    color: Theme.AppTheme.textPrimary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                    font.bold: true
                }
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
        helperText: "Percentage of this resource's available capacity committed to this task during the task period."
        required: true

        AppControls.TextField {
            id: allocationField

            Layout.fillWidth: true
            placeholderText: "0.1 - 100.0"
            onTextChanged: Qt.callLater(root.runAssignmentChecks)
        }
    }

    AppWidgets.FormField {
        Layout.fillWidth: true
        visible: root.mode === "create"
        label: "Planned Work (h)"
        helperText: "Portion of this resource's project planned hours assigned to this task."

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

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme

AppControls.CenteredDialog {
    id: root

    property string mode: "create"
    property string modeTitle: root.mode === "create" ? "Assign Resource" : "Adjust Allocation"
    property var resourceOptions: []
    property var taskData: ({})
    property var assignmentData: ({})
    property string validationMessage: ""

    signal submitted(var payload)

    modal: true
    width: 520
    title: root.modeTitle
    closePolicy: Popup.CloseOnEscape
    padding: Theme.AppTheme.marginMd

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
        root.validationMessage = ""
    }

    function buildPayload() {
        const assignmentState = root.selectedAssignmentState()
        const option = root.resourceOptions[resourceCombo.currentIndex] || {}
        return {
            "taskId": String(root.selectedTaskState().taskId || ""),
            "assignmentId": String(assignmentState.assignmentId || ""),
            "projectResourceId": String(option.value || ""),
            "allocationPercent": allocationField.text
        }
    }

    function submitDialog() {
        if (root.mode === "create"
                && String((root.resourceOptions[resourceCombo.currentIndex] || { "value": "" }).value || "").length === 0) {
            root.validationMessage = "Select a project resource before creating the assignment."
            return
        }
        if (allocationField.text.trim().length === 0) {
            root.validationMessage = "Allocation percentage is required."
            return
        }
        root.validationMessage = ""
        root.submitted(root.buildPayload())
    }

    onOpened: root.populateForm()

    background: Rectangle {
        radius: Theme.AppTheme.radiusLg
        color: Theme.AppTheme.surfaceRaised
        border.color: Theme.AppTheme.divider
        border.width: 1
    }

    contentItem: ColumnLayout {
        spacing: Theme.AppTheme.spacingMd

        AppControls.Label {
            Layout.fillWidth: true
            text: root.mode === "create"
                ? "Link a project resource to the selected task and set the starting allocation."
                : "Adjust the active allocation commitment for this task assignment."
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
            text: "Task"
            color: Theme.AppTheme.textPrimary
            font.family: Theme.AppTheme.fontFamily
        }

        AppControls.Label {
            id: taskLabel

            Layout.fillWidth: true
            color: Theme.AppTheme.textPrimary
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.bodySize
            font.bold: true
            wrapMode: Text.WordWrap
        }

        AppControls.Label {
            Layout.fillWidth: true
            visible: root.mode === "create"
            text: "Project resource"
            color: Theme.AppTheme.textPrimary
            font.family: Theme.AppTheme.fontFamily
        }

        AppControls.ComboBox {
            id: resourceCombo

            Layout.fillWidth: true
            visible: root.mode === "create"
            model: root.resourceOptions
            textRole: "label"
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

        AppControls.Label {
            text: "Allocation (%)"
            color: Theme.AppTheme.textPrimary
            font.family: Theme.AppTheme.fontFamily
        }

        AppControls.TextField {
            id: allocationField

            Layout.fillWidth: true
            placeholderText: "0.1 - 100.0"
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

    footer: AppControls.DialogActionFooter {

        Item {
            Layout.fillWidth: true
        }

        AppControls.SecondaryButton {
            objectName: "dialogCancelButton"
            text: "Cancel"
            iconName: "close"
            onClicked: root.close()
        }

        AppControls.PrimaryButton {
            objectName: "dialogSubmitButton"
            text: root.mode === "create" ? "Assign Resource" : "Save Allocation"
            iconName: root.mode === "create" ? "resources" : "save"
            enabled: root.mode !== "create" || (root.resourceOptions || []).length > 0
            onClicked: root.submitDialog()
        }
    }
}


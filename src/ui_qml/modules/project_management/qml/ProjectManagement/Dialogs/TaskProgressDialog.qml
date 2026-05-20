import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme

Dialog {
    id: root

    property var statusOptions: []
    property var taskData: ({})
    readonly property var workflowStatusOptions: (root.statusOptions || []).filter(function(option) {
        return String(option.value || "").toLowerCase() !== "all"
    })

    signal submitted(var payload)

    modal: true
    width: 460
    title: "Update Progress"
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
        percentField.text = String(state.percentComplete || "")
        actualStartField.text = String(state.actualStart || "")
        actualEndField.text = String(state.actualEnd || "")
        statusCombo.currentIndex = root.statusIndexForValue(state.status || "TODO")
    }

    onOpened: root.populateFromTask()

    background: Rectangle {
        radius: Theme.AppTheme.radiusLg
        color: Theme.AppTheme.surfaceRaised
        border.color: Theme.AppTheme.divider
        border.width: 1
    }

    contentItem: ColumnLayout {
        spacing: Theme.AppTheme.spacingMd

        Label {
            Layout.fillWidth: true
            text: root.taskData && root.taskData.title
                ? "Update progress, actual dates, and execution status for " + root.taskData.title + "."
                : "Update progress, actual dates, and execution status for the selected task."
            color: Theme.AppTheme.textSecondary
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.bodySize
            wrapMode: Text.WordWrap
        }

        Label { text: "Progress (%)"; color: Theme.AppTheme.textPrimary; font.family: Theme.AppTheme.fontFamily }
        TextField { id: percentField; Layout.fillWidth: true; placeholderText: "0-100" }

        Label { text: "Status"; color: Theme.AppTheme.textPrimary; font.family: Theme.AppTheme.fontFamily }
        ComboBox {
            id: statusCombo
            Layout.fillWidth: true
            model: root.workflowStatusOptions
            textRole: "label"
        }

        Label { text: "Actual start"; color: Theme.AppTheme.textPrimary; font.family: Theme.AppTheme.fontFamily }
        TextField { id: actualStartField; Layout.fillWidth: true; placeholderText: "YYYY-MM-DD" }

        Label { text: "Actual end"; color: Theme.AppTheme.textPrimary; font.family: Theme.AppTheme.fontFamily }
        TextField { id: actualEndField; Layout.fillWidth: true; placeholderText: "YYYY-MM-DD" }
    }

    footer: RowLayout {
        spacing: Theme.AppTheme.spacingSm

        Item { Layout.fillWidth: true }

        AppControls.SecondaryButton {
            objectName: "dialogCancelButton"
            text: "Cancel"
            iconName: "close"
            onClicked: root.close()
        }

        AppControls.PrimaryButton {
            objectName: "dialogSubmitButton"
            text: "Update Progress"
            iconName: "approve"
            onClicked: {
                var state = root.taskData && root.taskData.state ? root.taskData.state : (root.taskData || {})
                var option = root.workflowStatusOptions[statusCombo.currentIndex] || { "value": "TODO" }
                root.submitted({
                    "taskId": String(state.taskId || ""),
                    "expectedVersion": state.version,
                    "percentComplete": percentField.text,
                    "actualStart": actualStartField.text,
                    "actualEnd": actualEndField.text,
                    "status": String(option.value || "TODO")
                })
            }
        }
    }
}

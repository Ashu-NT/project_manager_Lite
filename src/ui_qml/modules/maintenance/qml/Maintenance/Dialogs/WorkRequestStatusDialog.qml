import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme

AppControls.CenteredDialog {
    id: root

    property var statusOptions: []
    property var workRequestData: ({})
    readonly property var workflowStatusOptions: (root.statusOptions || []).filter(function(option) {
        return String(option.value || "").toLowerCase() !== "all"
    })

    signal submitted(string statusValue)

    modal: true
    width: 420
    title: "Change Work Request Status"
    closePolicy: Popup.CloseOnEscape

    function statusIndexForValue(statusValue) {
        for (let index = 0; index < root.workflowStatusOptions.length; index += 1) {
            if (String(root.workflowStatusOptions[index].value || "") === String(statusValue || "")) {
                return index
            }
        }
        return 0
    }

    function submitDialog() {
        const option = root.workflowStatusOptions[statusCombo.currentIndex] || { "value": "NEW" }
        root.submitted(String(option.value || "NEW"))
    }

    onOpened: {
        const state = root.workRequestData && root.workRequestData.state ? root.workRequestData.state : (root.workRequestData || {})
        statusCombo.currentIndex = root.statusIndexForValue(state.status || "NEW")
    }

    background: Rectangle {
        radius: Theme.AppTheme.radiusLg
        color: Theme.AppTheme.surface
    }

    contentItem: ColumnLayout {
        spacing: Theme.AppTheme.spacingMd

        Label {
            Layout.fillWidth: true
            text: root.workRequestData && root.workRequestData.title
                ? "Update the triage lifecycle state for " + root.workRequestData.title + "."
                : "Update the lifecycle state for the selected work request."
            color: Theme.AppTheme.textSecondary
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.bodySize
            wrapMode: Text.WordWrap
        }

        ComboBox {
            id: statusCombo
            objectName: "statusCombo"

            Layout.fillWidth: true
            model: root.workflowStatusOptions
            textRole: "label"
        }
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
            text: "Update Status"
            iconName: "workflow"
            onClicked: root.submitDialog()
        }
    }
}


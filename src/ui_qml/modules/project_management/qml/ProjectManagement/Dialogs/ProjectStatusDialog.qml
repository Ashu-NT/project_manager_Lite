import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme

Dialog {
    id: root

    property var statusOptions: []
    property var projectData: ({})
    readonly property var workflowStatusOptions: (root.statusOptions || []).filter(function(option) {
        return String(option.value || "").toLowerCase() !== "all"
    })

    signal submitted(string statusValue)

    modal: true
    width: 420
    title: "Change Project Status"
    closePolicy: Popup.CloseOnEscape

    function statusIndexForValue(statusValue) {
        for (let index = 0; index < root.workflowStatusOptions.length; index += 1) {
            if (String(root.workflowStatusOptions[index].value || "") === String(statusValue || "")) {
                return index
            }
        }
        return 0
    }

    onOpened: {
        var state = root.projectData && root.projectData.state ? root.projectData.state : (root.projectData || {})
        statusCombo.currentIndex = root.statusIndexForValue(state.status || "PLANNED")
    }

    background: Rectangle {
        radius: Theme.AppTheme.radiusLg
        color: Theme.AppTheme.surface
        border.color: Theme.AppTheme.border
    }

    contentItem: ColumnLayout {
        spacing: Theme.AppTheme.spacingMd

        Label {
            Layout.fillWidth: true
            text: root.projectData && root.projectData.title
                ? "Update the lifecycle state for " + root.projectData.title + "."
                : "Update the lifecycle state for the selected project."
            color: Theme.AppTheme.textSecondary
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.bodySize
            wrapMode: Text.WordWrap
        }

        ComboBox {
            id: statusCombo

            Layout.fillWidth: true
            model: root.workflowStatusOptions
            textRole: "label"
        }
    }

    footer: RowLayout {
        spacing: Theme.AppTheme.spacingSm

        Item {
            Layout.fillWidth: true
        }

        Button {
            text: "Cancel"
            onClicked: root.close()
        }

        AppControls.PrimaryButton {
            text: "Update Status"
            onClicked: {
                var option = root.workflowStatusOptions[statusCombo.currentIndex] || { "value": "PLANNED" }
                root.submitted(String(option.value || "PLANNED"))
            }
        }
    }
}

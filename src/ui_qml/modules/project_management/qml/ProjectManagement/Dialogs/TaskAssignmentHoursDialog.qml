import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme

Dialog {
    id: root

    property var assignmentData: ({})

    signal submitted(var payload)

    modal: true
    width: 460
    title: "Update Assignment Effort"
    closePolicy: Popup.CloseOnEscape

    function assignmentState() {
        return root.assignmentData && root.assignmentData.state
            ? root.assignmentData.state
            : (root.assignmentData || {})
    }

    onOpened: {
        const state = root.assignmentState()
        hoursField.text = String(state.hoursLogged || "")
    }

    background: Rectangle {
        radius: Theme.AppTheme.radiusLg
        color: Theme.AppTheme.surface
    }

    contentItem: ColumnLayout {
        spacing: Theme.AppTheme.spacingMd

        Label {
            Layout.fillWidth: true
            text: root.assignmentData && root.assignmentData.title
                ? "Set aggregate effort for " + root.assignmentData.title + "."
                : "Set aggregate effort for the selected assignment."
            color: Theme.AppTheme.textSecondary
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.bodySize
            wrapMode: Text.WordWrap
        }

        Label {
            text: "Hours logged"
            color: Theme.AppTheme.textPrimary
            font.family: Theme.AppTheme.fontFamily
        }

        TextField {
            id: hoursField

            Layout.fillWidth: true
            placeholderText: "0.00"
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
            text: "Save Hours"
            iconName: "save"
            onClicked: root.submitted({
                "assignmentId": String(root.assignmentState().assignmentId || ""),
                "hoursLogged": hoursField.text
            })
        }
    }
}

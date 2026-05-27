import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme

AppControls.CenteredDialog {
    id: root

    property var assignmentData: ({})

    signal submitted(var payload)

    modal: true
    width: 460
    title: "Update Assignment Effort"
    closePolicy: Popup.CloseOnEscape
    padding: Theme.AppTheme.marginMd

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
        color: Theme.AppTheme.surfaceRaised
        border.color: Theme.AppTheme.divider
        border.width: 1
    }

    contentItem: ColumnLayout {
        spacing: Theme.AppTheme.spacingMd

        AppControls.Label {
            Layout.fillWidth: true
            text: root.assignmentData && root.assignmentData.title
                ? "Set aggregate effort for " + root.assignmentData.title + "."
                : "Set aggregate effort for the selected assignment."
            color: Theme.AppTheme.textSecondary
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.bodySize
            wrapMode: Text.WordWrap
        }

        AppControls.Label {
            text: "Hours logged"
            color: Theme.AppTheme.textPrimary
            font.family: Theme.AppTheme.fontFamily
        }

        AppControls.TextField {
            id: hoursField

            Layout.fillWidth: true
            placeholderText: "0.00"
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
            text: "Save Hours"
            iconName: "save"
            onClicked: root.submitted({
                "assignmentId": String(root.assignmentState().assignmentId || ""),
                "hoursLogged": hoursField.text
            })
        }
    }
}


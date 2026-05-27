import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Theme 1.0 as Theme

CenteredDialog {
    id: root

    property string message: ""
    property string supportingText: ""
    property string confirmLabel: "Confirm"
    property string confirmIcon: "approve"
    property bool confirmDanger: false
    property bool confirmEnabled: true
    property string cancelLabel: "Cancel"

    signal confirmed()

    modal: true
    width: 420
    padding: Theme.AppTheme.dialogPadding
    closePolicy: Popup.CloseOnEscape

    background: Rectangle {
        radius: Theme.AppTheme.radiusLg
        color: Theme.AppTheme.surfaceRaised
        border.color: Theme.AppTheme.divider
        border.width: 1
    }

    contentItem: ColumnLayout {
        spacing: Theme.AppTheme.spacingSm

        Label {
            Layout.fillWidth: true
            text: root.message
            color: Theme.AppTheme.textPrimary
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.bodySize
            wrapMode: Text.WordWrap
        }

        Label {
            Layout.fillWidth: true
            visible: text.length > 0
            text: root.supportingText
            color: Theme.AppTheme.textSecondary
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.smallSize
            wrapMode: Text.WordWrap
        }
    }

    footer: DialogActionFooter {
        Item {
            Layout.fillWidth: true
        }

        SecondaryButton {
            objectName: "dialogCancelButton"
            text: root.cancelLabel
            iconName: "close"
            onClicked: root.close()
        }

        PrimaryButton {
            objectName: "dialogConfirmButton"
            text: root.confirmLabel
            iconName: root.confirmIcon
            danger: root.confirmDanger
            enabled: root.confirmEnabled
            onClicked: {
                root.confirmed()
                root.close()
            }
        }
    }
}

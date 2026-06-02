pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

AppWidgets.AnchoredPopup {
    id: root

    signal clearFiltersRequested()

    width: 280
    modal: false
    focus: true
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
    padding: Theme.AppTheme.dialogPadding

    background: Rectangle {
        radius: Theme.AppTheme.radiusMd
        color: Theme.AppTheme.dialogBackground
        border.color: Theme.AppTheme.dialogBorder
        border.width: 1
    }

    ColumnLayout {
        width: parent.width
        spacing: Theme.AppTheme.spacingMd

        AppControls.Label {
            Layout.fillWidth: true
            text: "Active Filters"
            color: Theme.AppTheme.textPrimary
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.smallSize
            font.bold: true
        }

        AppControls.Label {
            Layout.fillWidth: true
            text: "Use the collaboration context toolbar to change project, team, period, and unread scope for all panels."
            color: Theme.AppTheme.textSecondary
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.smallSize
            wrapMode: Text.WordWrap
        }

        AppControls.SecondaryButton {
            text: "Clear Filters"
            iconName: "close"
            onClicked: {
                root.clearFiltersRequested()
                root.close()
            }
        }

        AppControls.PrimaryButton {
            text: "Apply View"
            iconName: "approve"
            onClicked: root.close()
        }
    }
}

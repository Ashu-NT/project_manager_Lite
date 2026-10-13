pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Icons 1.0 as AppIcons
import App.Theme 1.0 as Theme

// [<]   October 2026   [>]   [Today] -- pure navigation chrome, no date
// math beyond formatting the already-resolved `monthLabel` for display.
Item {
    id: root

    property string monthLabel: ""
    property bool busy: false

    signal previousRequested()
    signal nextRequested()
    signal todayRequested()

    implicitHeight: Math.max(previousButton.implicitHeight, 36)

    RowLayout {
        anchors.fill: parent
        spacing: Theme.AppTheme.spacingSm

        Rectangle {
            id: previousButton
            Layout.preferredWidth: 36
            Layout.preferredHeight: 36
            radius: Theme.AppTheme.radiusSm
            color: _prevHover.containsMouse ? Theme.AppTheme.hoverSurface : "transparent"
            border.color: Theme.AppTheme.subtleBorder
            border.width: 1

            activeFocusOnTab: true
            Accessible.role: Accessible.Button
            Accessible.name: "Previous month"
            Accessible.onPressAction: root.previousRequested()
            Keys.onPressed: (event) => {
                if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter || event.key === Qt.Key_Space) {
                    root.previousRequested()
                    event.accepted = true
                }
            }

            AppIcons.AppIcon {
                anchors.centerIn: parent
                name: "chevron_left"
                size: Theme.AppTheme.iconSm
                iconColor: Theme.AppTheme.textSecondary
            }

            MouseArea {
                id: _prevHover
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: root.previousRequested()
            }
        }

        AppControls.Label {
            Layout.preferredWidth: 160
            horizontalAlignment: Text.AlignHCenter
            text: root.monthLabel
            color: Theme.AppTheme.textPrimary
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.bodySize
            font.bold: true
        }

        Rectangle {
            Layout.preferredWidth: 36
            Layout.preferredHeight: 36
            radius: Theme.AppTheme.radiusSm
            color: _nextHover.containsMouse ? Theme.AppTheme.hoverSurface : "transparent"
            border.color: Theme.AppTheme.subtleBorder
            border.width: 1

            activeFocusOnTab: true
            Accessible.role: Accessible.Button
            Accessible.name: "Next month"
            Accessible.onPressAction: root.nextRequested()
            Keys.onPressed: (event) => {
                if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter || event.key === Qt.Key_Space) {
                    root.nextRequested()
                    event.accepted = true
                }
            }

            AppIcons.AppIcon {
                anchors.centerIn: parent
                name: "chevron_right"
                size: Theme.AppTheme.iconSm
                iconColor: Theme.AppTheme.textSecondary
            }

            MouseArea {
                id: _nextHover
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: root.nextRequested()
            }
        }

        AppControls.SecondaryButton {
            text: "Today"
            iconName: "calendar"
            enabled: !root.busy
            onClicked: root.todayRequested()
        }

        Item { Layout.fillWidth: true }
    }
}

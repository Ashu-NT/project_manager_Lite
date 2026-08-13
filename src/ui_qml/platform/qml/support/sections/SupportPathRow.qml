pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Icons 1.0 as AppIcons
import App.Theme 1.0 as Theme

Rectangle {
    id: root
    property string rowLabel: ""
    property string rowValue: ""
    property bool   canOpen:  false

    signal openRequested()

    Layout.fillWidth: true
    Layout.preferredHeight: 36
    color: "transparent"

    Rectangle {
        anchors { bottom: parent.bottom; left: parent.left; right: parent.right }
        height: 1; color: Theme.AppTheme.divider
    }

    RowLayout {
        anchors.fill:        parent
        anchors.leftMargin:  Theme.AppTheme.marginMd
        anchors.rightMargin: Theme.AppTheme.marginSm
        spacing:             Theme.AppTheme.spacingXs

        AppControls.Label {
            text:              root.rowLabel
            color:             Theme.AppTheme.textMuted
            font.family:       Theme.AppTheme.fontFamily
            font.pixelSize:    Theme.AppTheme.captionSize
            font.bold:         true
            Layout.preferredWidth: 160
        }
        AppControls.Label {
            Layout.fillWidth: true
            text:           root.rowValue.length > 0 ? root.rowValue : "-"
            color:          Theme.AppTheme.textSecondary
            font.family:    Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.captionSize
            elide:          Text.ElideMiddle
        }
        Rectangle {
            visible: root.canOpen
            Layout.preferredWidth: 22; Layout.preferredHeight: 22
            radius: Theme.AppTheme.radiusMd
            color:  _openMA.containsMouse ? Theme.AppTheme.hoverSurface : "transparent"

            AppIcons.AppIcon { anchors.centerIn: parent; name: "view"; size: 10; iconColor: Theme.AppTheme.textMuted }

            MouseArea {
                id: _openMA
                anchors.fill: parent
                hoverEnabled: true
                cursorShape:  Qt.PointingHandCursor
                onClicked:    root.openRequested()
            }
        }
    }
}

pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import App.Icons 1.0 as AppIcons
import App.Theme 1.0 as Theme

// Shell-header notification bell. Badge shows the exact unread count from
// NotificationsController.unreadCount (itself sourced from
// PlatformNotificationDesktopApi.count_my_unread(), never a capped list
// length) and is hidden entirely when there are zero unread notifications.
Rectangle {
    id: root

    // Shell.Controllers.NotificationsController
    property var controller: null

    signal activated()

    readonly property int _unreadCount: root.controller ? (root.controller.unreadCount || 0) : 0

    function _activate() {
        root.forceActiveFocus()
        root.activated()
    }

    implicitWidth: Theme.AppTheme.inputHeight
    implicitHeight: Theme.AppTheme.inputHeight
    radius: Theme.AppTheme.radiusSm
    color: (bellHover.containsMouse || root.activeFocus)
        ? Theme.AppTheme.hoverSurface
        : Theme.AppTheme.surfaceOverlay
    border.width: root.activeFocus ? 2 : 0
    border.color: Theme.AppTheme.focusBorder

    Behavior on color { ColorAnimation { duration: 100 } }

    // -- Keyboard / accessibility -------------------------------------
    activeFocusOnTab: true
    Accessible.role: Accessible.Button
    Accessible.name: root._unreadCount > 0
        ? ("Notifications, " + root._unreadCount + " unread")
        : "Notifications"
    Accessible.onPressAction: root._activate()

    Keys.onPressed: (event) => {
        if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter || event.key === Qt.Key_Space) {
            root._activate()
            event.accepted = true
        }
    }

    AppIcons.AppIcon {
        anchors.centerIn: parent
        name: "notifications"
        size: Theme.AppTheme.headerIconSize
        iconColor: Theme.AppTheme.textMuted
    }

    Rectangle {
        visible: root._unreadCount > 0
        anchors.top: parent.top
        anchors.right: parent.right
        anchors.margins: 2
        radius: height / 2
        height: 16
        width: Math.max(16, _badgeLabel.implicitWidth + 8)
        color: Theme.AppTheme.danger

        Text {
            id: _badgeLabel
            anchors.centerIn: parent
            text: root._unreadCount > 99 ? "99+" : String(root._unreadCount)
            color: "white"
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Math.max(9, Theme.AppTheme.captionSize - 1)
            font.bold: true
        }
    }

    MouseArea {
        id: bellHover
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: root._activate()
    }

    ToolTip {
        visible: bellHover.containsMouse
        text: "Notifications"
        delay: 400
    }
}

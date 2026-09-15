pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Theme 1.0 as Theme
import App.Widgets 1.0 as AppWidgets
import App.Controls 1.0 as AppControls

// Notification drawer. NotificationDto carries no route/source information,
// so rows are never presented as navigable -- only readable, with a
// keyboard-accessible "Mark read" action for unread rows.
AppWidgets.SlideOverPanel {
    id: root

    // Shell.Controllers.NotificationsController
    property var controller: null

    title: "Notifications"

    readonly property var _notifications: root.controller ? (root.controller.notifications || []) : []
    readonly property bool _isLoading: root.controller ? root.controller.isLoading === true : false
    readonly property string _errorMessage: root.controller ? (root.controller.errorMessage || "") : ""
    readonly property int _unreadCount: root.controller ? (root.controller.unreadCount || 0) : 0

    onOpenChanged: {
        if (root.open && root.controller) {
            root.controller.refresh()
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.AppTheme.marginMd
        spacing: Theme.AppTheme.spacingSm

        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.AppTheme.spacingSm

            AppControls.Label {
                Layout.fillWidth: true
                text: root._unreadCount > 0 ? (root._unreadCount + " unread") : "All caught up"
                color: Theme.AppTheme.textMuted
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.smallSize
            }

            AppControls.SecondaryButton {
                text: "Mark all read"
                visible: root._unreadCount > 0
                onClicked: {
                    if (root.controller) {
                        root.controller.markAllRead()
                    }
                }
            }
        }

        AppWidgets.LoadingOverlay {
            Layout.fillWidth: true
            compact: true
            loading: root._isLoading
            message: "Loading notifications…"
        }

        AppWidgets.InlineMessage {
            Layout.fillWidth: true
            tone: "danger"
            message: root._errorMessage
        }

        AppWidgets.EmptyState {
            Layout.fillWidth: true
            Layout.topMargin: Theme.AppTheme.spacingLg
            visible: !root._isLoading && root._errorMessage.length === 0 && root._notifications.length === 0
            title: "No notifications"
            message: "You're up to date."
        }

        ListView {
            id: _list
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: !root._isLoading && root._errorMessage.length === 0 && root._notifications.length > 0
            clip: true
            model: root._notifications
            spacing: Theme.AppTheme.spacingXs
            ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

            delegate: Rectangle {
                id: _row
                required property var modelData

                width: _list.width
                implicitHeight: _rowLayout.implicitHeight + Theme.AppTheme.spacingSm * 2
                radius: Theme.AppTheme.radiusMd
                color: _row.modelData.isRead ? "transparent" : Theme.AppTheme.infoSoft
                border.width: 1
                border.color: Theme.AppTheme.subtleBorder

                ColumnLayout {
                    id: _rowLayout
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: Theme.AppTheme.spacingSm
                    spacing: 2

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Theme.AppTheme.spacingXs

                        Rectangle {
                            visible: !_row.modelData.isRead
                            Layout.preferredWidth: 7
                            Layout.preferredHeight: 7
                            radius: 4
                            color: Theme.AppTheme.accent
                        }

                        AppControls.Label {
                            Layout.fillWidth: true
                            text: String(_row.modelData.title || "")
                            color: Theme.AppTheme.textPrimary
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.smallSize
                            font.bold: !_row.modelData.isRead
                            wrapMode: Text.WordWrap
                        }
                    }

                    AppControls.Label {
                        Layout.fillWidth: true
                        visible: String(_row.modelData.body || "").length > 0
                        text: String(_row.modelData.body || "")
                        color: Theme.AppTheme.textSecondary
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.captionSize
                        wrapMode: Text.WordWrap
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Theme.AppTheme.spacingXs

                        AppControls.Label {
                            Layout.fillWidth: true
                            text: String(_row.modelData.timestampLabel || "")
                            color: Theme.AppTheme.textMuted
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.captionSize
                        }

                        // Keyboard-accessible "Mark read" action -- a real
                        // focusable/activatable button, not clickable text.
                        Rectangle {
                            id: _markReadAction
                            visible: !_row.modelData.isRead
                            implicitWidth: _markReadLabel.implicitWidth + Theme.AppTheme.spacingSm * 2
                            implicitHeight: Theme.AppTheme.captionSize + 12
                            radius: Theme.AppTheme.radiusSm
                            color: (_markReadHover.containsMouse || _markReadAction.activeFocus)
                                ? Theme.AppTheme.hoverSurface
                                : "transparent"
                            border.width: _markReadAction.activeFocus ? 2 : 0
                            border.color: Theme.AppTheme.focusBorder

                            activeFocusOnTab: true
                            Accessible.role: Accessible.Button
                            Accessible.name: "Mark read: " + String(_row.modelData.title || "")
                            Accessible.onPressAction: _markReadAction._activate()

                            function _activate() {
                                if (root.controller) {
                                    root.controller.markRead(String(_row.modelData.id || ""))
                                }
                            }

                            Keys.onPressed: (event) => {
                                if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter || event.key === Qt.Key_Space) {
                                    _markReadAction._activate()
                                    event.accepted = true
                                }
                            }

                            AppControls.Label {
                                id: _markReadLabel
                                anchors.centerIn: parent
                                text: "Mark read"
                                color: Theme.AppTheme.accent
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.captionSize
                                font.bold: true
                            }

                            MouseArea {
                                id: _markReadHover
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: {
                                    _markReadAction.forceActiveFocus()
                                    _markReadAction._activate()
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls as QQC2
import App.Theme 1.0 as Theme

QQC2.ToolButton {
    id: root

    property string message: ""
    property string title: "Information"
    property string accessibleLabel: "More information"
    property int toolTipDelay: 350
    property int maximumToolTipWidth: 308
    property bool expanded: false

    readonly property bool hasMessage: root.message.trim().length > 0
    readonly property real _messageTextWidth: Math.min(
        Math.max(180, root.maximumToolTipWidth - 58),
        Math.max(150, messageMetrics.advanceWidth)
    )

    visible: root.hasMessage
    enabled: root.hasMessage
    hoverEnabled: true
    focusPolicy: Qt.StrongFocus
    implicitWidth: 24
    implicitHeight: 24

    Accessible.name: root.accessibleLabel
    Accessible.description: root.message

    contentItem: Item {
        Rectangle {
            anchors.centerIn: parent
            width: 14
            height: 14
            radius: 7
            color: root.hovered || root.activeFocus
                ? Theme.AppTheme.accentSoft
                : "transparent"
            border.width: 1
            border.color: root.hovered || root.activeFocus
                ? Theme.AppTheme.accent
                : Theme.AppTheme.textMuted

            Text {
                anchors.centerIn: parent
                text: "i"
                color: root.hovered || root.activeFocus
                    ? Theme.AppTheme.accent
                    : Theme.AppTheme.textSecondary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Math.max(9, Theme.AppTheme.captionSize - 1)
                font.bold: true
                verticalAlignment: Text.AlignVCenter
                horizontalAlignment: Text.AlignHCenter
            }
        }
    }

    background: Rectangle {
        radius: root.implicitWidth / 2
        color: root.down
            ? Theme.AppTheme.hoverSurface
            : root.hovered
                ? Theme.AppTheme.accentSoft
                : "transparent"
        border.width: root.activeFocus ? 1 : 0
        border.color: Theme.AppTheme.focusBorder
    }

    onClicked: {
        root.expanded = !root.expanded
        if (root.expanded) root.forceActiveFocus()
    }
    onActiveFocusChanged: {
        if (!root.activeFocus && !root.hovered) root.expanded = false
    }
    onVisibleChanged: {
        if (!root.visible) root.expanded = false
    }

    TextMetrics {
        id: messageMetrics
        text: root.message
        font.family: Theme.AppTheme.fontFamily
        font.pixelSize: Theme.AppTheme.smallSize
    }

    QQC2.ToolTip {
        id: toolTip
        objectName: "infoTipPopup"
        parent: root
        visible: root.hasMessage
            && (root.hovered || root.activeFocus || root.expanded)
        text: root.message
        delay: root.activeFocus ? 0 : root.toolTipDelay
        timeout: 10000
        padding: 0

        contentItem: Item {
            implicitWidth: 58 + root._messageTextWidth
            implicitHeight: Math.max(54, tipCopy.implicitHeight + 20)

            Rectangle {
                id: tipBadge
                anchors.left: parent.left
                anchors.leftMargin: 14
                anchors.verticalCenter: parent.verticalCenter
                width: 22
                height: 22
                radius: 11
                color: Theme.AppTheme.accentSoft

                Text {
                    anchors.centerIn: parent
                    text: "i"
                    color: Theme.AppTheme.accent
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.captionSize
                    font.bold: true
                }
            }

            Column {
                id: tipCopy
                anchors.left: tipBadge.right
                anchors.leftMargin: 10
                anchors.right: parent.right
                anchors.rightMargin: 12
                anchors.verticalCenter: parent.verticalCenter
                spacing: 3

                Text {
                    width: parent.width
                    text: root.title
                    color: Theme.AppTheme.textPrimary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.captionSize
                    font.bold: true
                    elide: Text.ElideRight
                }

                Text {
                    width: parent.width
                    text: root.message
                    color: Theme.AppTheme.textSecondary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                    wrapMode: Text.WordWrap
                }
            }
        }

        background: Item {
            Rectangle {
                anchors.fill: parent
                anchors.topMargin: 3
                radius: Theme.AppTheme.radiusMd
                color: Theme.AppTheme.elevationMediumShadow
                opacity: 0.55
            }

            Rectangle {
                anchors.fill: parent
                radius: Theme.AppTheme.radiusMd
                color: Theme.AppTheme.surfaceRaised
                border.width: 1
                border.color: Theme.AppTheme.subtleBorder
            }

            Rectangle {
                anchors.left: parent.left
                anchors.top: parent.top
                anchors.bottom: parent.bottom
                anchors.topMargin: 7
                anchors.bottomMargin: 7
                width: 3
                radius: 1.5
                color: Theme.AppTheme.accent
            }
        }
    }
}

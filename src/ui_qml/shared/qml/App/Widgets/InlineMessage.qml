import QtQuick
import QtQuick.Controls
import App.Theme 1.0 as Theme
import App.Controls 1.0 as AppControls

Rectangle {
    id: root

    property string message: ""
    property string tone: "info"  // info | success | warning | danger
    property string actionLabel: ""   // optional inline action button label ("Retry", "Dismiss", etc.)

    signal actionClicked()

    readonly property color toneColor: {
        switch (root.tone) {
            case "success": return Theme.AppTheme.success
            case "warning": return Theme.AppTheme.warning
            case "danger": return Theme.AppTheme.error
            default: return Theme.AppTheme.info
        }
    }

    readonly property color toneSurface: {
        switch (root.tone) {
            case "success": return Theme.AppTheme.successSoft
            case "warning": return Theme.AppTheme.warningSoft
            case "danger": return Theme.AppTheme.dangerSoft
            default: return Theme.AppTheme.infoSoft
        }
    }

    visible: root.message.length > 0
    implicitHeight: visible ? Math.max(msgLabel.implicitHeight, _actionBtn.implicitHeight) + Theme.AppTheme.spacingSm * 2 : 0
    radius: Theme.AppTheme.radiusSm
    color: root.toneSurface

    Rectangle {
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        width: 3
        radius: 2
        color: root.toneColor
    }

    AppControls.Label {
        id: msgLabel
        anchors.left: parent.left
        anchors.right: _actionBtn.visible ? _actionBtn.left : parent.right
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        anchors.leftMargin: Theme.AppTheme.spacingSm + 6
        anchors.rightMargin: Theme.AppTheme.spacingSm
        anchors.topMargin: Theme.AppTheme.spacingSm
        anchors.bottomMargin: Theme.AppTheme.spacingSm
        text: root.message
        color: root.toneColor
        font.family: Theme.AppTheme.fontFamily
        font.pixelSize: Theme.AppTheme.smallSize
        wrapMode: Text.WordWrap
    }

    // Optional inline action (e.g. "Retry")
    Rectangle {
        id: _actionBtn
        anchors.right: parent.right
        anchors.rightMargin: Theme.AppTheme.spacingSm
        anchors.verticalCenter: parent.verticalCenter
        visible: root.actionLabel.length > 0
        implicitWidth: _actionLbl.implicitWidth + 14
        implicitHeight: Theme.AppTheme.captionSize + 8
        radius: Theme.AppTheme.radiusSm
        color: _actionHover.containsMouse ? Qt.darker(root.toneColor, 1.1) : root.toneColor

        AppControls.Label {
            id: _actionLbl
            anchors.centerIn: parent
            text: root.actionLabel
            color: "white"
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.captionSize
            font.bold: true
        }

        MouseArea {
            id: _actionHover
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: root.actionClicked()
        }
    }
}

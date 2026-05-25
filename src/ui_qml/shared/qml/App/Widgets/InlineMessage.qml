import QtQuick
import QtQuick.Controls
import App.Theme 1.0 as Theme
import App.Controls 1.0 as AppControls

Rectangle {
    id: root

    property string message: ""
    property string tone: "info"  // info | success | warning | danger

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
    implicitHeight: visible ? msgLabel.implicitHeight + Theme.AppTheme.spacingSm * 2 : 0
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
        anchors.right: parent.right
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
}


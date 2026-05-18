import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Theme 1.0 as Theme

Rectangle {
    id: root

    property string message: ""
    property string tone: "info"  // info | success | warning | danger

    visible: root.message.length > 0
    implicitHeight: visible ? msgLabel.implicitHeight + Theme.AppTheme.spacingSm * 2 : 0
    radius: Theme.AppTheme.radiusSm

    color: {
        switch (root.tone) {
            case "success": return Theme.AppTheme.successSoft
            case "warning": return Theme.AppTheme.warningSoft
            case "danger":  return Theme.AppTheme.dangerSoft
            default:        return Theme.AppTheme.infoSoft
        }
    }

    border.color: {
        switch (root.tone) {
            case "success": return Theme.AppTheme.success
            case "warning": return Theme.AppTheme.warning
            case "danger":  return Theme.AppTheme.danger
            default:        return Theme.AppTheme.accent
        }
    }
    border.width: 1

    Label {
        id: msgLabel
        anchors.fill: parent
        anchors.margins: Theme.AppTheme.spacingSm
        text: root.message
        color: {
            switch (root.tone) {
                case "success": return Theme.AppTheme.success
                case "warning": return Theme.AppTheme.warning
                case "danger":  return Theme.AppTheme.danger
                default:        return Theme.AppTheme.accent
            }
        }
        font.family: Theme.AppTheme.fontFamily
        font.pixelSize: Theme.AppTheme.smallSize
        wrapMode: Text.WordWrap
    }
}

import QtQuick
import QtQuick.Controls
import App.Theme 1.0 as Theme
import App.Controls 1.0 as AppControls

Rectangle {
    id: chip

    property string status: ""
    // Caller-supplied semantic tone -- "neutral" | "info" | "success" |
    // "warning" | "danger". StatusChip is domain-neutral: it never infers
    // meaning from `status` text, which is display text only. The caller
    // owns the mapping from its own business/domain status to a semantic
    // tone; an unrecognized or empty tone fails safe to "neutral".
    property string tone: "neutral"

    readonly property var _validTones: ["neutral", "info", "success", "warning", "danger"]

    implicitHeight: 22
    implicitWidth: chipLabel.implicitWidth + 16
    radius: implicitHeight / 2

    readonly property var _variant: chip._validTones.indexOf(chip.tone) >= 0 ? chip.tone : "neutral"

    color: {
        switch (chip._variant) {
            case "success": return Theme.AppTheme.successSoft
            case "info":    return Theme.AppTheme.infoSoft
            case "warning": return Theme.AppTheme.warningSoft
            case "danger":  return Theme.AppTheme.dangerSoft
            default:        return Theme.AppTheme.surfaceAlt
        }
    }

    border.color: {
        switch (chip._variant) {
            case "success": return Theme.AppTheme.success
            case "info":    return Theme.AppTheme.info
            case "warning": return Theme.AppTheme.warning
            case "danger":  return Theme.AppTheme.error
            default:        return Theme.AppTheme.borderStrong
        }
    }
    border.width: 1

    AppControls.Label {
        id: chipLabel
        anchors.centerIn: parent
        text: chip.status
        color: {
            switch (chip._variant) {
                case "success": return Theme.AppTheme.success
                case "info":    return Theme.AppTheme.info
                case "warning": return Theme.AppTheme.warning
                case "danger":  return Theme.AppTheme.error
                default:        return Theme.AppTheme.textSecondary
            }
        }
        font.family: Theme.AppTheme.fontFamily
        font.pixelSize: Theme.AppTheme.captionSize
        font.bold: true
    }
}

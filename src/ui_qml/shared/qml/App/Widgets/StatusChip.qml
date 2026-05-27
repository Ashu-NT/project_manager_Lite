import QtQuick
import QtQuick.Controls
import App.Theme 1.0 as Theme
import App.Controls 1.0 as AppControls

Rectangle {
    id: chip

    property string status: ""

    implicitHeight: 22
    implicitWidth: chipLabel.implicitWidth + 16
    radius: implicitHeight / 2

    readonly property string _normalized: status.toLowerCase().replace(/\s+/g, "_").replace(/-/g, "_")

    readonly property var _variant: {
        const s = chip._normalized
        if (s === "active" || s === "approved" || s === "closed" || s === "completed"
                || s === "verified" || s === "issued" || s === "fully_received")
            return "success"
        if (s === "progress" || s === "in_progress" || s === "pending" || s === "submitted"
                || s === "planned" || s === "scheduled" || s === "released"
                || s === "partial" || s === "partially_received" || s === "sent")
            return "info"
        if (s === "waiting" || s === "blocked" || s === "paused" || s === "deferred"
                || s === "on_hold")
            return "warning"
        if (s === "rejected" || s === "cancelled" || s === "overdue" || s === "failed"
                || s === "error" || s === "expired" || s === "danger")
            return "danger"
        return "neutral"
    }

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

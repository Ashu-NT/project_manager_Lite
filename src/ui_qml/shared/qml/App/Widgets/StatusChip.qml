import QtQuick
import QtQuick.Controls
import App.Theme 1.0 as Theme
import App.Controls 1.0 as AppControls

Rectangle {
    id: chip

    property string status: ""
    // Explicit caller-supplied semantic tone -- "neutral" | "info" |
    // "success" | "warning" | "danger". When set, this is used verbatim and
    // `status` is display text only (no classification happens). This is
    // the preferred way for new/future-module callers to use this
    // component: StatusChip must not grow a new hardcoded business-status
    // string for every module (Inventory, Procurement, Accounting, Payroll,
    // QHSE, HR, ...); the caller already knows what a status means and
    // should say so directly.
    property string tone: ""

    readonly property var _validTones: ["neutral", "info", "success", "warning", "danger"]

    implicitHeight: 22
    implicitWidth: chipLabel.implicitWidth + 16
    radius: implicitHeight / 2

    readonly property string _normalized: status.toLowerCase().replace(/\s+/g, "_").replace(/-/g, "_")

    // LEGACY auto-classification -- kept only for existing Platform/PM
    // callers that don't pass an explicit tone yet, so none of them
    // visually regress. Do not add new status strings here; give the new
    // caller an explicit `tone` instead.
    readonly property var _legacyVariant: {
        const s = chip._normalized
        if (s === "active" || s === "approved" || s === "closed" || s === "completed"
                || s === "verified" || s === "issued" || s === "fully_received" || s === "accepted"
                || s === "within_capacity" || s === "available" || s === "flexible")
            return "success"
        if (s === "progress" || s === "in_progress" || s === "pending" || s === "submitted"
                || s === "planned" || s === "scheduled" || s === "released"
                || s === "partial" || s === "partially_received" || s === "sent"
                || s === "low")
            return "info"
        if (s === "waiting" || s === "blocked" || s === "paused" || s === "deferred"
                || s === "on_hold" || s === "medium" || s === "near_capacity")
            return "warning"
        if (s === "rejected" || s === "cancelled" || s === "overdue" || s === "failed"
                || s === "error" || s === "expired" || s === "danger" || s === "high"
                || s === "critical" || s === "declined" || s === "over_capacity"
                || s === "infeasible")
            return "danger"
        return "neutral"
    }

    readonly property var _variant: {
        if (chip.tone.length > 0) {
            return chip._validTones.indexOf(chip.tone) >= 0 ? chip.tone : "neutral"
        }
        return chip._legacyVariant
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

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Theme 1.0 as Theme
import App.Controls 1.0 as AppControls

// ─────────────────────────────────────────────────────────────────────────────
// LoadingOverlay  —  enterprise-grade loading feedback component
//
// Modes:
//   modal: true,  compact: false  →  full scrim overlay (original behavior)
//   modal: false, compact: false  →  centered spinner + message, no scrim
//   compact: true                 →  inline row: small spinner + message text
//
// Backward compatible: existing usages that set `loading` and `anchors.fill`
// continue to work as before.
//
// Usage (full overlay):
//   AppWidgets.LoadingOverlay { anchors.fill: parent; loading: controller.isLoading }
//
// Usage (full overlay with message):
//   AppWidgets.LoadingOverlay {
//       anchors.fill: parent
//       loading: controller.isLoading
//       message: "Loading resources..."
//   }
//
// Usage (compact inline — for lazy-loaded sections):
//   AppWidgets.LoadingOverlay {
//       Layout.fillWidth: true
//       loading: isLoading
//       compact: true
//       message: "Loading tasks..."
//   }
// ─────────────────────────────────────────────────────────────────────────────

Item {
    id: root

    // ── Public API ─────────────────────────────────────────────────────────────
    property bool   loading:        false
    property string message:        ""
    property bool   compact:        false   // true → inline row; false → centered overlay
    property bool   modal:          true    // true → scrim background (non-compact only)

    // ── Visibility ─────────────────────────────────────────────────────────────
    visible: root.loading

    // ── Sizing ─────────────────────────────────────────────────────────────────
    // Compact: driven by content so it fits cleanly in ColumnLayout / Column.
    // Full:    caller is responsible for sizing (typically anchors.fill: parent).
    implicitWidth:  root.compact ? _row.implicitWidth  + Theme.AppTheme.spacingMd * 2 : 0
    implicitHeight: root.compact ? _row.implicitHeight + Theme.AppTheme.spacingMd     : 0

    // ── Scrim (modal, non-compact only) ────────────────────────────────────────
    Rectangle {
        anchors.fill: parent
        color: Theme.AppTheme.overlayScrim
        visible: root.modal && !root.compact
        // Ensures overlay blocks interaction in the same z-order
        z: 0
    }

    // ── Content: spinner + optional message ────────────────────────────────────
    Row {
        id: _row
        z: 1

        // Compact → left-aligned with margin; full → centered in parent
        anchors.left:             root.compact ? parent.left             : undefined
        anchors.leftMargin:       root.compact ? Theme.AppTheme.marginMd : 0
        anchors.verticalCenter:   root.compact ? parent.verticalCenter   : undefined
        anchors.horizontalCenter: root.compact ? undefined               : parent.horizontalCenter
        anchors.centerIn:         root.compact ? undefined               : parent

        spacing: Theme.AppTheme.spacingSm

        BusyIndicator {
            id: _spinner
            anchors.verticalCenter: parent.verticalCenter
            running:       root.loading
            // Compact → icon-sized; full → prominent
            implicitWidth:  root.compact ? Theme.AppTheme.iconLg          : Theme.AppTheme.normalRowHeight
            implicitHeight: root.compact ? Theme.AppTheme.iconLg          : Theme.AppTheme.normalRowHeight
        }

        AppControls.Label {
            visible:            root.message.length > 0
            anchors.verticalCenter: parent.verticalCenter
            text:               root.message
            color:              root.compact
                ? Theme.AppTheme.textMuted
                : Theme.AppTheme.textSecondary
            font.family:        Theme.AppTheme.fontFamily
            font.pixelSize:     root.compact
                ? Theme.AppTheme.smallSize
                : Theme.AppTheme.bodySize
            wrapMode:           Text.NoWrap
        }
    }
}

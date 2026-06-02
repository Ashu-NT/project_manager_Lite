pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme

// ─────────────────────────────────────────────────────────────────────────────
// FormField — reusable "persistent label + field + helper/error" form row.
//
// The standard wrapper for a single labelled input inside any dialog/form. It
// renders, top-to-bottom:
//   • a persistent visible label (+ a consistent required indicator)
//   • the input control(s) you nest as default children
//   • a helper line (caption) OR a danger InlineMessage when errorText is set
//
// Placeholders stay on the nested control as short example text — they are NOT
// the label. Uses only shared controls + Theme tokens, so it is safe inside any
// ColumnLayout-based EntityDialog form body.
//
//   AppWidgets.FormField {
//       Layout.fillWidth: true
//       label: "Project Name"
//       required: true
//       helperText: "Shown on dashboards and reports."
//       errorText: root.fieldErrors.projectName || ""
//
//       AppControls.TextField {
//           Layout.fillWidth: true
//           text: root.form.projectName
//           placeholderText: "e.g. Refinery Upgrade"
//           onTextEdited: root.form.projectName = text
//       }
//   }
// ─────────────────────────────────────────────────────────────────────────────

ColumnLayout {
    id: root

    // Nested input control(s) land in the content holder below the label.
    default property alias content: _contentHolder.data

    property string label:           ""
    property string placeholderText: ""   // convenience passthrough (reference via id)
    property string helperText:      ""
    property string errorText:       ""
    property bool   required:        false

    spacing: Theme.AppTheme.spacingXs

    // ── Label (+ required indicator) ─────────────────────────────────────────
    RowLayout {
        Layout.fillWidth: true
        spacing: Math.round(Theme.AppTheme.spacingXs / 2)
        visible: root.label.length > 0

        AppControls.Label {
            text:           root.label
            color:          root.enabled ? Theme.AppTheme.textSecondary : Theme.AppTheme.textMuted
            font.family:    Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.smallSize
            font.bold:      true
        }

        AppControls.Label {
            visible:        root.required
            text:           "*"
            color:          Theme.AppTheme.error
            font.family:    Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.smallSize
            font.bold:      true
        }

        Item { Layout.fillWidth: true }
    }

    // ── Field content slot ───────────────────────────────────────────────────
    ColumnLayout {
        id: _contentHolder
        Layout.fillWidth: true
        spacing: Theme.AppTheme.spacingXs
    }

    // ── Error (danger) takes priority over helper text ───────────────────────
    InlineMessage {
        Layout.fillWidth: true
        visible: root.errorText.length > 0
        tone:    "danger"
        message: root.errorText
    }

    AppControls.Label {
        Layout.fillWidth: true
        visible:        root.errorText.length === 0 && root.helperText.length > 0
        text:           root.helperText
        color:          Theme.AppTheme.textMuted
        font.family:    Theme.AppTheme.fontFamily
        font.pixelSize: Theme.AppTheme.captionSize
        wrapMode:       Text.WordWrap
    }
}

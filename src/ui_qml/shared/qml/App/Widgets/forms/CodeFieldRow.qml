pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme

// ─────────────────────────────────────────────────────────────────────────────
// CodeFieldRow — labelled code input with an optional "Generate" action.
//
// A reusable form row for entity codes (project/client/item/asset/document …).
// Uses only shared controls + Theme tokens; safe inside any ColumnLayout form.
//
//   AppWidgets.CodeFieldRow {
//       Layout.fillWidth: true
//       label: "Project Code"
//       value: root.form.projectCode
//       placeholderText: "Auto-generated if empty"
//       required: true
//       generateVisible: true
//       busy: root.workspaceController ? root.workspaceController.isBusy : false
//       onValueEdited: function(v) { root.form.projectCode = v }
//       onGenerateRequested: root.form.projectCode =
//           root.workspaceController.generateProjectCode(root.form)
//   }
// ─────────────────────────────────────────────────────────────────────────────

ColumnLayout {
    id: root

    property string label: ""
    property string value: ""
    property string placeholderText: ""
    property bool   required: false
    property string helperText: ""
    property string errorText: ""
    property bool   generateVisible: false
    property bool   generateEnabled: true
    property bool   busy: false

    signal valueEdited(string value)
    signal generateRequested()

    spacing: Theme.AppTheme.spacingXs

    // ── Label (+ required indicator) ─────────────────────────────────────────
    RowLayout {
        Layout.fillWidth: true
        spacing: Theme.AppTheme.spacingXs / 2
        visible: root.label.length > 0

        AppControls.Label {
            text:           root.label
            color:          Theme.AppTheme.textPrimary
            font.family:    Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.bodySize
            font.bold:      true
        }

        AppControls.Label {
            visible:        root.required
            text:           "*"
            color:          Theme.AppTheme.error
            font.family:    Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.bodySize
            font.bold:      true
        }

        Item { Layout.fillWidth: true }
    }

    // ── Field + Generate ─────────────────────────────────────────────────────
    RowLayout {
        Layout.fillWidth: true
        spacing: Theme.AppTheme.spacingSm

        AppControls.TextField {
            id: codeField
            Layout.fillWidth: true
            placeholderText: root.placeholderText
            enabled: !root.busy
            onTextEdited: root.valueEdited(text)
            Component.onCompleted: text = root.value
        }

        AppControls.SecondaryButton {
            visible:   root.generateVisible
            text:      "Generate"
            iconName:  "refresh"
            enabled:   root.generateEnabled && !root.busy
            onClicked: root.generateRequested()
        }
    }

    // Push external value changes (e.g. after Generate) into the field without
    // clobbering what the user is typing, and without a two-way binding loop.
    Connections {
        target: root
        function onValueChanged() {
            if (codeField.text !== root.value) {
                codeField.text = root.value
            }
        }
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

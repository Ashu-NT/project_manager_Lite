pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme

// ─────────────────────────────────────────────────────────────────────────────
// EntityDialog — enterprise dialog shell
//
// Extends CenteredDialog with:
//   • Subtitle line below the title
//   • InlineMessage areas for error / feedback / info
//   • Scrollable form content via default property injection
//   • Standardised footer: [Destructive] ←spacer→ [spinner] [Cancel] [Primary]
//   • Busy state disables all buttons
//
// Usage:
//   AppWidgets.EntityDialog {
//       title:        "Edit Project"
//       subtitle:     "Update lifecycle and ownership"
//       errorMessage: root.validationMessage
//       primaryText:  "Save Changes"
//       primaryIcon:  "save"
//       onAccepted:   root.submitDialog()
//       onRejected:   root.close()
//
//       GridLayout { ... }   // form fields go here
//   }
// ─────────────────────────────────────────────────────────────────────────────

AppControls.CenteredDialog {
    id: root

    // ── Content ───────────────────────────────────────────────────────────────
    default property alias content: _formArea.data

    // ── Header ────────────────────────────────────────────────────────────────
    property string subtitle: ""

    // ── Messages (priority: error > feedback > info) ──────────────────────────
    property string errorMessage:    ""
    property string feedbackMessage: ""
    property string infoMessage:     ""

    // ── Busy ──────────────────────────────────────────────────────────────────
    property bool busy: false

    // ── Primary action ────────────────────────────────────────────────────────
    property string primaryText:    "Save"
    property string primaryIcon:    "save"
    property bool   primaryEnabled: true
    property bool   showPrimary:    true

    // ── Secondary (Cancel) ────────────────────────────────────────────────────
    property string secondaryText: "Cancel"
    property string secondaryIcon: "close"
    property bool   showSecondary: true

    // ── Destructive action ────────────────────────────────────────────────────
    property string destructiveText:    ""
    property string destructiveIcon:    "delete"
    property bool   showDestructive:    false
    property bool   destructiveEnabled: true

    // ── Signals ───────────────────────────────────────────────────────────────
    signal accepted()
    signal rejected()
    signal destructiveRequested()

    // ── Sizing ────────────────────────────────────────────────────────────────
    modal: true
    focus: true
    closePolicy: Popup.CloseOnEscape
    width:  Theme.AppTheme.dialogFormWidth   // 640 — dialogs may override
    height: Math.min(
        parent ? parent.height - Theme.AppTheme.dialogPadding * 2 : 760,
        760
    )

    // ── Content item ──────────────────────────────────────────────────────────
    contentItem: ColumnLayout {
        id: _shell
        spacing: 0

        // Subtitle
        AppControls.Label {
            Layout.fillWidth: true
            Layout.leftMargin:  Theme.AppTheme.dialogPadding
            Layout.rightMargin: Theme.AppTheme.dialogPadding
            Layout.topMargin:   Theme.AppTheme.spacingSm
            visible: root.subtitle.length > 0
            text:    root.subtitle
            color:   Theme.AppTheme.textSecondary
            font.family:    Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.bodySize
            wrapMode: Text.WordWrap
        }

        // Message area — only one visible at a time (priority: error > feedback > info)
        InlineMessage {
            Layout.fillWidth: true
            Layout.leftMargin:  Theme.AppTheme.dialogPadding
            Layout.rightMargin: Theme.AppTheme.dialogPadding
            Layout.topMargin:   Theme.AppTheme.spacingSm
            visible: root.errorMessage.length > 0
            message: root.errorMessage
            tone:    "danger"
        }

        InlineMessage {
            Layout.fillWidth: true
            Layout.leftMargin:  Theme.AppTheme.dialogPadding
            Layout.rightMargin: Theme.AppTheme.dialogPadding
            Layout.topMargin:   Theme.AppTheme.spacingSm
            visible: root.feedbackMessage.length > 0 && root.errorMessage.length === 0
            message: root.feedbackMessage
            tone:    "success"
        }

        InlineMessage {
            Layout.fillWidth: true
            Layout.leftMargin:  Theme.AppTheme.dialogPadding
            Layout.rightMargin: Theme.AppTheme.dialogPadding
            Layout.topMargin:   Theme.AppTheme.spacingSm
            visible: root.infoMessage.length > 0
                && root.errorMessage.length === 0
                && root.feedbackMessage.length === 0
            message: root.infoMessage
            tone:    "info"
        }

        // Scrollable form area
        Flickable {
            Layout.fillWidth:  true
            Layout.fillHeight: true
            Layout.topMargin:  Theme.AppTheme.spacingSm

            contentWidth:  availableWidth
            contentHeight: _formArea.implicitHeight
            clip: true

            // Vertical scrollbar
            ScrollBar.vertical: ScrollBar {
                policy: ScrollBar.AsNeeded
            }

            // Form content injection target
            ColumnLayout {
                id: _formArea
                width:   parent.width
                spacing: Theme.AppTheme.spacingMd

                // Padding inside scrollable area
                Item { Layout.preferredHeight: Theme.AppTheme.spacingXs }

                // content items go here via default property alias

                Item { Layout.preferredHeight: Theme.AppTheme.spacingXs }
            }
        }
    }

    // ── Footer ────────────────────────────────────────────────────────────────
    footer: AppControls.DialogActionFooter {

        // Destructive action (left-aligned, separated)
        AppControls.SecondaryButton {
            visible: root.showDestructive && root.destructiveText.length > 0
            text:     root.destructiveText
            iconName: root.destructiveIcon
            danger:   true
            enabled:  root.destructiveEnabled && !root.busy
            onClicked: root.destructiveRequested()
        }

        Item { Layout.fillWidth: true }

        // Busy spinner
        BusyIndicator {
            visible: root.busy
            running: root.busy
            implicitWidth:  20
            implicitHeight: 20
        }

        // Cancel
        AppControls.SecondaryButton {
            visible:  root.showSecondary
            text:     root.secondaryText
            iconName: root.secondaryIcon
            enabled:  !root.busy
            onClicked: root.rejected()
        }

        // Primary
        AppControls.PrimaryButton {
            visible:  root.showPrimary
            text:     root.primaryText
            iconName: root.primaryIcon
            enabled:  root.primaryEnabled && !root.busy
            onClicked: root.accepted()
        }
    }
}

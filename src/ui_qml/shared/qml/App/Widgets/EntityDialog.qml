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
// Submit contract:
//   The Primary button calls root.submitDialog() if the dialog defines one,
//   otherwise it falls back to accept(). submitDialog() should VALIDATE first:
//   on failure set root.errorMessage and return (the dialog stays OPEN); on
//   success emit a payload signal (e.g. submitted) — the host then closes the
//   dialog only after the controller reports success (see DialogHost
//   _handleResult). This is why submit does NOT auto-close: validation and
//   backend errors must remain visible inside the open dialog.
//
// Usage:
//   AppWidgets.EntityDialog {
//       title:        "Edit Project"
//       subtitle:     "Update lifecycle and ownership"
//       errorMessage: root.validationMessage
//       primaryText:  "Save Changes"
//       primaryIcon:  "save"
//       function submitDialog() {            // validate → emit; do NOT close
//           if (!valid) { errorMessage = "..."; return }
//           submitted(buildPayload())
//       }
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
    // accepted() and rejected() are inherited from Dialog — do NOT redeclare them.
    // Buttons call root.accept() / root.reject() which emit those built-in signals.
    signal destructiveRequested()

    // ── Sizing ────────────────────────────────────────────────────────────────
    // Height is CONTENT-DRIVEN, never fixed:
    //   • small/medium dialogs shrink to fit their content (implicitHeight)
    //   • the dialog is capped to the available window height (availableHeight)
    //   • when content exceeds the cap, the form body Flickable scrolls while
    //     the header (title/subtitle) and footer (buttons) stay pinned.
    // Dialogs should NOT override `height`; override `width` only if needed.
    modal: true
    focus: true
    closePolicy: Popup.CloseOnEscape
    width:  Theme.AppTheme.dialogFormWidth   // 640 — dialogs may override

    // Largest height the dialog may occupy: window height minus top+bottom margin.
    readonly property real maxDialogHeight:
        (parent ? parent.height : 760) - Theme.AppTheme.dialogPadding * 2

    // Natural height = content body + pinned header/footer + paddings. Capped to
    // the window so the dialog is never cut off; when capped, the body scrolls.
    height: Math.min(
        _shell.implicitHeight
            + implicitHeaderHeight + implicitFooterHeight
            + topPadding + bottomPadding
            + spacing * 2,
        maxDialogHeight
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

        // Scrollable form area.
        //   • Layout.preferredHeight = natural content height → feeds the dialog's
        //     implicitHeight so it can shrink to content when there is room.
        //   • Layout.fillHeight lets the body shrink below that when the dialog is
        //     capped to maxDialogHeight, at which point the Flickable scrolls.
        Flickable {
            Layout.fillWidth:  true
            Layout.fillHeight: true
            Layout.preferredHeight: _formArea.implicitHeight
            Layout.topMargin:  Theme.AppTheme.spacingSm

            contentWidth:  root.availableWidth
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
            objectName: "dialogCancelButton"
            visible:  root.showSecondary
            text:     root.secondaryText
            iconName: root.secondaryIcon
            enabled:  !root.busy
            onClicked: root.reject()
        }

        // Primary
        AppControls.PrimaryButton {
            objectName: "dialogSubmitButton"
            visible:  root.showPrimary
            text:     root.primaryText
            iconName: root.primaryIcon
            enabled:  root.primaryEnabled && !root.busy
            // If the dialog defines submitDialog(), call it directly so it can
            // validate and keep the dialog OPEN on failure (closing is then
            // owned by the host's _handleResult on success). Dialogs without a
            // submitDialog() fall back to accept() → onAccepted (legacy path).
            onClicked: {
                if (typeof root.submitDialog === "function")
                    root.submitDialog()
                else
                    root.accept()
            }
        }
    }
}

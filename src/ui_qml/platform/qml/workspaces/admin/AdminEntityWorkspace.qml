import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Icons 1.0 as AppIcons
import App.Theme 1.0 as Theme

// Reusable admin entity workspace: section toolbar + ContextualActionToolbar + DataTable.
// Drop in one instance per admin section (organizations, sites, employees, etc.).
// Wire up signals to the page-level dialog host and controller slots.
ColumnLayout {
    id: root
    spacing: 0

    // ── Public API ────────────────────────────────────────────────
    property string sectionTitle:         ""
    property string entityLabel:          ""   // used in "New <entityLabel>" button
    property var    catalog:              ({ items: [], emptyState: "No records" })
    property var    columns:              []
    property bool   isBusy:               false
    property bool   isLoading:            false
    property string errorMessage:         ""
    property string feedbackMessage:      ""
    property string selectedRowId:        ""
    property string selectedRowTitle:     ""

    // Toolbar action labels — set to "" to hide the button
    property string primaryActionLabel:   "Edit"
    property string secondaryActionLabel: ""
    property string tertiaryActionLabel:  ""
    property string primaryActionIcon:    "edit"
    property string secondaryActionIcon:  "approve"
    property string tertiaryActionIcon:   "add"
    property bool   primaryActionDanger:  false
    property bool   secondaryActionDanger: false
    property bool   tertiaryActionDanger: false

    signal createRequested()
    signal primaryActionRequested(string itemId)
    signal secondaryActionRequested(string itemId)
    signal tertiaryActionRequested(string itemId)
    signal rowSelected(string rowId)
    signal rowActivated(string rowId)
    signal refreshRequested()

    // ── Computed actions for ContextualActionToolbar ──────────────
    readonly property var _contextActions: {
        const sel = root.selectedRowId.length > 0
        const result = []
        if (root.primaryActionLabel.length > 0)
            result.push({ id: "primary",   label: root.primaryActionLabel,   icon: root.primaryActionIcon,   enabled: sel, danger: root.primaryActionDanger   })
        if (root.secondaryActionLabel.length > 0)
            result.push({ id: "secondary", label: root.secondaryActionLabel, icon: root.secondaryActionIcon, enabled: sel, danger: root.secondaryActionDanger })
        if (root.tertiaryActionLabel.length > 0)
            result.push({ id: "tertiary",  label: root.tertiaryActionLabel,  icon: root.tertiaryActionIcon,  enabled: sel, danger: root.tertiaryActionDanger  })
        return result
    }

    // ── Section header toolbar ────────────────────────────────────
    Rectangle {
        Layout.fillWidth: true
        height: Theme.AppTheme.toolbarHeight - 6
        color:  Theme.AppTheme.surfaceRaised
        z:      1

        Rectangle {
            anchors { bottom: parent.bottom; left: parent.left; right: parent.right }
            height: 1; color: Theme.AppTheme.divider
        }

        RowLayout {
            anchors.fill:           parent
            anchors.leftMargin:     Theme.AppTheme.marginMd
            anchors.rightMargin:    8
            spacing:                Theme.AppTheme.spacingXs

            Label {
                text:           root.sectionTitle
                color:          Theme.AppTheme.textPrimary
                font.family:    Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.smallSize
                font.bold:      true
            }

            Label {
                visible:        (root.catalog.items || []).length > 0
                text:           String((root.catalog.items || []).length)
                color:          Theme.AppTheme.textMuted
                font.family:    Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.captionSize
                leftPadding:    4
            }

            Item { Layout.fillWidth: true }

            Rectangle {
                visible: root.entityLabel.length > 0
                width: 1; height: 14
                color: Theme.AppTheme.divider
            }

            AppControls.PrimaryButton {
                visible:  root.entityLabel.length > 0
                text:     "New " + root.entityLabel
                iconName: "add"
                enabled:  !root.isBusy
                onClicked: root.createRequested()
            }

            Rectangle {
                width: 26; height: 26; radius: 4
                color: _refreshMA.containsMouse ? Theme.AppTheme.hoverSurface : "transparent"

                AppIcons.AppIcon {
                    anchors.centerIn: parent
                    name: "refresh"; size: 12
                    iconColor: Theme.AppTheme.textMuted
                }

                MouseArea {
                    id: _refreshMA
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape:  Qt.PointingHandCursor
                    enabled:      !root.isBusy
                    onClicked:    root.refreshRequested()
                }
            }
        }
    }

    // ── Contextual action toolbar — visible when a row is selected ─
    AppWidgets.ContextualActionToolbar {
        Layout.fillWidth: true
        visible:  root.selectedRowId.length > 0
        title:    root.selectedRowTitle.length > 0 ? root.selectedRowTitle : root.selectedRowId
        busy:     root.isBusy
        actions:  root._contextActions
        onActionTriggered: function(id) {
            if      (id === "primary")   root.primaryActionRequested(root.selectedRowId)
            else if (id === "secondary") root.secondaryActionRequested(root.selectedRowId)
            else if (id === "tertiary")  root.tertiaryActionRequested(root.selectedRowId)
        }
    }

    // ── Inline state banners ──────────────────────────────────────
    AppWidgets.InlineMessage {
        Layout.fillWidth: true
        visible: (root.isLoading || root.isBusy) && root.errorMessage.length === 0
        tone:    "info"
        message: root.isBusy ? "Saving changes..." : "Loading..."
    }

    AppWidgets.InlineMessage {
        Layout.fillWidth: true
        visible: root.errorMessage.length > 0
        tone:    "danger"
        message: root.errorMessage
    }

    AppWidgets.InlineMessage {
        Layout.fillWidth: true
        visible: root.feedbackMessage.length > 0 && root.errorMessage.length === 0
        tone:    "success"
        message: root.feedbackMessage
    }

    // ── Data table ────────────────────────────────────────────────
    AppWidgets.DataTable {
        Layout.fillWidth:  true
        Layout.fillHeight: true

        rows:          root.catalog.items || []
        columns:       root.columns
        emptyText:     root.catalog.emptyState || "No records"
        loading:       root.isLoading
        selectedRowId: root.selectedRowId

        onRowSelected:  function(rowId) { root.rowSelected(rowId)  }
        onRowActivated: function(rowId) { root.rowActivated(rowId) }
    }
}

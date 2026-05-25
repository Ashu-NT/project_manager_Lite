import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

// Reusable admin entity workspace: section title bar + TableToolbar + DataTable.
// All selected-record business actions live exclusively in the right detail panel.
ColumnLayout {
    id: root
    spacing: 0

    // ── Public API ────────────────────────────────────────────────
    property string sectionTitle:    ""
    property string entityLabel:     ""
    property var    catalog:         ({ items: [], emptyState: "No records" })
    property var    columns:         []
    property bool   isBusy:          false
    property bool   isLoading:       false
    property string errorMessage:    ""
    property string feedbackMessage: ""
    property string selectedRowId:   ""

    signal createRequested()
    signal rowSelected(string rowId)
    signal rowActivated(string rowId)
    signal refreshRequested()

    // ── Section title bar ─────────────────────────────────────────
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
            anchors.fill:        parent
            anchors.leftMargin:  Theme.AppTheme.marginMd
            anchors.rightMargin: 8
            spacing:             Theme.AppTheme.spacingXs

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
        }
    }

    // ── Table toolbar (always visible) ────────────────────────────
    AppWidgets.TableToolbar {
        id: _tableToolbar
        Layout.fillWidth: true
        showCreate:    root.entityLabel.length > 0
        createLabel:   "New " + root.entityLabel
        showRefresh:   true
        showCustomize: root.columns.length > 0
        isBusy:        root.isBusy
        onCreateRequested:  root.createRequested()
        onRefreshRequested: root.refreshRequested()
        onCustomizeClicked: _dataTable.openColumnCustomizer(_tableToolbar.customizeButtonItem)
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
        id: _dataTable
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

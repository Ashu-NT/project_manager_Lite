import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import App.Controls 1.0 as AppControls

// Reusable admin entity workspace: section title bar + TableToolbar + DataTable.
// All selected-record business actions live exclusively in the right detail panel.
ColumnLayout {
    id: root
    spacing: 0

    property string sectionTitle:    ""
    property string entityLabel:     ""
    property var    catalog:         ({ items: [], emptyState: "No records" })
    property var    columns:         []
    property bool   isBusy:          false
    property bool   isLoading:       false
    property string errorMessage:    ""
    property string feedbackMessage: ""
    property string selectedRowId:   ""
    // Python-owned DynamicTableModel that DataTable binds to directly.
    property var    catalogModel:    null

    signal createRequested()
    signal rowSelected(string rowId)
    signal rowActivated(string rowId)
    signal refreshRequested()

    readonly property int _totalCount: root.catalogModel
        ? root.catalogModel.rowCountValue
        : (root.catalog.items || []).length

    Rectangle {
        Layout.fillWidth: true
        height: Theme.AppTheme.toolbarHeight - 6
        color: Theme.AppTheme.surfaceRaised
        z: 1

        Rectangle {
            anchors.bottom: parent.bottom
            anchors.left: parent.left
            anchors.right: parent.right
            height: 1
            color: Theme.AppTheme.divider
        }

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: Theme.AppTheme.marginMd
            anchors.rightMargin: 8
            spacing: Theme.AppTheme.spacingXs

            AppControls.Label {
                text: root.sectionTitle
                color: Theme.AppTheme.textPrimary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.smallSize
                font.bold: true
            }

            AppControls.Label {
                visible: root._totalCount > 0
                text: String(root._totalCount)
                color: Theme.AppTheme.textMuted
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.captionSize
                leftPadding: 4
            }

            Item { Layout.fillWidth: true }
        }
    }

    AppWidgets.TableToolbar {
        id: _tableToolbar
        Layout.fillWidth: true
        showCreate: root.entityLabel.length > 0
        createLabel: "New " + root.entityLabel
        showRefresh: true
        showCustomize: root.columns.length > 0
        isBusy: root.isBusy
        onCreateRequested: root.createRequested()
        onRefreshRequested: root.refreshRequested()
        onCustomizeClicked: _dataTable.openColumnCustomizer(_tableToolbar.customizeButtonItem)
    }

    AppWidgets.InlineMessage {
        Layout.fillWidth: true
        visible: (root.isLoading || root.isBusy) && root.errorMessage.length === 0
        tone: "info"
        message: root.isBusy ? "Saving changes..." : "Loading..."
    }

    AppWidgets.InlineMessage {
        Layout.fillWidth: true
        visible: root.errorMessage.length > 0 && root._totalCount > 0
        tone: "danger"
        message: root.errorMessage
    }

    AppWidgets.InlineMessage {
        Layout.fillWidth: true
        visible: root.feedbackMessage.length > 0 && root.errorMessage.length === 0
        tone: "success"
        message: root.feedbackMessage
    }

    AppWidgets.DataTable {
        id: _dataTable
        Layout.fillWidth: true
        Layout.fillHeight: true
        visible: !(root.errorMessage.length > 0 && root._totalCount === 0)

        sourceModel: root.catalogModel
        columns: root.columns
        emptyText: root.catalog.emptyState || "No records"
        loading: root.isLoading
        selectedRowId: root.selectedRowId

        onRowSelected: function(rowId) { root.rowSelected(rowId) }
        onRowActivated: function(rowId) { root.rowActivated(rowId) }
    }

    // R6.5: friendlier fallback than the raw danger banner when the
    // underlying data call fails and leaves nothing to show.
    AppWidgets.PermissionState {
        Layout.fillWidth: true
        Layout.fillHeight: true
        visible: root.errorMessage.length > 0 && root._totalCount === 0
        message: root.errorMessage
    }
}

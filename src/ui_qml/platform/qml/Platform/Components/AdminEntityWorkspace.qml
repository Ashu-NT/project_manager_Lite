import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import App.Controls 1.0 as AppControls

// Reusable admin entity workspace: section title bar + TableToolbar +
// DataTable, with an opt-in fixed-footer pagination region matching the
// canonical master-data list pattern (see TablePaginationBar consumers
// under Project Management, e.g. ProjectsListPage.qml). All selected-record
// business actions live exclusively in the right detail panel.
ColumnLayout {
    id: root
    spacing: 0

    property string sectionTitle:    ""
    property string entityLabel:     ""
    // RBAC: whether the current session may create a new record here.
    // Defaults true so callers that don't opt in keep today's behavior.
    property bool   canCreate:       true
    // `catalog` may optionally carry server-side pagination metadata
    // (paginated/page/pageSize/totalCount/filteredTotal/noResultsState) --
    // see PlatformWorkspaceActionListViewModel. Callers that don't
    // populate those fields keep today's non-paginated behavior exactly.
    property var    catalog:         ({ items: [], emptyState: "No records" })
    property var    columns:         []
    property bool   isBusy:          false
    property bool   isLoading:       false
    property string errorMessage:    ""
    property string feedbackMessage: ""
    property string selectedRowId:   ""
    // Python-owned DynamicTableModel that DataTable binds to directly.
    property var    catalogModel:    null

    // Search is opt-in (showSearch) since not every entity page has wired
    // server-side search yet; searchText is caller-owned input state.
    property bool   showSearch:      false
    property string searchText:      ""
    property var    pageSizeOptions: [25, 50, 100]

    signal createRequested()
    signal rowSelected(string rowId)
    signal rowActivated(string rowId)
    signal refreshRequested()
    signal searchChanged(string text)
    signal pageRequested(int page)
    signal pageSizeRequested(int pageSize)
    signal clearFiltersRequested()

    readonly property bool _paginated: root.catalog.paginated === true
    readonly property int _totalCount: root._paginated
        ? (root.catalog.totalCount || 0)
        : (root.catalogModel ? root.catalogModel.rowCountValue : (root.catalog.items || []).length)
    readonly property int _filteredTotal: root._paginated
        ? (root.catalog.filteredTotal || 0)
        : root._totalCount

    // True empty (nothing in the dataset at all) vs. a search/filter that
    // matched nothing -- two different UX states, never conflated.
    readonly property bool _isTrueEmpty: root._paginated
        && root._totalCount === 0
        && !root.isLoading
    readonly property bool _isNoResults: root._paginated
        && root._totalCount > 0
        && root._filteredTotal === 0
        && !root.isLoading

    readonly property string _emptyText: root._isNoResults
        ? (root.catalog.noResultsState || "No records match your current filters.")
        : (root.catalog.emptyState || "No records")
    readonly property string _emptyActionLabel: {
        if (root._isNoResults) return "Clear filters"
        if (root._isTrueEmpty && root.canCreate && root.entityLabel.length > 0) return "Create " + root.entityLabel
        return ""
    }

    function _onEmptyActionRequested() {
        if (root._isNoResults) {
            root.clearFiltersRequested()
        } else {
            root.createRequested()
        }
    }

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
        showSearch: root.showSearch
        searchText: root.searchText
        searchPlaceholder: "Search " + (root.sectionTitle || root.entityLabel).toLowerCase() + "..."
        showCreate: root.entityLabel.length > 0 && root.canCreate
        createLabel: "New " + root.entityLabel
        showRefresh: true
        showCustomize: root.columns.length > 0
        isBusy: root.isBusy
        onSearchChanged: function(text) { root.searchChanged(text) }
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

    // ── Table region: fixed pagination footer, scrollable table body ────
    // Mirrors the canonical master-data list layout (DataTable anchored
    // top..paginationBar.top, TablePaginationBar anchored to parent.bottom)
    // so pagination never moves immediately after the last row and never
    // jumps as the row count changes.
    Item {
        Layout.fillWidth: true
        Layout.fillHeight: true
        visible: !(root.errorMessage.length > 0 && root._totalCount === 0)

        AppWidgets.DataTable {
            id: _dataTable
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: root._paginated ? _paginationBar.top : parent.bottom

            sourceModel: root.catalogModel
            columns: root.columns
            emptyText: root._emptyText
            emptyActionLabel: root._emptyActionLabel
            loading: root.isLoading
            selectedRowId: root.selectedRowId

            onRowSelected: function(rowId) { root.rowSelected(rowId) }
            onRowActivated: function(rowId) { root.rowActivated(rowId) }
            onEmptyActionRequested: root._onEmptyActionRequested()
        }

        AppWidgets.TablePaginationBar {
            id: _paginationBar
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            visible: root._paginated
            currentPage: root.catalog.page || 1
            pageSize: root.catalog.pageSize || 25
            totalItems: root._filteredTotal
            pageSizeOptions: root.pageSizeOptions
            busy: root.isBusy || root.isLoading

            onPageRequested: function(page) { root.pageRequested(page) }
            onPageSizeRequested: function(pageSize) { root.pageSizeRequested(pageSize) }
        }
    }

    AppWidgets.PermissionState {
        Layout.fillWidth: true
        Layout.fillHeight: true
        visible: root.errorMessage.length > 0 && root._totalCount === 0
        message: root.errorMessage
    }
}

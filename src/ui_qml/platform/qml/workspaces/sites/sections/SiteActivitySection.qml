pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

// Site Detail's Activity tab: this site's own paginated, searchable
// business-activity history (create/update/activate/deactivate/archive) --
// distinct from the tenant-wide Platform audit trail (Platform > Control >
// Audit), which the previous "Audit" stub tab pointed to. Renders with the
// canonical App.Widgets.ActivityFeed; this file owns no activity-domain
// knowledge of its own -- every title/actor/subject/tone/icon is
// presenter-supplied (see PlatformSiteActivityPresenter). No entity-type
// filter here (unlike Organization's Activity tab) -- every row is always
// this one site's own history.
Item {
    id: root

    property var catalog: ({
        "items": [], "page": 1, "pageSize": 25, "totalCount": 0, "filteredTotal": 0,
        "emptyState": "", "noResultsState": ""
    })
    property bool busy: false
    property string searchText: ""
    property var dateFilterOptions: []
    property string dateFilter: ""

    signal refreshRequested()
    signal searchChanged(string text)
    signal dateFilterRequested(string value)
    signal pageRequested(int page)
    signal pageSizeRequested(int pageSize)

    readonly property int _readableWidth: 1000
    readonly property bool _hasActiveFilter: root.searchText.trim().length > 0 || root.dateFilter.length > 0
    readonly property var _items: root.catalog.items || []
    readonly property string _emptyText: root._hasActiveFilter
        ? String(root.catalog.noResultsState || "No activity matches your current filters.")
        : String(root.catalog.emptyState || "No activity yet. Business activity for this site will appear here.")

    ColumnLayout {
        anchors.fill: parent
        spacing: Theme.AppTheme.spacingSm

        AppWidgets.TableToolbar {
            Layout.fillWidth: true
            showSearch: true
            showRefresh: true
            showCreate: false
            showImport: false
            showExport: false
            showFilter: false
            showCustomize: false
            showViews: false
            searchPlaceholder: "Search activity..."
            searchText: root.searchText
            isBusy: root.busy

            AppControls.ComboBox {
                Layout.preferredWidth: 150
                model: root.dateFilterOptions
                textRole: "label"
                valueRole: "value"
                currentIndex: {
                    for (let i = 0; i < root.dateFilterOptions.length; i += 1) {
                        if (root.dateFilterOptions[i].value === root.dateFilter) return i
                    }
                    return 0
                }
                onActivated: root.dateFilterRequested(String(currentValue || ""))
            }

            onSearchChanged: function(text) { root.searchChanged(text) }
            onRefreshRequested: root.refreshRequested()
        }

        Flickable {
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            contentWidth: width
            contentHeight: _feed.implicitHeight
            boundsBehavior: Flickable.StopAtBounds

            AppWidgets.ActivityFeed {
                id: _feed
                width: Math.min(parent.width, root._readableWidth)
                anchors.horizontalCenter: parent.horizontalCenter
                items: root._items
                emptyText: root._emptyText
            }

            ScrollBar.vertical: ScrollBar {
                policy: ScrollBar.AsNeeded
            }
        }

        AppWidgets.TablePaginationBar {
            Layout.fillWidth: true
            visible: root.catalog.filteredTotal > 0
            currentPage: root.catalog.page || 1
            pageSize: root.catalog.pageSize || 25
            totalItems: root.catalog.filteredTotal || 0
            busy: root.busy
            pageSizeOptions: [25, 50, 100]

            onPageRequested: function(page) { root.pageRequested(page) }
            onPageSizeRequested: function(pageSize) { root.pageSizeRequested(pageSize) }
        }
    }
}

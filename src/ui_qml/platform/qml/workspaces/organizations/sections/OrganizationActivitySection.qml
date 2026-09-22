pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

// Organization Detail's full Activity tab: a paginated, searchable,
// filterable business-activity workspace for this organization -- distinct
// from the tenant-wide Platform audit trail (Platform > Control > Audit)
// and from Overview's small, bounded "Recent Activity" preview (still a
// separate, unpaginated call -- see AdminOrganizationDetailPage.qml).
// Renders with the canonical App.Widgets.ActivityFeed; this file owns no
// activity-domain knowledge of its own -- every title/description/actor/
// subject/tone/icon is presenter-supplied. All state (catalog/page/search/
// filters) is owned by the orchestrator; this section is presentational
// and emits signals for every user action.
//
// Layout: fills the page's actual available viewport (set by the
// orchestrator, same Math.max(420, contentViewportHeight) pattern as
// Sites/Departments/Employees/Documents) -- a content-driven height here
// previously left dead space below the pagination footer on tall
// viewports. The toolbar and pagination bar are pinned to the top/bottom
// of that space and span its full width; only the feed itself scrolls
// internally, capped to a readable width and centered, so it doesn't
// stretch edge-to-edge on a wide monitor while search/filters/pagination
// still use the full row.
Item {
    id: root

    property var catalog: ({
        "items": [], "page": 1, "pageSize": 25, "totalCount": 0, "filteredTotal": 0,
        "emptyState": "", "noResultsState": ""
    })
    property bool busy: false
    property string searchText: ""
    property var typeFilterOptions: []
    property string typeFilter: ""
    property var dateFilterOptions: []
    property string dateFilter: ""

    signal refreshRequested()
    signal searchChanged(string text)
    signal typeFilterRequested(string value)
    signal dateFilterRequested(string value)
    signal pageRequested(int page)
    signal pageSizeRequested(int pageSize)
    signal itemActivated(var item)

    // A readable feed width even on a very wide monitor -- an activity
    // timeline stays scannable at ~1000px; no shared readable-content-width
    // token exists yet in App.Theme, so this stays a local constant scoped
    // to this one file rather than inventing a new global one.
    readonly property int _readableWidth: 1000
    readonly property bool _hasActiveFilter: root.searchText.trim().length > 0
        || root.typeFilter.length > 0 || root.dateFilter.length > 0
    readonly property var _items: root.catalog.items || []
    readonly property string _emptyText: root._hasActiveFilter
        ? String(root.catalog.noResultsState || "No activity matches your current filters.")
        : String(root.catalog.emptyState || "No activity yet. Business activity related to this organization will appear here.")

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
                model: root.typeFilterOptions
                textRole: "label"
                valueRole: "value"
                currentIndex: {
                    for (let i = 0; i < root.typeFilterOptions.length; i += 1) {
                        if (root.typeFilterOptions[i].value === root.typeFilter) return i
                    }
                    return 0
                }
                onActivated: root.typeFilterRequested(String(currentValue || ""))
            }

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
                onItemActivated: function(item) { root.itemActivated(item) }
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

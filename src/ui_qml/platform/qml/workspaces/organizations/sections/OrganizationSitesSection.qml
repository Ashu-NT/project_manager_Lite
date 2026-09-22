pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Models 1.0 as AppModels
import Platform.Components 1.0 as PlatformComponents
import workspaces.sites 1.0 as SitesWorkspace

// Organization Detail's Sites tab: a real, tenant-scoped management
// workspace (a tenant-scoped backend read, not a client-side filter of the
// global session-active-organization catalog -- see Phase K report). Row
// activation opens the same AdminSiteDetailPage the standalone Sites
// workspace uses. All state (catalog/page/search/filter/selection) is
// owned by the orchestrator (AdminOrganizationDetailPage.qml); this
// section is presentational and emits signals for every user action.
Item {
    id: root

    property var platformCatalog: null
    property var workspaceController: null
    property bool canWrite: true
    property bool busy: false
    property string errorMessage: ""
    property string feedbackMessage: ""
    property real viewportHeight: 420

    property var catalog: ({ "items": [] })
    property var columns: []
    property bool canCreate: false
    property string selectedRowId: ""
    property string searchText: ""
    property var statusFilterOptions: []
    property string statusFilter: ""
    property bool detailOpen: false
    property var selectedSite: null

    signal createRequested()
    signal rowSelected(string id)
    signal rowActivated(string id)
    signal refreshRequested()
    signal searchChanged(string text)
    signal pageRequested(int page)
    signal pageSizeRequested(int pageSize)
    signal clearFiltersRequested()
    signal statusFilterRequested(string value)
    signal detailBackRequested()
    signal detailActionRequested(string actionId)

    width: parent ? parent.width : 0
    height: root.viewportHeight

    AppModels.DynamicTableModel {
        id: _tableModel
        rows: root.catalog.items || []
    }

    PlatformComponents.AdminEntityWorkspace {
        id: _workspace
        anchors.fill: parent
        visible: !root.detailOpen
        sectionTitle: "Sites"
        entityLabel: "Site"
        catalog: root.catalog
        catalogModel: _tableModel
        tableId: "organization.detail.sites.table"
        columns: root.columns
        canCreate: root.canCreate
        isBusy: root.busy
        isLoading: false
        errorMessage: root.errorMessage
        feedbackMessage: root.feedbackMessage
        selectedRowId: root.selectedRowId
        showSearch: true
        searchText: root.searchText
        pageSizeOptions: [25, 50, 100]

        AppControls.ComboBox {
            id: _statusFilterCombo
            Layout.preferredWidth: 150
            model: root.statusFilterOptions
            textRole: "label"
            valueRole: "value"
            currentIndex: {
                for (let i = 0; i < root.statusFilterOptions.length; i += 1) {
                    if (root.statusFilterOptions[i].value === root.statusFilter) return i
                }
                return 0
            }
            onActivated: root.statusFilterChanged(String(currentValue || ""))
        }

        onCreateRequested: root.createRequested()
        onRowSelected: function(id) { root.rowSelected(id) }
        onRowActivated: function(id) { root.rowActivated(id) }
        onRefreshRequested: root.refreshRequested()
        onSearchChanged: function(text) { root.searchChanged(text) }
        onPageRequested: function(page) { root.pageRequested(page) }
        onPageSizeRequested: function(pageSize) { root.pageSizeRequested(pageSize) }
        onClearFiltersRequested: root.clearFiltersRequested()
    }

    Loader {
        anchors.fill: parent
        active: root.detailOpen
        visible: active
        asynchronous: true

        sourceComponent: Component {
            SitesWorkspace.AdminSiteDetailPage {
                platformCatalog: root.platformCatalog
                site: root.selectedSite || ({})
                departmentCatalog: root.workspaceController
                    ? root.workspaceController.departments
                    : ({ "items": [] })
                employeeCatalog: root.workspaceController
                    ? root.workspaceController.employees
                    : ({ "items": [] })
                canWrite: root.canWrite
                busy: root.busy
                errorMessage: root.errorMessage
                feedbackMessage: root.feedbackMessage

                onBackRequested: root.detailBackRequested()
                onActionRequested: function(actionId) { root.detailActionRequested(actionId) }
            }
        }
    }
}

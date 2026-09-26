pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Models 1.0 as AppModels
import Platform.Components 1.0 as PlatformComponents

// Site Detail's Employees tab: a real, site_id-scoped, server-paginated
// management view -- the shared platform Employee master filtered to this
// site, using the same canonical AdminEntityWorkspace stack Organization
// Detail's own Employees tab uses (see OrganizationEmployeesSection.qml).
// "New Employee" creates a new Employee with this site preselected --
// EmployeeService.create_employee already accepts site_id at creation time;
// there is no separate "assign an existing employee to a site" operation in
// the Employee domain today (site (re)assignment for an existing employee
// is just one field on the generic update_employee), so no such affordance
// is offered here. Row activation opens the standalone Employees
// workspace's own Employee Detail page rather than nesting a second copy
// of that UI here.
Item {
    id: root

    property var platformCatalog: null
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
    property var departmentFilterOptions: []
    property string departmentFilter: ""

    signal createRequested()
    signal rowSelected(string id)
    signal rowActivated(string id)
    signal refreshRequested()
    signal searchChanged(string text)
    signal pageRequested(int page)
    signal pageSizeRequested(int pageSize)
    signal clearFiltersRequested()
    signal statusFilterRequested(string value)
    signal departmentFilterRequested(string value)

    width: parent ? parent.width : 0
    height: root.viewportHeight

    AppModels.DynamicTableModel {
        id: _tableModel
        rows: root.catalog.items || []
    }

    PlatformComponents.AdminEntityWorkspace {
        id: _workspace
        anchors.fill: parent
        sectionTitle: "Employees"
        entityLabel: "Employee"
        catalog: root.catalog
        catalogModel: _tableModel
        tableId: "site.detail.employees.table"
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
            id: _departmentFilterCombo
            Layout.preferredWidth: 170
            model: root.departmentFilterOptions
            textRole: "label"
            valueRole: "value"
            currentIndex: {
                for (let i = 0; i < root.departmentFilterOptions.length; i += 1) {
                    if (root.departmentFilterOptions[i].value === root.departmentFilter) return i
                }
                return 0
            }
            onActivated: root.departmentFilterRequested(String(currentValue || ""))
        }

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
            onActivated: root.statusFilterRequested(String(currentValue || ""))
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
}

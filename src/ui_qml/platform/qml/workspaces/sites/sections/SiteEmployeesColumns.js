// Column configuration for the Employees table -- shared by the standalone
// Sites workspace's Employees tab (SitesWorkspacePage.qml) and Site
// Detail's own Employees section (SiteEmployeesSection.qml), which both
// render the same shared Employee master rows.

function columns() {
    return [
        { key: "title",          label: "Name",             flex: 3, minWidth: 160, sortable: true,  visible: true },
        { key: "subtitle",       label: "Code / Job Title", flex: 3, minWidth: 180, sortable: false, visible: true },
        { key: "departmentName", label: "Department",       flex: 2.4, minWidth: 180, sortable: true, visible: true },
        { key: "siteName",       label: "Site",             flex: 2.2, minWidth: 160, sortable: true, visible: true },
        { key: "statusLabel",    label: "Status",           flex: 0, minWidth: 90,  sortable: false, visible: true, type: "status" },
        { key: "metaText",       label: "Employment",       flex: 3, minWidth: 160, sortable: false, visible: true }
    ]
}

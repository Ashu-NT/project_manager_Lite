// Column configuration for the Departments table -- shared by the
// standalone Sites workspace's Departments tab (SitesWorkspacePage.qml)
// and Site Detail's own Departments section (SiteDepartmentsSection.qml),
// which both render the same shared Department master rows.

function columns() {
    return [
        { key: "title",       label: "Name",        flex: 3, minWidth: 160, sortable: true,  visible: true },
        { key: "subtitle",    label: "Code / Type", flex: 3, minWidth: 160, sortable: false, visible: true },
        { key: "siteName",    label: "Site",        flex: 2.4, minWidth: 180, sortable: true, visible: true },
        { key: "statusLabel", label: "Status",      flex: 0, minWidth: 90,  sortable: false, visible: true, type: "status" },
        { key: "metaText",    label: "Cost Center", flex: 2, minWidth: 120, sortable: false, visible: true }
    ]
}

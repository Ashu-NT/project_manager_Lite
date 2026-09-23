pragma ComponentBehavior: Bound
import QtQuick
import Platform.Components 1.0

// Site Detail's Employees tab -- a read-only view of the shared platform
// Employee master filtered to this site, via an explicit site_id-scoped
// backend query (see AdminSiteDetailPage.qml's _employeeRows /
// employeesForSite(site_id)). Not a second Employee management surface --
// "New Employee"/"Open Employees" (toolbar actions owned by the
// orchestrator) are the only mutation/full-workspace entry points.
AdminDetailTableSection {
    id: root
    width: parent ? parent.width : 0
    sectionLabel: "Employees"
    infoMessage: "Employee assignment remains sourced from the shared employee master."
    emptyTitle: "No employees mapped"
    emptyMessage: "This site does not currently have employees assigned."
}

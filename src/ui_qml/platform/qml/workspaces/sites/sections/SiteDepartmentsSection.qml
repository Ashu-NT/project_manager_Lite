pragma ComponentBehavior: Bound
import QtQuick
import Platform.Components 1.0

// Site Detail's Departments tab -- a read-only view of the shared platform
// Department master filtered to this site, via an explicit site_id-scoped
// backend query (see AdminSiteDetailPage.qml's _departmentRows). Not a
// second Department management surface -- "New Department"/"Open
// Departments" (toolbar actions owned by the orchestrator) are the only
// mutation/full-workspace entry points.
AdminDetailTableSection {
    id: root
    width: parent ? parent.width : 0
    sectionLabel: "Departments"
    infoMessage: "Departments remain shared platform masters. This section filters them by the selected site association."
    emptyTitle: "No departments for this site"
    emptyMessage: "No departments are currently assigned to this site."
}

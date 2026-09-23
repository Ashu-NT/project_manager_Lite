pragma ComponentBehavior: Bound
import QtQuick
import Platform.Components 1.0

// Site Detail's Documents tab -- an informational boundary. The admin
// controller does not yet surface a site-filtered document relationship
// view (unlike Departments/Employees, which have an explicit site_id-scoped
// read path), so this intentionally delegates to the shared Documents
// workspace rather than fabricating a filtered list.
AdminInformationalDetailSection {
    id: root
    width: parent ? parent.width : 0
    sectionLabel: "Documents"
    infoMessage: "Site-scoped document governance remains in the shared documents workspace."
    cardTitle: "Document Boundary"
    notes: [
        "Use the shared Documents workspace to manage governed documents and document structures linked to platform records.",
        "The admin controller does not yet surface a site-filtered document relationship view, so this section intentionally delegates to the owning document workspace."
    ]
}

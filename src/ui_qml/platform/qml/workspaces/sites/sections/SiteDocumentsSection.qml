pragma ComponentBehavior: Bound
import QtQuick
import Platform.Components 1.0

// Site Detail's Documents tab. The Documents domain has no site_id
// association today (no column on the document record, and no populated
// document-link rows for sites), so this intentionally delegates to the
// shared Documents workspace rather than fabricating a filtered list.
AdminInformationalDetailSection {
    id: root
    width: parent ? parent.width : 0
    sectionLabel: "Documents"
    cardTitle: "Documents"
    icon: "documents"
    maxContentWidth: 800
    notes: [
        "Documents are managed centrally in the Documents workspace."
    ]
    ctaLabel: "Open Documents"
}

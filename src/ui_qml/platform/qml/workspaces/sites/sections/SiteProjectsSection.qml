pragma ComponentBehavior: Bound
import QtQuick
import Platform.Components 1.0

// Site Detail's Projects tab (only shown when Project Management is
// enabled for this tenant). No safe, already-approved cross-module read
// exists today for Platform to show real PM project rows scoped to a site
// (Platform must not depend on Project Management's schema -- see
// test_platform_does_not_import_business_modules.py), so this stays a
// polished business-facing summary rather than a fabricated local table.
AdminInformationalDetailSection {
    id: root
    width: parent ? parent.width : 0
    sectionLabel: "Projects"
    cardTitle: "Projects"
    notes: [
        "Projects associated with this site are managed in Project Management.",
        "Open Project Management to review projects, schedules, and delivery records linked to this site."
    ]
}

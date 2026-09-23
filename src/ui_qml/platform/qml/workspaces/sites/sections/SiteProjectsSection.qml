pragma ComponentBehavior: Bound
import QtQuick
import Platform.Components 1.0

// Site Detail's Projects tab (only shown when Project Management is
// enabled for this tenant) -- an informational boundary pointing to the
// PM module, which owns project/site alignment. Site Detail never
// duplicates PM's own project data here.
AdminInformationalDetailSection {
    id: root
    width: parent ? parent.width : 0
    sectionLabel: "Projects"
    infoMessage: "Project Management is enabled for this tenant. Project/site alignment stays PM-owned and references the shared site master."
    cardTitle: "PM Boundary"
    notes: [
        "Use the Project Management module to review projects, work packages, schedules, and delivery records linked to this site.",
        "Platform admin keeps the site reference authoritative while PM owns the project and task execution layer."
    ]
}

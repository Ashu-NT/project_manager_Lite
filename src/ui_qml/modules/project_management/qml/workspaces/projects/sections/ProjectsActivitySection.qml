import ProjectManagement.Widgets 1.0 as PMWidgets

// Thin wrapper: Projects' Activity section is the shared
// PMWidgets.ActivityLogSection design (search + RecordListCard feed).
// Kept as its own named component only so ProjectsDetailPanel.qml's
// existing `projectActivityModel` prop name doesn't need to change;
// `sectionErrors`/`label`/`errorKey` are inherited from the base as-is
// (its own "Activity"/"activity" defaults already match what Projects
// needs).
PMWidgets.ActivityLogSection {
    id: root

    property var projectActivityModel: ({
        "title": "Activity", "subtitle": "", "emptyState": "No activity has been recorded for this project yet.", "items": []
    })

    activityModel: root.projectActivityModel
}

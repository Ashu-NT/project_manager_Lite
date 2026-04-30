import QtQuick
import ProjectManagement.Widgets 1.0 as ProjectManagementWidgets

ProjectManagementWidgets.RecordListCard {
    id: root

    property var projectsModel: ({
        "title": "",
        "subtitle": "",
        "emptyState": "",
        "items": []
    })
    property string selectedProjectId: ""
    property bool isBusy: false

    signal projectSelected(string projectId)
    signal editRequested(var projectData)
    signal statusRequested(var projectData)
    signal deleteRequested(var projectData)

    title: root.projectsModel.title || "Project Catalog"
    subtitle: root.projectsModel.subtitle || ""
    emptyState: root.projectsModel.emptyState || ""
    items: root.projectsModel.items || []
    selectedItemId: root.selectedProjectId
    primaryActionLabel: "Edit"
    secondaryActionLabel: "Status"
    tertiaryActionLabel: "Delete"
    tertiaryDanger: true
    actionsEnabled: !root.isBusy

    onItemSelected: function(itemId) {
        root.projectSelected(itemId)
    }

    onPrimaryActionRequested: function(itemData) {
        root.editRequested(itemData)
    }

    onSecondaryActionRequested: function(itemData) {
        root.statusRequested(itemData)
    }

    onTertiaryActionRequested: function(itemData) {
        root.deleteRequested(itemData)
    }
}

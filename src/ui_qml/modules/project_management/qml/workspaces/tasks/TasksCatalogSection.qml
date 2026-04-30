import QtQuick
import ProjectManagement.Widgets 1.0 as ProjectManagementWidgets

ProjectManagementWidgets.RecordListCard {
    id: root

    property var tasksModel: ({
        "title": "",
        "subtitle": "",
        "emptyState": "",
        "items": []
    })
    property string selectedTaskId: ""
    property bool isBusy: false

    signal taskSelected(string taskId)
    signal editRequested(var taskData)
    signal progressRequested(var taskData)
    signal deleteRequested(var taskData)

    title: root.tasksModel.title || "Task Catalog"
    subtitle: root.tasksModel.subtitle || ""
    emptyState: root.tasksModel.emptyState || ""
    items: root.tasksModel.items || []
    selectedItemId: root.selectedTaskId
    primaryActionLabel: "Edit"
    secondaryActionLabel: "Progress"
    tertiaryActionLabel: "Delete"
    tertiaryDanger: true
    actionsEnabled: !root.isBusy

    onItemSelected: function(itemId) {
        root.taskSelected(itemId)
    }

    onPrimaryActionRequested: function(itemData) {
        root.editRequested(itemData)
    }

    onSecondaryActionRequested: function(itemData) {
        root.progressRequested(itemData)
    }

    onTertiaryActionRequested: function(itemData) {
        root.deleteRequested(itemData)
    }
}

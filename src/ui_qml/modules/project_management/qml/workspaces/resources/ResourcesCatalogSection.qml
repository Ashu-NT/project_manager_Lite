import QtQuick
import ProjectManagement.Widgets 1.0 as ProjectManagementWidgets

ProjectManagementWidgets.RecordListCard {
    id: root

    property var resourcesModel: ({
        "title": "",
        "subtitle": "",
        "emptyState": "",
        "items": []
    })
    property string selectedResourceId: ""
    property bool isBusy: false

    signal resourceSelected(string resourceId)
    signal editRequested(var resourceData)
    signal toggleRequested(var resourceData)
    signal deleteRequested(var resourceData)

    title: root.resourcesModel.title || "Resource Pool"
    subtitle: root.resourcesModel.subtitle || ""
    emptyState: root.resourcesModel.emptyState || ""
    items: root.resourcesModel.items || []
    selectedItemId: root.selectedResourceId
    primaryActionLabel: "Edit"
    secondaryActionLabel: "Toggle Active"
    tertiaryActionLabel: "Delete"
    tertiaryDanger: true
    actionsEnabled: !root.isBusy

    onItemSelected: function(itemId) {
        root.resourceSelected(itemId)
    }

    onPrimaryActionRequested: function(itemData) {
        root.editRequested(itemData)
    }

    onSecondaryActionRequested: function(itemData) {
        root.toggleRequested(itemData)
    }

    onTertiaryActionRequested: function(itemData) {
        root.deleteRequested(itemData)
    }
}

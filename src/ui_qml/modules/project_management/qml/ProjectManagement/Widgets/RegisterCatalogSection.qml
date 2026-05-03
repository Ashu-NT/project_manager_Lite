import QtQuick

RecordListCard {
    id: root

    property var entriesModel: ({
        "title": "",
        "subtitle": "",
        "emptyState": "",
        "items": []
    })
    property string selectedEntryId: ""
    property bool isBusy: false

    signal entrySelected(string entryId)
    signal editRequested(var entryData)
    signal deleteRequested(var entryData)

    title: root.entriesModel.title || "Register Entries"
    subtitle: root.entriesModel.subtitle || ""
    emptyState: root.entriesModel.emptyState || ""
    items: root.entriesModel.items || []
    selectedItemId: root.selectedEntryId
    primaryActionLabel: "Edit"
    secondaryActionLabel: "Delete"
    secondaryDanger: true
    actionsEnabled: !root.isBusy

    onItemSelected: function(itemId) {
        root.entrySelected(itemId)
    }

    onPrimaryActionRequested: function(itemData) {
        root.editRequested(itemData)
    }

    onSecondaryActionRequested: function(itemData) {
        root.deleteRequested(itemData)
    }
}

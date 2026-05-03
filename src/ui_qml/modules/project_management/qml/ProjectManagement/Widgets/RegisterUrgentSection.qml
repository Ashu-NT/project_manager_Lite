import QtQuick

RecordListCard {
    id: root

    property var urgentModel: ({
        "title": "",
        "subtitle": "",
        "emptyState": "",
        "items": []
    })
    property string selectedEntryId: ""

    signal entrySelected(string entryId)

    title: root.urgentModel.title || "Urgent Review Queue"
    subtitle: root.urgentModel.subtitle || ""
    emptyState: root.urgentModel.emptyState || ""
    items: root.urgentModel.items || []
    selectedItemId: root.selectedEntryId

    onItemSelected: function(itemId) {
        root.entrySelected(itemId)
    }
}

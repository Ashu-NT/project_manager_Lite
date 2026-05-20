import QtQuick
import App.Mock 1.0 as AppMock

RecordListCard {
    id: root

    property var urgentModel: AppMock.MockFactory.catalog()
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

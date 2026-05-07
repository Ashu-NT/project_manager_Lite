import QtQuick
import InventoryProcurement.Widgets 1.0 as InventoryWidgets

InventoryWidgets.RecordListCard {
    id: root

    property var categoriesModel: ({
        "title": "",
        "subtitle": "",
        "emptyState": "",
        "items": []
    })
    property string selectedCategoryId: ""
    property bool isBusy: false

    signal categorySelected(string categoryId)
    signal editRequested(var categoryData)
    signal toggleRequested(var categoryData)

    title: root.categoriesModel.title || "Category Catalog"
    subtitle: root.categoriesModel.subtitle || ""
    emptyState: root.categoriesModel.emptyState || ""
    items: root.categoriesModel.items || []
    selectedItemId: root.selectedCategoryId
    primaryActionLabel: "Edit"
    secondaryActionLabel: "Toggle Active"
    actionsEnabled: !root.isBusy

    onItemSelected: function(categoryId) {
        root.categorySelected(categoryId)
    }

    onPrimaryActionRequested: function(categoryData) {
        root.editRequested(categoryData)
    }

    onSecondaryActionRequested: function(categoryData) {
        root.toggleRequested(categoryData)
    }
}

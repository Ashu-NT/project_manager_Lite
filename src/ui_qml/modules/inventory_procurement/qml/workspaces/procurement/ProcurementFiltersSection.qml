import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme

Item {
    id: root

    property var siteOptions: []
    property var storeroomOptions: []
    property var supplierOptions: []
    property var requisitionStatusOptions: []
    property var purchaseOrderStatusOptions: []
    property string selectedSiteFilter: "all"
    property string selectedStoreroomFilter: "all"
    property string selectedSupplierFilter: "all"
    property string selectedRequisitionStatusFilter: "all"
    property string selectedPurchaseOrderStatusFilter: "all"
    property string searchText: ""
    property bool isBusy: false

    signal searchTextUpdated(string searchText)
    signal siteFilterUpdated(string siteId)
    signal storeroomFilterUpdated(string storeroomId)
    signal supplierFilterUpdated(string supplierId)
    signal requisitionStatusFilterUpdated(string status)
    signal purchaseOrderStatusFilterUpdated(string status)
    signal refreshRequested()
    signal createRequisitionRequested()
    signal createPurchaseOrderRequested()

    implicitHeight: contentLayout.implicitHeight

    function indexForValue(options, targetValue) {
        for (var index = 0; index < options.length; index += 1) {
            if (String(options[index].value || "") === String(targetValue || "")) {
                return index
            }
        }
        return 0
    }

    ColumnLayout {
        id: contentLayout

        anchors.fill: parent
        spacing: Theme.AppTheme.spacingMd

        RowLayout {
            Layout.fillWidth: true

            Label {
                Layout.fillWidth: true
                text: "Procurement Filters"
                color: Theme.AppTheme.textPrimary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.bodySize
                font.bold: true
            }

            AppControls.PrimaryButton {
                text: "New Requisition"
                iconName: "add"
                enabled: !root.isBusy
                onClicked: root.createRequisitionRequested()
            }

            AppControls.PrimaryButton {
                text: "New Purchase Order"
                iconName: "add"
                enabled: !root.isBusy
                onClicked: root.createPurchaseOrderRequested()
            }

            AppControls.PrimaryButton {
                text: "Refresh"
                iconName: "refresh"
                enabled: !root.isBusy
                onClicked: root.refreshRequested()
            }
        }

        GridLayout {
            Layout.fillWidth: true
            columns: root.width > 1140 ? 3 : (root.width > 760 ? 2 : 1)
            columnSpacing: Theme.AppTheme.spacingMd
            rowSpacing: Theme.AppTheme.spacingSm

            Label { text: "Search" }
            TextField {
                id: searchField
                Layout.fillWidth: true
                placeholderText: "Number, purpose, supplier, or reference"
                text: root.searchText
                enabled: !root.isBusy
                onEditingFinished: root.searchTextUpdated(text)
            }

            Item { Layout.fillWidth: true }

            Label { text: "Site" }
            ComboBox {
                Layout.fillWidth: true
                model: root.siteOptions
                textRole: "label"
                currentIndex: root.indexForValue(root.siteOptions, root.selectedSiteFilter)
                enabled: !root.isBusy
                onActivated: function(index) {
                    var option = root.siteOptions[index] || { "value": "all" }
                    root.siteFilterUpdated(String(option.value || "all"))
                }
            }

            Label { text: "Storeroom" }
            ComboBox {
                Layout.fillWidth: true
                model: root.storeroomOptions
                textRole: "label"
                currentIndex: root.indexForValue(root.storeroomOptions, root.selectedStoreroomFilter)
                enabled: !root.isBusy
                onActivated: function(index) {
                    var option = root.storeroomOptions[index] || { "value": "all" }
                    root.storeroomFilterUpdated(String(option.value || "all"))
                }
            }

            Label { text: "Supplier" }
            ComboBox {
                Layout.fillWidth: true
                model: root.supplierOptions
                textRole: "label"
                currentIndex: root.indexForValue(root.supplierOptions, root.selectedSupplierFilter)
                enabled: !root.isBusy
                onActivated: function(index) {
                    var option = root.supplierOptions[index] || { "value": "all" }
                    root.supplierFilterUpdated(String(option.value || "all"))
                }
            }

            Label { text: "Requisition status" }
            ComboBox {
                Layout.fillWidth: true
                model: root.requisitionStatusOptions
                textRole: "label"
                currentIndex: root.indexForValue(root.requisitionStatusOptions, root.selectedRequisitionStatusFilter)
                enabled: !root.isBusy
                onActivated: function(index) {
                    var option = root.requisitionStatusOptions[index] || { "value": "all" }
                    root.requisitionStatusFilterUpdated(String(option.value || "all"))
                }
            }

            Label { text: "PO status" }
            ComboBox {
                Layout.fillWidth: true
                model: root.purchaseOrderStatusOptions
                textRole: "label"
                currentIndex: root.indexForValue(root.purchaseOrderStatusOptions, root.selectedPurchaseOrderStatusFilter)
                enabled: !root.isBusy
                onActivated: function(index) {
                    var option = root.purchaseOrderStatusOptions[index] || { "value": "all" }
                    root.purchaseOrderStatusFilterUpdated(String(option.value || "all"))
                }
            }
        }
    }
}

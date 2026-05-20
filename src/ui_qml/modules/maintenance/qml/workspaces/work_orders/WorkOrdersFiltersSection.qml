import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme

Item {
    id: root

    property var siteOptions: []
    property var statusOptions: []
    property var priorityOptions: []
    property var workOrderTypeOptions: []
    property var assetOptions: []
    property string selectedSiteFilter: "all"
    property string selectedStatusFilter: "all"
    property string selectedPriorityFilter: "all"
    property string selectedWorkOrderTypeFilter: "all"
    property string selectedAssetFilter: "all"
    property string searchText: ""
    property bool isBusy: false

    signal searchTextUpdated(string searchText)
    signal siteFilterUpdated(string siteId)
    signal statusFilterUpdated(string status)
    signal priorityFilterUpdated(string priority)
    signal workOrderTypeFilterUpdated(string workOrderType)
    signal assetFilterUpdated(string assetId)
    signal refreshRequested()
    signal createRequested()

    implicitHeight: contentLayout.implicitHeight

    function indexForValue(options, targetValue) {
        for (let index = 0; index < options.length; index += 1) {
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
                text: "Work Order Filters"
                color: Theme.AppTheme.textPrimary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.bodySize
                font.bold: true
            }

            AppControls.PrimaryButton {
                text: "New Work Order"
                iconName: "add"
                enabled: !root.isBusy
                onClicked: root.createRequested()
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
            columns: root.width > 900 ? 4 : (root.width > 620 ? 2 : 1)
            columnSpacing: Theme.AppTheme.spacingMd
            rowSpacing: Theme.AppTheme.spacingSm

            Label { text: "Search" }
            TextField {
                Layout.fillWidth: true
                placeholderText: "Code, title, type, source, asset, or vendor"
                text: root.searchText
                enabled: !root.isBusy
                onEditingFinished: root.searchTextUpdated(text)
            }

            Label { text: "Site" }
            ComboBox {
                Layout.fillWidth: true
                model: root.siteOptions
                textRole: "label"
                currentIndex: root.indexForValue(root.siteOptions, root.selectedSiteFilter)
                enabled: !root.isBusy
                onActivated: function(index) {
                    const option = root.siteOptions[index] || { "value": "all" }
                    root.siteFilterUpdated(String(option.value || "all"))
                }
            }

            Label { text: "Status" }
            ComboBox {
                Layout.fillWidth: true
                model: root.statusOptions
                textRole: "label"
                currentIndex: root.indexForValue(root.statusOptions, root.selectedStatusFilter)
                enabled: !root.isBusy
                onActivated: function(index) {
                    const option = root.statusOptions[index] || { "value": "all" }
                    root.statusFilterUpdated(String(option.value || "all"))
                }
            }

            Label { text: "Priority" }
            ComboBox {
                Layout.fillWidth: true
                model: root.priorityOptions
                textRole: "label"
                currentIndex: root.indexForValue(root.priorityOptions, root.selectedPriorityFilter)
                enabled: !root.isBusy
                onActivated: function(index) {
                    const option = root.priorityOptions[index] || { "value": "all" }
                    root.priorityFilterUpdated(String(option.value || "all"))
                }
            }

            Label { text: "Type" }
            ComboBox {
                Layout.fillWidth: true
                model: root.workOrderTypeOptions
                textRole: "label"
                currentIndex: root.indexForValue(root.workOrderTypeOptions, root.selectedWorkOrderTypeFilter)
                enabled: !root.isBusy
                onActivated: function(index) {
                    const option = root.workOrderTypeOptions[index] || { "value": "all" }
                    root.workOrderTypeFilterUpdated(String(option.value || "all"))
                }
            }

            Label { text: "Asset" }
            ComboBox {
                Layout.fillWidth: true
                model: root.assetOptions
                textRole: "label"
                currentIndex: root.indexForValue(root.assetOptions, root.selectedAssetFilter)
                enabled: !root.isBusy
                onActivated: function(index) {
                    const option = root.assetOptions[index] || { "value": "all" }
                    root.assetFilterUpdated(String(option.value || "all"))
                }
            }
        }
    }
}

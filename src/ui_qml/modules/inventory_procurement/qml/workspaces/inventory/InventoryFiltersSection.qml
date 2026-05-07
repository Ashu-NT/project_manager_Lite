import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme

Rectangle {
    id: root

    property var siteOptions: []
    property var activeOptions: []
    property var storeroomOptions: []
    property var itemOptions: []
    property var transactionTypeOptions: []
    property string selectedSiteFilter: "all"
    property string selectedActiveFilter: "all"
    property string selectedStoreroomFilter: "all"
    property string selectedItemFilter: "all"
    property string selectedTransactionTypeFilter: "all"
    property string searchText: ""
    property bool isBusy: false

    signal searchTextUpdated(string searchText)
    signal siteFilterUpdated(string siteId)
    signal activeFilterUpdated(string activeValue)
    signal storeroomFilterUpdated(string storeroomId)
    signal itemFilterUpdated(string itemId)
    signal transactionTypeFilterUpdated(string transactionType)
    signal refreshRequested()
    signal createStoreroomRequested()
    signal openOpeningBalanceRequested()

    radius: Theme.AppTheme.radiusLg
    color: Theme.AppTheme.surface
    border.color: Theme.AppTheme.border
    implicitHeight: contentLayout.implicitHeight + (Theme.AppTheme.marginLg * 2)

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
        anchors.margins: Theme.AppTheme.marginLg
        spacing: Theme.AppTheme.spacingMd

        RowLayout {
            Layout.fillWidth: true

            Label {
                Layout.fillWidth: true
                text: "Operational Filters"
                color: Theme.AppTheme.textPrimary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.bodySize
                font.bold: true
            }

            AppControls.PrimaryButton {
                text: "Create Storeroom"
                enabled: !root.isBusy
                onClicked: root.createStoreroomRequested()
            }

            AppControls.PrimaryButton {
                text: "Opening Balance"
                enabled: !root.isBusy
                onClicked: root.openOpeningBalanceRequested()
            }

            AppControls.PrimaryButton {
                text: "Refresh"
                enabled: !root.isBusy
                onClicked: root.refreshRequested()
            }
        }

        GridLayout {
            Layout.fillWidth: true
            columns: root.width > 980 ? 3 : (root.width > 680 ? 2 : 1)
            columnSpacing: Theme.AppTheme.spacingMd
            rowSpacing: Theme.AppTheme.spacingSm

            Label { text: "Search" }
            TextField {
                id: searchField
                Layout.fillWidth: true
                Layout.columnSpan: root.width > 980 ? 2 : 1
                placeholderText: "Storeroom, item, transaction, or reference"
                text: root.searchText
                enabled: !root.isBusy
                onEditingFinished: root.searchTextUpdated(text)
            }

            Label { text: "Site" }
            ComboBox {
                id: siteCombo
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

            Label { text: "Storeroom activity" }
            ComboBox {
                id: activeCombo
                Layout.fillWidth: true
                model: root.activeOptions
                textRole: "label"
                currentIndex: root.indexForValue(root.activeOptions, root.selectedActiveFilter)
                enabled: !root.isBusy
                onActivated: function(index) {
                    var option = root.activeOptions[index] || { "value": "all" }
                    root.activeFilterUpdated(String(option.value || "all"))
                }
            }

            Label { text: "Storeroom" }
            ComboBox {
                id: storeroomCombo
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

            Label { text: "Item" }
            ComboBox {
                id: itemCombo
                Layout.fillWidth: true
                model: root.itemOptions
                textRole: "label"
                currentIndex: root.indexForValue(root.itemOptions, root.selectedItemFilter)
                enabled: !root.isBusy
                onActivated: function(index) {
                    var option = root.itemOptions[index] || { "value": "all" }
                    root.itemFilterUpdated(String(option.value || "all"))
                }
            }

            Label { text: "Movement" }
            ComboBox {
                id: transactionTypeCombo
                Layout.fillWidth: true
                model: root.transactionTypeOptions
                textRole: "label"
                currentIndex: root.indexForValue(root.transactionTypeOptions, root.selectedTransactionTypeFilter)
                enabled: !root.isBusy
                onActivated: function(index) {
                    var option = root.transactionTypeOptions[index] || { "value": "all" }
                    root.transactionTypeFilterUpdated(String(option.value || "all"))
                }
            }
        }
    }
}

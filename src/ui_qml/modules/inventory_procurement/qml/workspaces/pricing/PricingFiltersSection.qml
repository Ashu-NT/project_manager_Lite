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
    property var limitOptions: []
    property string selectedSiteFilter: "all"
    property string selectedStoreroomFilter: "all"
    property string selectedSupplierFilter: "all"
    property string selectedLimitFilter: "200"
    property string contextLabel: ""
    property bool isBusy: false

    signal siteFilterUpdated(string siteId)
    signal storeroomFilterUpdated(string storeroomId)
    signal supplierFilterUpdated(string supplierId)
    signal limitFilterUpdated(string limitValue)
    signal refreshRequested()

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
            spacing: Theme.AppTheme.spacingSm

            Label {
                Layout.fillWidth: true
                text: "Pricing Filters"
                color: Theme.AppTheme.textPrimary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.bodySize
                font.bold: true
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
            columns: root.width > 1120 ? 4 : (root.width > 820 ? 2 : 1)
            columnSpacing: Theme.AppTheme.spacingMd
            rowSpacing: Theme.AppTheme.spacingSm

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

            Label { text: "Storeroom" }
            ComboBox {
                Layout.fillWidth: true
                model: root.storeroomOptions
                textRole: "label"
                currentIndex: root.indexForValue(root.storeroomOptions, root.selectedStoreroomFilter)
                enabled: !root.isBusy
                onActivated: function(index) {
                    const option = root.storeroomOptions[index] || { "value": "all" }
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
                    const option = root.supplierOptions[index] || { "value": "all" }
                    root.supplierFilterUpdated(String(option.value || "all"))
                }
            }

            Label { text: "Procurement limit" }
            ComboBox {
                Layout.fillWidth: true
                model: root.limitOptions
                textRole: "label"
                currentIndex: root.indexForValue(root.limitOptions, root.selectedLimitFilter)
                enabled: !root.isBusy
                onActivated: function(index) {
                    const option = root.limitOptions[index] || { "value": "200" }
                    root.limitFilterUpdated(String(option.value || "200"))
                }
            }
        }

        Label {
            Layout.fillWidth: true
            text: root.contextLabel.length > 0
                ? "Current scope: " + root.contextLabel
                : "Current scope updates as filters change."
            color: Theme.AppTheme.textSecondary
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.smallSize
            wrapMode: Text.WordWrap
        }
    }
}

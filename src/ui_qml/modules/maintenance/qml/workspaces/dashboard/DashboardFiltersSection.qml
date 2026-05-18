import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme

Item {
    id: root

    property var siteOptions: []
    property var assetOptions: []
    property var systemOptions: []
    property var locationOptions: []
    property var windowOptions: []
    property string selectedSiteFilter: "all"
    property string selectedAssetFilter: "all"
    property string selectedSystemFilter: "all"
    property string selectedLocationFilter: "all"
    property string selectedDaysFilter: "90"
    property bool isBusy: false

    signal siteFilterUpdated(string siteId)
    signal assetFilterUpdated(string assetId)
    signal systemFilterUpdated(string systemId)
    signal locationFilterUpdated(string locationId)
    signal daysFilterUpdated(int days)
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
                text: "Dashboard Filters"
                color: Theme.AppTheme.textPrimary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.bodySize
                font.bold: true
            }

            AppControls.PrimaryButton {
                text: "Refresh"
                enabled: !root.isBusy
                onClicked: root.refreshRequested()
            }
        }

        GridLayout {
            Layout.fillWidth: true
            columns: root.width > 1120 ? 5 : (root.width > 820 ? 2 : 1)
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

            Label { text: "System" }
            ComboBox {
                Layout.fillWidth: true
                model: root.systemOptions
                textRole: "label"
                currentIndex: root.indexForValue(root.systemOptions, root.selectedSystemFilter)
                enabled: !root.isBusy
                onActivated: function(index) {
                    const option = root.systemOptions[index] || { "value": "all" }
                    root.systemFilterUpdated(String(option.value || "all"))
                }
            }

            Label { text: "Location" }
            ComboBox {
                Layout.fillWidth: true
                model: root.locationOptions
                textRole: "label"
                currentIndex: root.indexForValue(root.locationOptions, root.selectedLocationFilter)
                enabled: !root.isBusy
                onActivated: function(index) {
                    const option = root.locationOptions[index] || { "value": "all" }
                    root.locationFilterUpdated(String(option.value || "all"))
                }
            }

            Label { text: "Window" }
            ComboBox {
                Layout.fillWidth: true
                model: root.windowOptions
                textRole: "label"
                currentIndex: root.indexForValue(root.windowOptions, root.selectedDaysFilter)
                enabled: !root.isBusy
                onActivated: function(index) {
                    const option = root.windowOptions[index] || { "value": "90" }
                    root.daysFilterUpdated(Number(option.value || 90))
                }
            }
        }
    }
}

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
    property var failureSymptomOptions: []
    property var daysOptions: []
    property var limitOptions: []
    property var thresholdOptions: []
    property string selectedSiteFilter: "all"
    property string selectedAssetFilter: "all"
    property string selectedSystemFilter: "all"
    property string selectedLocationFilter: "all"
    property string selectedFailureCodeFilter: "all"
    property string selectedDaysFilter: "90"
    property string selectedLimitFilter: "20"
    property string selectedThresholdFilter: "2"
    property bool isBusy: false

    signal siteFilterUpdated(string siteId)
    signal assetFilterUpdated(string assetId)
    signal systemFilterUpdated(string systemId)
    signal locationFilterUpdated(string locationId)
    signal failureCodeFilterUpdated(string failureCode)
    signal daysFilterUpdated(int days)
    signal limitFilterUpdated(int limitValue)
    signal thresholdFilterUpdated(int thresholdValue)
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

            AppControls.Label {
                Layout.fillWidth: true
                text: "Reliability Filters"
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

            AppControls.Label { text: "Site" }
            AppControls.ComboBox {
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

            AppControls.Label { text: "Asset" }
            AppControls.ComboBox {
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

            AppControls.Label { text: "System" }
            AppControls.ComboBox {
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

            AppControls.Label { text: "Location" }
            AppControls.ComboBox {
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

            AppControls.Label { text: "Failure symptom" }
            AppControls.ComboBox {
                Layout.fillWidth: true
                model: root.failureSymptomOptions
                textRole: "label"
                currentIndex: root.indexForValue(root.failureSymptomOptions, root.selectedFailureCodeFilter)
                enabled: !root.isBusy
                onActivated: function(index) {
                    const option = root.failureSymptomOptions[index] || { "value": "all" }
                    root.failureCodeFilterUpdated(String(option.value || "all"))
                }
            }

            AppControls.Label { text: "Window" }
            AppControls.ComboBox {
                Layout.fillWidth: true
                model: root.daysOptions
                textRole: "label"
                currentIndex: root.indexForValue(root.daysOptions, root.selectedDaysFilter)
                enabled: !root.isBusy
                onActivated: function(index) {
                    const option = root.daysOptions[index] || { "value": "90" }
                    root.daysFilterUpdated(Number(option.value || 90))
                }
            }

            AppControls.Label { text: "Limit" }
            AppControls.ComboBox {
                Layout.fillWidth: true
                model: root.limitOptions
                textRole: "label"
                currentIndex: root.indexForValue(root.limitOptions, root.selectedLimitFilter)
                enabled: !root.isBusy
                onActivated: function(index) {
                    const option = root.limitOptions[index] || { "value": "20" }
                    root.limitFilterUpdated(Number(option.value || 20))
                }
            }

            AppControls.Label { text: "Recurring threshold" }
            AppControls.ComboBox {
                Layout.fillWidth: true
                model: root.thresholdOptions
                textRole: "label"
                currentIndex: root.indexForValue(root.thresholdOptions, root.selectedThresholdFilter)
                enabled: !root.isBusy
                onActivated: function(index) {
                    const option = root.thresholdOptions[index] || { "value": "2" }
                    root.thresholdFilterUpdated(Number(option.value || 2))
                }
            }
        }
    }
}

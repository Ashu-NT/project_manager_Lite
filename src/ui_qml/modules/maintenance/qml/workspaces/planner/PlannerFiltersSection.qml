import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme

Rectangle {
    id: root

    property var siteOptions: []
    property var assetOptions: []
    property var systemOptions: []
    property var requestQueueOptions: []
    property var workOrderQueueOptions: []
    property string selectedSiteFilter: "all"
    property string selectedAssetFilter: "all"
    property string selectedSystemFilter: "all"
    property string selectedRequestQueue: ""
    property string selectedWorkOrderQueue: ""
    property string searchText: ""
    property bool isBusy: false

    signal siteFilterUpdated(string siteId)
    signal assetFilterUpdated(string assetId)
    signal systemFilterUpdated(string systemId)
    signal requestQueueUpdated(string requestQueue)
    signal workOrderQueueUpdated(string workOrderQueue)
    signal searchTextUpdated(string searchText)
    signal refreshRequested()

    radius: Theme.AppTheme.radiusLg
    color: Theme.AppTheme.surface
    border.color: Theme.AppTheme.border
    implicitHeight: contentLayout.implicitHeight + (Theme.AppTheme.marginLg * 2)

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
        anchors.margins: Theme.AppTheme.marginLg
        spacing: Theme.AppTheme.spacingMd

        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.AppTheme.spacingSm

            Label {
                Layout.fillWidth: true
                text: "Planner Filters"
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

            Label { text: "Request queue" }
            ComboBox {
                Layout.fillWidth: true
                model: root.requestQueueOptions
                textRole: "label"
                currentIndex: root.indexForValue(root.requestQueueOptions, root.selectedRequestQueue)
                enabled: !root.isBusy
                onActivated: function(index) {
                    const option = root.requestQueueOptions[index] || { "value": "" }
                    root.requestQueueUpdated(String(option.value || ""))
                }
            }

            Label { text: "Work order queue" }
            ComboBox {
                Layout.fillWidth: true
                model: root.workOrderQueueOptions
                textRole: "label"
                currentIndex: root.indexForValue(root.workOrderQueueOptions, root.selectedWorkOrderQueue)
                enabled: !root.isBusy
                onActivated: function(index) {
                    const option = root.workOrderQueueOptions[index] || { "value": "" }
                    root.workOrderQueueUpdated(String(option.value || ""))
                }
            }

            Label { text: "Search" }
            TextField {
                Layout.fillWidth: true
                text: root.searchText
                enabled: !root.isBusy
                placeholderText: "Filter requests, orders, and codes"
                onEditingFinished: root.searchTextUpdated(text)
            }
        }
    }
}

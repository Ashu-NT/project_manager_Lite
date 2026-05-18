import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme

Item {
    id: root

    property var siteOptions: []
    property var activeFilterOptions: []
    property string selectedSiteFilter: "all"
    property string selectedActiveFilter: "all"
    property string searchText: ""
    property bool isBusy: false

    signal searchTextUpdated(string searchText)
    signal siteFilterUpdated(string siteId)
    signal activeFilterUpdated(string activeFilter)
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

            ColumnLayout {
                Layout.fillWidth: true
                spacing: Theme.AppTheme.spacingXs

                Label {
                    Layout.fillWidth: true
                    text: "Asset Library Filters"
                    color: Theme.AppTheme.textPrimary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.bodySize
                    font.bold: true
                }

                Label {
                    Layout.fillWidth: true
                    text: "Location selection scopes systems and assets. Asset selection scopes components."
                    color: Theme.AppTheme.textSecondary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                    wrapMode: Text.WordWrap
                }
            }

            AppControls.PrimaryButton {
                text: "Refresh"
                enabled: !root.isBusy
                onClicked: root.refreshRequested()
            }
        }

        GridLayout {
            Layout.fillWidth: true
            columns: root.width > 760 ? 3 : 1
            columnSpacing: Theme.AppTheme.spacingMd
            rowSpacing: Theme.AppTheme.spacingSm

            Label { text: "Search" }
            TextField {
                Layout.fillWidth: true
                placeholderText: "Code, name, anchor, type, vendor, or notes"
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
                    const option = root.siteOptions[index] || { "value": "all" }
                    root.siteFilterUpdated(String(option.value || "all"))
                }
            }

            Label { text: "State" }
            ComboBox {
                Layout.fillWidth: true
                model: root.activeFilterOptions
                textRole: "label"
                currentIndex: root.indexForValue(root.activeFilterOptions, root.selectedActiveFilter)
                enabled: !root.isBusy
                onActivated: function(index) {
                    const option = root.activeFilterOptions[index] || { "value": "all" }
                    root.activeFilterUpdated(String(option.value || "all"))
                }
            }
        }
    }
}

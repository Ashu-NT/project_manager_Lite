import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme

Rectangle {
    id: root

    property var statusOptions: []
    property var itemOptions: []
    property var storeroomOptions: []
    property string selectedStatusFilter: "all"
    property string selectedItemFilter: "all"
    property string selectedStoreroomFilter: "all"
    property string searchText: ""
    property bool isBusy: false

    signal searchTextUpdated(string searchText)
    signal statusFilterUpdated(string status)
    signal itemFilterUpdated(string itemId)
    signal storeroomFilterUpdated(string storeroomId)
    signal refreshRequested()
    signal createReservationRequested()

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
                text: "Reservation Filters"
                color: Theme.AppTheme.textPrimary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.bodySize
                font.bold: true
            }

            AppControls.PrimaryButton {
                text: "New Reservation"
                enabled: !root.isBusy
                onClicked: root.createReservationRequested()
            }

            AppControls.PrimaryButton {
                text: "Refresh"
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
                id: searchField
                Layout.fillWidth: true
                placeholderText: "Reservation number, source, or requester"
                text: root.searchText
                enabled: !root.isBusy
                onEditingFinished: root.searchTextUpdated(text)
            }

            Label { text: "Status" }
            ComboBox {
                id: statusCombo
                Layout.fillWidth: true
                model: root.statusOptions
                textRole: "label"
                currentIndex: root.indexForValue(root.statusOptions, root.selectedStatusFilter)
                enabled: !root.isBusy
                onActivated: function(index) {
                    var option = root.statusOptions[index] || { "value": "all" }
                    root.statusFilterUpdated(String(option.value || "all"))
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
        }
    }
}

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme

Item {
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

            AppControls.Label {
                Layout.fillWidth: true
                text: "Reservation Filters"
                color: Theme.AppTheme.textPrimary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.bodySize
                font.bold: true
            }

            AppControls.PrimaryButton {
                text: "New Reservation"
                iconName: "add"
                enabled: !root.isBusy
                onClicked: root.createReservationRequested()
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

            AppControls.Label { text: "Search" }
            AppControls.TextField {
                id: searchField
                Layout.fillWidth: true
                placeholderText: "Reservation number, source, or requester"
                text: root.searchText
                enabled: !root.isBusy
                onEditingFinished: root.searchTextUpdated(text)
            }

            AppControls.Label { text: "Status" }
            AppControls.ComboBox {
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

            AppControls.Label { text: "Item" }
            AppControls.ComboBox {
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

            AppControls.Label { text: "Storeroom" }
            AppControls.ComboBox {
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

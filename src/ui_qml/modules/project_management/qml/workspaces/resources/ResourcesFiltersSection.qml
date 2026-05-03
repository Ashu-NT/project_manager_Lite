import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme

Rectangle {
    id: root

    property var categoryOptions: []
    property string selectedActiveFilter: "all"
    property string selectedCategoryFilter: "all"
    property string searchText: ""
    property bool isBusy: false
    readonly property var activeOptions: [
        { "value": "all", "label": "All availability" },
        { "value": "active", "label": "Active" },
        { "value": "inactive", "label": "Inactive" }
    ]

    signal searchTextUpdated(string searchText)
    signal activeFilterUpdated(string activeValue)
    signal categoryFilterUpdated(string categoryValue)
    signal refreshRequested()
    signal createRequested()

    function indexForValue(options, targetValue) {
        for (var index = 0; index < options.length; index += 1) {
            if (String(options[index].value || "") === String(targetValue || "")) {
                return index
            }
        }
        return 0
    }

    radius: Theme.AppTheme.radiusLg
    color: Theme.AppTheme.surface
    border.color: Theme.AppTheme.border
    implicitHeight: controlsLayout.implicitHeight + (Theme.AppTheme.marginLg * 2)

    RowLayout {
        id: controlsLayout

        anchors.fill: parent
        anchors.margins: Theme.AppTheme.marginLg
        spacing: Theme.AppTheme.spacingMd

        TextField {
            Layout.fillWidth: true
            text: root.searchText
            placeholderText: "Search by name, role, worker type, category, or context"
            enabled: !root.isBusy
            onTextEdited: root.searchTextUpdated(text)
        }

        ComboBox {
            id: activeCombo

            Layout.preferredWidth: 180
            model: root.activeOptions
            textRole: "label"
            enabled: !root.isBusy
            currentIndex: root.indexForValue(root.activeOptions, root.selectedActiveFilter)

            onActivated: function(index) {
                var option = root.activeOptions[index]
                if (option) {
                    root.activeFilterUpdated(String(option.value || "all"))
                }
            }
        }

        ComboBox {
            id: categoryCombo

            Layout.preferredWidth: 220
            model: root.categoryOptions
            textRole: "label"
            enabled: !root.isBusy
            currentIndex: root.indexForValue(root.categoryOptions, root.selectedCategoryFilter)

            onActivated: function(index) {
                var option = root.categoryOptions[index]
                if (option) {
                    root.categoryFilterUpdated(String(option.value || "all"))
                }
            }
        }

        Button {
            text: "Refresh"
            enabled: !root.isBusy
            onClicked: root.refreshRequested()
        }

        AppControls.PrimaryButton {
            text: "New Resource"
            enabled: !root.isBusy
            onClicked: root.createRequested()
        }
    }
}

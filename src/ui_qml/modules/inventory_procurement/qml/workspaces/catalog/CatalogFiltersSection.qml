import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme

Rectangle {
    id: root

    property var activeOptions: []
    property var usageOptions: []
    property var categoryTypeOptions: []
    property var categoryOptions: []
    property string selectedActiveFilter: "all"
    property string selectedUsageFilter: "all"
    property string selectedCategoryTypeFilter: "all"
    property string selectedCategoryFilter: "all"
    property string searchText: ""
    property bool isBusy: false

    signal searchTextUpdated(string searchText)
    signal activeFilterUpdated(string activeValue)
    signal usageFilterUpdated(string usageValue)
    signal categoryTypeFilterUpdated(string categoryType)
    signal categoryFilterUpdated(string categoryCode)
    signal refreshRequested()
    signal createCategoryRequested()
    signal createItemRequested()

    radius: Theme.AppTheme.radiusLg
    color: Theme.AppTheme.surface
    border.color: Theme.AppTheme.border

    function indexForValue(options, targetValue) {
        for (var index = 0; index < options.length; index += 1) {
            if (String(options[index].value || "") === String(targetValue || "")) {
                return index
            }
        }
        return 0
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.AppTheme.marginLg
        spacing: Theme.AppTheme.spacingMd

        Label {
            Layout.fillWidth: true
            text: "Filter the shared inventory master, then open category or item workflows without leaving the catalog."
            color: Theme.AppTheme.textSecondary
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.smallSize
            wrapMode: Text.WordWrap
        }

        GridLayout {
            Layout.fillWidth: true
            columns: root.width > 1180 ? 5 : (root.width > 840 ? 3 : 1)
            columnSpacing: Theme.AppTheme.spacingMd
            rowSpacing: Theme.AppTheme.spacingSm

            TextField {
                id: searchField
                Layout.fillWidth: true
                placeholderText: "Search code, name, category, supplier, or notes"
                text: root.searchText
                enabled: !root.isBusy
                onEditingFinished: root.searchTextUpdated(text)
            }

            ComboBox {
                id: activeCombo
                Layout.fillWidth: true
                model: root.activeOptions
                textRole: "label"
                enabled: !root.isBusy
                onActivated: root.activeFilterUpdated(String((model[currentIndex] || { "value": "all" }).value || "all"))
                Component.onCompleted: currentIndex = root.indexForValue(root.activeOptions, root.selectedActiveFilter)
            }

            ComboBox {
                id: usageCombo
                Layout.fillWidth: true
                model: root.usageOptions
                textRole: "label"
                enabled: !root.isBusy
                onActivated: root.usageFilterUpdated(String((model[currentIndex] || { "value": "all" }).value || "all"))
                Component.onCompleted: currentIndex = root.indexForValue(root.usageOptions, root.selectedUsageFilter)
            }

            ComboBox {
                id: categoryTypeCombo
                Layout.fillWidth: true
                model: root.categoryTypeOptions
                textRole: "label"
                enabled: !root.isBusy
                onActivated: root.categoryTypeFilterUpdated(String((model[currentIndex] || { "value": "all" }).value || "all"))
                Component.onCompleted: currentIndex = root.indexForValue(root.categoryTypeOptions, root.selectedCategoryTypeFilter)
            }

            ComboBox {
                id: categoryCombo
                Layout.fillWidth: true
                model: root.categoryOptions
                textRole: "label"
                enabled: !root.isBusy
                onActivated: root.categoryFilterUpdated(String((model[currentIndex] || { "value": "all" }).value || "all"))
                Component.onCompleted: currentIndex = root.indexForValue(root.categoryOptions, root.selectedCategoryFilter)
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.AppTheme.spacingSm

            AppControls.PrimaryButton {
                text: "Refresh"
                enabled: !root.isBusy
                onClicked: root.refreshRequested()
            }

            AppControls.PrimaryButton {
                text: "New Category"
                enabled: !root.isBusy
                onClicked: root.createCategoryRequested()
            }

            AppControls.PrimaryButton {
                text: "New Item"
                enabled: !root.isBusy
                onClicked: root.createItemRequested()
            }

            Item {
                Layout.fillWidth: true
            }
        }
    }

    onSelectedActiveFilterChanged: activeCombo.currentIndex = root.indexForValue(root.activeOptions, root.selectedActiveFilter)
    onSelectedUsageFilterChanged: usageCombo.currentIndex = root.indexForValue(root.usageOptions, root.selectedUsageFilter)
    onSelectedCategoryTypeFilterChanged: categoryTypeCombo.currentIndex = root.indexForValue(root.categoryTypeOptions, root.selectedCategoryTypeFilter)
    onSelectedCategoryFilterChanged: categoryCombo.currentIndex = root.indexForValue(root.categoryOptions, root.selectedCategoryFilter)
}

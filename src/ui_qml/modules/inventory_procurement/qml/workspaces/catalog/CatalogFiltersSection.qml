import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme

Item {
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
        spacing: Theme.AppTheme.spacingMd

        AppControls.Label {
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

            AppControls.TextField {
                id: searchField
                Layout.fillWidth: true
                placeholderText: "Search code, name, category, supplier, or notes"
                text: root.searchText
                enabled: !root.isBusy
                onEditingFinished: root.searchTextUpdated(text)
            }

            AppControls.ComboBox {
                id: activeCombo
                Layout.fillWidth: true
                model: root.activeOptions
                textRole: "label"
                enabled: !root.isBusy
                onActivated: root.activeFilterUpdated(String((model[currentIndex] || { "value": "all" }).value || "all"))
                Component.onCompleted: currentIndex = root.indexForValue(root.activeOptions, root.selectedActiveFilter)
            }

            AppControls.ComboBox {
                id: usageCombo
                Layout.fillWidth: true
                model: root.usageOptions
                textRole: "label"
                enabled: !root.isBusy
                onActivated: root.usageFilterUpdated(String((model[currentIndex] || { "value": "all" }).value || "all"))
                Component.onCompleted: currentIndex = root.indexForValue(root.usageOptions, root.selectedUsageFilter)
            }

            AppControls.ComboBox {
                id: categoryTypeCombo
                Layout.fillWidth: true
                model: root.categoryTypeOptions
                textRole: "label"
                enabled: !root.isBusy
                onActivated: root.categoryTypeFilterUpdated(String((model[currentIndex] || { "value": "all" }).value || "all"))
                Component.onCompleted: currentIndex = root.indexForValue(root.categoryTypeOptions, root.selectedCategoryTypeFilter)
            }

            AppControls.ComboBox {
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
                iconName: "refresh"
                enabled: !root.isBusy
                onClicked: root.refreshRequested()
            }

            AppControls.PrimaryButton {
                text: "New Category"
                iconName: "add"
                enabled: !root.isBusy
                onClicked: root.createCategoryRequested()
            }

            AppControls.PrimaryButton {
                text: "New Item"
                iconName: "add"
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

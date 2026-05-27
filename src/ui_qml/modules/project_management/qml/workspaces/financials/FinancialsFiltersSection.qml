import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme

Item {
    id: root

    property var projectOptions: []
    property var costTypeOptions: []
    property string selectedProjectId: ""
    property string selectedCostType: "all"
    property string searchText: ""
    property bool isBusy: false

    signal projectUpdated(string projectId)
    signal costTypeUpdated(string costType)
    signal searchTextUpdated(string searchText)
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

    implicitHeight: controlsLayout.implicitHeight

    RowLayout {
        id: controlsLayout

        anchors.fill: parent
        spacing: Theme.AppTheme.spacingMd

        AppControls.ComboBox {
            id: projectCombo

            Layout.preferredWidth: 240
            model: root.projectOptions
            textRole: "label"
            enabled: !root.isBusy
            currentIndex: root.indexForValue(root.projectOptions, root.selectedProjectId)

            onActivated: function(index) {
                var option = root.projectOptions[index]
                if (option) {
                    root.projectUpdated(String(option.value || ""))
                }
            }
        }

        AppControls.TextField {
            Layout.fillWidth: true
            text: root.searchText
            placeholderText: "Search by description, task, category, or currency"
            enabled: !root.isBusy
            onTextEdited: root.searchTextUpdated(text)
        }

        AppControls.ComboBox {
            id: costTypeCombo

            Layout.preferredWidth: 220
            model: root.costTypeOptions
            textRole: "label"
            enabled: !root.isBusy
            currentIndex: root.indexForValue(root.costTypeOptions, root.selectedCostType)

            onActivated: function(index) {
                var option = root.costTypeOptions[index]
                if (option) {
                    root.costTypeUpdated(String(option.value || "all"))
                }
            }
        }

        AppControls.SecondaryButton {
            text: "Refresh"
            iconName: "refresh"
            enabled: !root.isBusy
            onClicked: root.refreshRequested()
        }

        AppControls.PrimaryButton {
            text: "New Cost"
            iconName: "add"
            enabled: !root.isBusy && root.selectedProjectId.length > 0
            onClicked: root.createRequested()
        }
    }
}

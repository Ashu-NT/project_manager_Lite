import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Theme 1.0 as Theme
import App.Controls 1.0 as AppControls

Item {
    id: root

    property var intakeStatusOptions: []
    property var scenarioOptions: []
    property string selectedIntakeStatusFilter: "all"
    property string selectedScenarioId: ""
    property string selectedBaseScenarioId: ""
    property string selectedCompareScenarioId: ""
    property bool isBusy: false

    signal intakeStatusFilterChanged(string value)
    signal scenarioChanged(string value)
    signal compareBaseChanged(string value)
    signal compareScenarioChanged(string value)
    signal refreshRequested()

    function indexForValue(options, targetValue) {
        for (var index = 0; index < options.length; index += 1) {
            if (String(options[index].value || "") === String(targetValue || "")) {
                return index
            }
        }
        return 0
    }

    implicitHeight: toolbarLayout.implicitHeight

    GridLayout {
        id: toolbarLayout

        anchors.fill: parent
        columns: root.width > 1200 ? 5 : 2
        columnSpacing: Theme.AppTheme.spacingMd
        rowSpacing: Theme.AppTheme.spacingMd

        AppControls.ComboBox {
            Layout.fillWidth: true
            model: root.intakeStatusOptions
            textRole: "label"
            enabled: !root.isBusy
            currentIndex: root.indexForValue(root.intakeStatusOptions, root.selectedIntakeStatusFilter)

            onActivated: function(index) {
                var option = root.intakeStatusOptions[index]
                if (option) {
                    root.intakeStatusFilterChanged(String(option.value || "all"))
                }
            }
        }

        AppControls.ComboBox {
            Layout.fillWidth: true
            model: root.scenarioOptions
            textRole: "label"
            enabled: !root.isBusy
            currentIndex: root.indexForValue(root.scenarioOptions, root.selectedScenarioId)

            onActivated: function(index) {
                var option = root.scenarioOptions[index]
                if (option) {
                    root.scenarioChanged(String(option.value || ""))
                }
            }
        }

        AppControls.ComboBox {
            Layout.fillWidth: true
            model: root.scenarioOptions
            textRole: "label"
            enabled: !root.isBusy
            currentIndex: root.indexForValue(root.scenarioOptions, root.selectedBaseScenarioId)

            onActivated: function(index) {
                var option = root.scenarioOptions[index]
                if (option) {
                    root.compareBaseChanged(String(option.value || ""))
                }
            }
        }

        AppControls.ComboBox {
            Layout.fillWidth: true
            model: root.scenarioOptions
            textRole: "label"
            enabled: !root.isBusy
            currentIndex: root.indexForValue(root.scenarioOptions, root.selectedCompareScenarioId)

            onActivated: function(index) {
                var option = root.scenarioOptions[index]
                if (option) {
                    root.compareScenarioChanged(String(option.value || ""))
                }
            }
        }

        Button {
            Layout.fillWidth: true
            text: "Refresh"
            enabled: !root.isBusy
            onClicked: root.refreshRequested()
        }
    }
}

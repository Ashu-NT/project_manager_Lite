import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Theme 1.0 as Theme

Rectangle {
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

    radius: Theme.AppTheme.radiusLg
    color: Theme.AppTheme.surface
    border.color: Theme.AppTheme.border
    implicitHeight: toolbarLayout.implicitHeight + (Theme.AppTheme.marginLg * 2)

    GridLayout {
        id: toolbarLayout

        anchors.fill: parent
        anchors.margins: Theme.AppTheme.marginLg
        columns: root.width > 1200 ? 5 : 2
        columnSpacing: Theme.AppTheme.spacingMd
        rowSpacing: Theme.AppTheme.spacingMd

        ComboBox {
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

        ComboBox {
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

        ComboBox {
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

        ComboBox {
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

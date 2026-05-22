pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme

Rectangle {
    id: root

    property var    scenarioOptions:             []
    property string selectedScenarioId:          ""
    property string selectedBaseScenarioId:      ""
    property string selectedCompareScenarioId:   ""
    property bool   isBusy:                      false

    signal scenarioSelected(string scenarioId)
    signal compareBaseSelected(string scenarioId)
    signal compareScenarioSelected(string scenarioId)
    signal refreshRequested()
    signal rebalanceRequested()
    signal compareRequested()
    signal exportRequested()

    function _indexForValue(options, value) {
        const opts = options || []
        for (let i = 0; i < opts.length; i += 1) {
            if (String(opts[i].value || "") === String(value || "")) {
                return i
            }
        }
        return opts.length > 0 ? 0 : -1
    }

    implicitHeight: Theme.AppTheme.toolbarHeight + 2
    color: Theme.AppTheme.surfaceRaised
    radius: Theme.AppTheme.radiusMd

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: Theme.AppTheme.marginMd
        anchors.rightMargin: Theme.AppTheme.marginMd
        spacing: Theme.AppTheme.spacingSm

        Label {
            text: "Scenario"
            color: Theme.AppTheme.textMuted
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.captionSize
        }

        ComboBox {
            Layout.preferredWidth: 190
            model: root.scenarioOptions
            textRole: "label"
            enabled: !root.isBusy
            currentIndex: root._indexForValue(root.scenarioOptions, root.selectedScenarioId)

            onActivated: function(idx) {
                const opt = root.scenarioOptions[idx]
                if (opt) {
                    root.scenarioSelected(String(opt.value || ""))
                }
            }
        }

        Rectangle {
            width: 1
            height: Theme.AppTheme.toolbarHeight - 16
            color: Theme.AppTheme.divider
            opacity: 0.6
        }

        Label {
            text: "Base"
            color: Theme.AppTheme.textMuted
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.captionSize
        }

        ComboBox {
            Layout.preferredWidth: 160
            model: root.scenarioOptions
            textRole: "label"
            enabled: !root.isBusy && root.scenarioOptions.length > 1
            currentIndex: root._indexForValue(root.scenarioOptions, root.selectedBaseScenarioId)

            onActivated: function(idx) {
                const opt = root.scenarioOptions[idx]
                if (opt) {
                    root.compareBaseSelected(String(opt.value || ""))
                }
            }
        }

        Label {
            text: "vs"
            color: Theme.AppTheme.textMuted
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.captionSize
        }

        ComboBox {
            Layout.preferredWidth: 160
            model: root.scenarioOptions
            textRole: "label"
            enabled: !root.isBusy && root.scenarioOptions.length > 1
            currentIndex: root._indexForValue(root.scenarioOptions, root.selectedCompareScenarioId)

            onActivated: function(idx) {
                const opt = root.scenarioOptions[idx]
                if (opt) {
                    root.compareScenarioSelected(String(opt.value || ""))
                }
            }
        }

        Item { Layout.fillWidth: true }

        AppControls.SecondaryButton {
            text: "Compare"
            iconName: "register"
            enabled: !root.isBusy && root.scenarioOptions.length > 1
            onClicked: root.compareRequested()
        }

        AppControls.SecondaryButton {
            text: "Export"
            iconName: "export"
            enabled: !root.isBusy
            onClicked: root.exportRequested()
        }

        AppControls.PrimaryButton {
            text: "Rebalance"
            iconName: "approve"
            enabled: !root.isBusy && String(root.selectedScenarioId || "").length > 0
            onClicked: root.rebalanceRequested()
        }
    }
}

pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme
import App.Widgets 1.0 as AppWidgets

Rectangle {
    id: root

    property var    scenarioOptions:             []
    property string selectedScenarioId:          ""
    property string selectedBaseScenarioId:      ""
    property string selectedCompareScenarioId:   ""
    property var    evaluationModel:              ({ "fields": [] })
    property var    comparisonModel:              ({ "fields": [] })
    property bool   isBusy:                      false

    signal scenarioSelected(string scenarioId)
    signal compareBaseSelected(string scenarioId)
    signal compareScenarioSelected(string scenarioId)
    signal refreshRequested()

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

        AppControls.Label {
            text: "Scenario"
            color: Theme.AppTheme.textMuted
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.captionSize
        }

        AppControls.ComboBox {
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

        AppControls.Label {
            text: "Base"
            color: Theme.AppTheme.textMuted
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.captionSize
        }

        AppControls.ComboBox {
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

        AppControls.Label {
            text: "vs"
            color: Theme.AppTheme.textMuted
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.captionSize
        }

        AppControls.ComboBox {
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
            id: compareButton
            text: "Compare"
            iconName: "register"
            enabled: !root.isBusy && root.scenarioOptions.length > 1
            onClicked: analysisPopup.open()
        }

    }

    AppWidgets.AnchoredPopup {
        id: analysisPopup
        anchorItem: compareButton
        width: Math.min(560, root.width)
        height: Math.min(480, analysisContent.implicitHeight + Theme.AppTheme.marginMd * 2)
        padding: Theme.AppTheme.marginMd
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

        background: Rectangle {
            radius: Theme.AppTheme.radiusLg
            color: Theme.AppTheme.surfaceRaised
            border.color: Theme.AppTheme.divider
            border.width: 1
        }

        contentItem: Flickable {
            clip: true
            contentWidth: width
            contentHeight: analysisContent.implicitHeight
            boundsBehavior: Flickable.StopAtBounds
            ScrollBar.vertical: ScrollBar { }

            ColumnLayout {
                id: analysisContent
                width: parent.width
                spacing: Theme.AppTheme.spacingLg

                PortfolioSummaryCard {
                    Layout.fillWidth: true
                    summaryModel: root.evaluationModel
                }

                PortfolioSummaryCard {
                    Layout.fillWidth: true
                    summaryModel: root.comparisonModel
                }
            }
        }
    }
}

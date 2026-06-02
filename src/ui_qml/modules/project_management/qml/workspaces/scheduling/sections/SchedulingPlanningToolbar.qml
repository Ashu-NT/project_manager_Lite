pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme

Rectangle {
    id: root

    property var projectOptions: []
    property var baselineOptions: []
    property var calendarOptions: []
    property string selectedProjectId: ""
    property string selectedBaselineId: ""
    property string selectedCalendarId: "default"
    property bool isBusy: false

    signal projectSelected(string projectId)
    signal baselineSelected(string baselineId)
    signal calendarSelected(string calendarId)
    signal saveBaselineRequested()
    signal recalculateRequested()

    function _indexForValue(options, value) {
        const optionList = options || []
        for (let i = 0; i < optionList.length; i += 1) {
            if (String(optionList[i].value || "") === String(value || "")) {
                return i
            }
        }
        return optionList.length > 0 ? 0 : -1
    }

    implicitHeight: Theme.AppTheme.toolbarHeight + 2
    color: Theme.AppTheme.surfaceRaised
    radius: Theme.AppTheme.radiusMd

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: Theme.AppTheme.marginMd
        anchors.rightMargin: Theme.AppTheme.marginMd
        spacing: Theme.AppTheme.spacingSm

        AppControls.ComboBox {
            Layout.preferredWidth: 210
            model: root.projectOptions
            textRole: "label"
            enabled: !root.isBusy
            currentIndex: root._indexForValue(root.projectOptions, root.selectedProjectId)

            onActivated: function(index) {
                const option = root.projectOptions[index]
                if (option) {
                    root.projectSelected(String(option.value || ""))
                }
            }
        }

        AppControls.ComboBox {
            Layout.preferredWidth: 190
            model: root.baselineOptions
            textRole: "label"
            enabled: !root.isBusy && root.baselineOptions.length > 0
            currentIndex: root._indexForValue(root.baselineOptions, root.selectedBaselineId)

            onActivated: function(index) {
                const option = root.baselineOptions[index]
                if (option) {
                    root.baselineSelected(String(option.value || ""))
                }
            }
        }

        AppControls.ComboBox {
            Layout.preferredWidth: 170
            model: root.calendarOptions
            textRole: "label"
            enabled: !root.isBusy && root.calendarOptions.length > 0
            currentIndex: root._indexForValue(root.calendarOptions, root.selectedCalendarId)

            onActivated: function(index) {
                const option = root.calendarOptions[index]
                if (option) {
                    root.calendarSelected(String(option.value || ""))
                }
            }
        }

        Item { Layout.fillWidth: true }

        AppControls.SecondaryButton {
            text: "Save Baseline"
            iconName: "register"
            enabled: !root.isBusy && String(root.selectedProjectId || "").length > 0
            onClicked: root.saveBaselineRequested()
        }

        AppControls.PrimaryButton {
            text: "Recalculate"
            iconName: "approve"
            enabled: !root.isBusy && String(root.selectedProjectId || "").length > 0
            onClicked: root.recalculateRequested()
        }
    }
}

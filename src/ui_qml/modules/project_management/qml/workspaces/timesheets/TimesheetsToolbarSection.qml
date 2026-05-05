import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Theme 1.0 as Theme

Rectangle {
    id: root

    property var projectOptions: []
    property var assignmentOptions: []
    property var periodOptions: []
    property var queueStatusOptions: []
    property string selectedProjectId: "all"
    property string selectedAssignmentId: ""
    property string selectedPeriodStart: ""
    property string selectedQueueStatus: "SUBMITTED"
    property bool isBusy: false

    signal projectChanged(string value)
    signal assignmentChanged(string value)
    signal periodChanged(string value)
    signal queueStatusChanged(string value)
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
            model: root.projectOptions
            textRole: "label"
            enabled: !root.isBusy
            currentIndex: root.indexForValue(root.projectOptions, root.selectedProjectId)

            onActivated: function(index) {
                var option = root.projectOptions[index]
                if (option) {
                    root.projectChanged(String(option.value || "all"))
                }
            }
        }

        ComboBox {
            Layout.fillWidth: true
            model: root.assignmentOptions
            textRole: "label"
            enabled: !root.isBusy
            currentIndex: root.indexForValue(root.assignmentOptions, root.selectedAssignmentId)

            onActivated: function(index) {
                var option = root.assignmentOptions[index]
                if (option) {
                    root.assignmentChanged(String(option.value || ""))
                }
            }
        }

        ComboBox {
            Layout.fillWidth: true
            model: root.periodOptions
            textRole: "label"
            enabled: !root.isBusy
            currentIndex: root.indexForValue(root.periodOptions, root.selectedPeriodStart)

            onActivated: function(index) {
                var option = root.periodOptions[index]
                if (option) {
                    root.periodChanged(String(option.value || ""))
                }
            }
        }

        ComboBox {
            Layout.fillWidth: true
            model: root.queueStatusOptions
            textRole: "label"
            enabled: !root.isBusy
            currentIndex: root.indexForValue(root.queueStatusOptions, root.selectedQueueStatus)

            onActivated: function(index) {
                var option = root.queueStatusOptions[index]
                if (option) {
                    root.queueStatusChanged(String(option.value || "SUBMITTED"))
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

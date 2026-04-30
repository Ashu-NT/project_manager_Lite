import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme

Rectangle {
    id: root

    property var projectOptions: []
    property string selectedProjectId: ""
    property var statusOptions: []
    property string selectedStatusFilter: "all"
    property string searchText: ""
    property bool isBusy: false

    signal projectSelected(string projectId)
    signal searchTextUpdated(string searchText)
    signal statusFilterUpdated(string statusValue)
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

        ComboBox {
            id: projectCombo
            Layout.preferredWidth: 240
            model: root.projectOptions
            textRole: "label"
            enabled: !root.isBusy
            currentIndex: root.indexForValue(root.projectOptions, root.selectedProjectId)

            onActivated: function(index) {
                var option = root.projectOptions[index]
                if (option) {
                    root.projectSelected(String(option.value || ""))
                }
            }
        }

        TextField {
            Layout.fillWidth: true
            text: root.searchText
            placeholderText: "Search by task, project, or description"
            enabled: !root.isBusy
            onTextEdited: root.searchTextUpdated(text)
        }

        ComboBox {
            id: statusCombo
            Layout.preferredWidth: 220
            model: root.statusOptions
            textRole: "label"
            enabled: !root.isBusy
            currentIndex: root.indexForValue(root.statusOptions, root.selectedStatusFilter)

            onActivated: function(index) {
                var option = root.statusOptions[index]
                if (option) {
                    root.statusFilterUpdated(String(option.value || "all"))
                }
            }
        }

        Button {
            text: "Refresh"
            enabled: !root.isBusy
            onClicked: root.refreshRequested()
        }

        AppControls.PrimaryButton {
            text: "New Task"
            enabled: !root.isBusy
            onClicked: root.createRequested()
        }
    }
}

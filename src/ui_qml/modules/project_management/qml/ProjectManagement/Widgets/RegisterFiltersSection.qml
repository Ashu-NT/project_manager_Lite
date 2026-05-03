import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme

Rectangle {
    id: root

    property var projectOptions: []
    property var typeOptions: []
    property var statusOptions: []
    property var severityOptions: []
    property string selectedProjectId: "all"
    property string selectedTypeFilter: "all"
    property string selectedStatusFilter: "all"
    property string selectedSeverityFilter: "all"
    property string searchText: ""
    property bool isBusy: false
    property bool showTypeFilter: true
    property string createButtonLabel: "New Entry"

    signal projectChanged(string projectId)
    signal typeChanged(string typeValue)
    signal statusChanged(string statusValue)
    signal severityChanged(string severityValue)
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

    radius: Theme.AppTheme.radiusLg
    color: Theme.AppTheme.surface
    border.color: Theme.AppTheme.border
    implicitHeight: controlsLayout.implicitHeight + (Theme.AppTheme.marginLg * 2)

    ColumnLayout {
        id: controlsLayout

        anchors.fill: parent
        anchors.margins: Theme.AppTheme.marginLg
        spacing: Theme.AppTheme.spacingMd

        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.AppTheme.spacingMd

            TextField {
                Layout.fillWidth: true
                text: root.searchText
                placeholderText: "Search by title, owner, project, impact, or response plan"
                enabled: !root.isBusy
                onTextEdited: root.searchTextUpdated(text)
            }

            Button {
                text: "Refresh"
                enabled: !root.isBusy
                onClicked: root.refreshRequested()
            }

            AppControls.PrimaryButton {
                text: root.createButtonLabel
                enabled: !root.isBusy
                onClicked: root.createRequested()
            }
        }

        GridLayout {
            Layout.fillWidth: true
            columns: root.width > 780 ? (root.showTypeFilter ? 4 : 3) : 2
            columnSpacing: Theme.AppTheme.spacingMd
            rowSpacing: Theme.AppTheme.spacingSm

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
                visible: root.showTypeFilter
                Layout.fillWidth: true
                model: root.typeOptions
                textRole: "label"
                enabled: !root.isBusy
                currentIndex: root.indexForValue(root.typeOptions, root.selectedTypeFilter)

                onActivated: function(index) {
                    var option = root.typeOptions[index]
                    if (option) {
                        root.typeChanged(String(option.value || "all"))
                    }
                }
            }

            ComboBox {
                Layout.fillWidth: true
                model: root.statusOptions
                textRole: "label"
                enabled: !root.isBusy
                currentIndex: root.indexForValue(root.statusOptions, root.selectedStatusFilter)

                onActivated: function(index) {
                    var option = root.statusOptions[index]
                    if (option) {
                        root.statusChanged(String(option.value || "all"))
                    }
                }
            }

            ComboBox {
                Layout.fillWidth: true
                model: root.severityOptions
                textRole: "label"
                enabled: !root.isBusy
                currentIndex: root.indexForValue(root.severityOptions, root.selectedSeverityFilter)

                onActivated: function(index) {
                    var option = root.severityOptions[index]
                    if (option) {
                        root.severityChanged(String(option.value || "all"))
                    }
                }
            }
        }
    }
}

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme

Item {
    id: root

    property var projectOptions: []
    property string selectedProjectId: ""
    property var statusOptions: []
    property var priorityOptions: []
    property var scheduleOptions: []
    property var taskViewOptions: []
    property string selectedStatusFilter: "all"
    property string selectedPriorityFilter: "all"
    property string selectedScheduleFilter: "all"
    property string selectedTaskViewName: ""
    property string searchText: ""
    property bool isBusy: false

    signal projectSelected(string projectId)
    signal searchTextUpdated(string searchText)
    signal statusFilterUpdated(string statusValue)
    signal priorityFilterUpdated(string priorityValue)
    signal scheduleFilterUpdated(string scheduleValue)
    signal taskViewSelected(string viewName)
    signal refreshRequested()
    signal clearRequested()
    signal applyTaskViewRequested()
    signal saveTaskViewRequested(string viewName)
    signal deleteTaskViewRequested()
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

    ColumnLayout {
        id: controlsLayout

        anchors.fill: parent
        spacing: Theme.AppTheme.spacingMd

        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.AppTheme.spacingMd

            ComboBox {
                id: projectCombo
                Layout.preferredWidth: 220
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
                placeholderText: "Task name/desc | advanced: status:done priority>=70 progress<100"
                enabled: !root.isBusy
                onTextEdited: root.searchTextUpdated(text)
            }

            ComboBox {
                Layout.preferredWidth: 180
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

            ComboBox {
                Layout.preferredWidth: 180
                model: root.priorityOptions
                textRole: "label"
                enabled: !root.isBusy
                currentIndex: root.indexForValue(root.priorityOptions, root.selectedPriorityFilter)

                onActivated: function(index) {
                    var option = root.priorityOptions[index]
                    if (option) {
                        root.priorityFilterUpdated(String(option.value || "all"))
                    }
                }
            }

            ComboBox {
                Layout.preferredWidth: 180
                model: root.scheduleOptions
                textRole: "label"
                enabled: !root.isBusy
                currentIndex: root.indexForValue(root.scheduleOptions, root.selectedScheduleFilter)

                onActivated: function(index) {
                    var option = root.scheduleOptions[index]
                    if (option) {
                        root.scheduleFilterUpdated(String(option.value || "all"))
                    }
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.AppTheme.spacingMd

            ComboBox {
                Layout.preferredWidth: 240
                model: root.taskViewOptions
                textRole: "label"
                enabled: !root.isBusy
                currentIndex: root.indexForValue(root.taskViewOptions, root.selectedTaskViewName)

                onActivated: function(index) {
                    var option = root.taskViewOptions[index]
                    if (option) {
                        root.taskViewSelected(String(option.value || ""))
                    }
                }
            }

            Button {
                text: "Apply View"
                enabled: !root.isBusy
                onClicked: root.applyTaskViewRequested()
            }

            Button {
                text: "Save View"
                enabled: !root.isBusy
                onClicked: saveViewDialog.open()
            }

            Button {
                text: "Delete View"
                enabled: !root.isBusy && !!root.selectedTaskViewName
                onClicked: root.deleteTaskViewRequested()
            }

            Item {
                Layout.fillWidth: true
            }

            Button {
                text: "Clear Filters"
                enabled: !root.isBusy
                onClicked: root.clearRequested()
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

    Dialog {
        id: saveViewDialog

        modal: true
        title: "Save Task View"
        anchors.centerIn: Overlay.overlay
        standardButtons: Dialog.Ok | Dialog.Cancel

        onAboutToShow: viewNameField.text = root.selectedTaskViewName

        onAccepted: {
            var name = String(viewNameField.text || "").trim()
            if (name.length > 0) {
                root.saveTaskViewRequested(name)
            }
        }

        contentItem: ColumnLayout {
            width: 320
            spacing: Theme.AppTheme.spacingSm

            Label {
                text: "View name"
            }

            TextField {
                id: viewNameField

                Layout.fillWidth: true
                placeholderText: "High Focus"
                selectByMouse: true
            }
        }
    }
}

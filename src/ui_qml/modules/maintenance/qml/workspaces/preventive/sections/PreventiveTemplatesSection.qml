import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme
import Maintenance.Widgets 1.0 as MaintenanceWidgets

ColumnLayout {
    id: root

    property var templateLibraryState: ({
        "activeOptions": [],
        "maintenanceTypeOptions": [],
        "statusOptions": [],
        "selectedActiveFilter": "all",
        "selectedMaintenanceTypeFilter": "all",
        "selectedStatusFilter": "all",
        "searchText": "",
        "templates": { "title": "", "subtitle": "", "emptyState": "", "items": [] },
        "selectedTaskTemplateId": "",
        "selectedTaskTemplate": { "id": "", "title": "", "statusLabel": "", "subtitle": "", "description": "", "emptyState": "", "fields": [], "state": {} },
        "steps": { "title": "", "subtitle": "", "emptyState": "", "items": [] },
        "selectedTaskStepId": "",
        "selectedTaskStep": { "id": "", "title": "", "statusLabel": "", "subtitle": "", "description": "", "emptyState": "", "fields": [], "state": {} }
    })
    property bool isBusy: false

    signal activeFilterUpdated(string activeFilter)
    signal maintenanceTypeFilterUpdated(string maintenanceType)
    signal statusFilterUpdated(string templateStatus)
    signal searchTextUpdated(string searchText)
    signal refreshRequested()
    signal createTaskTemplateRequested()
    signal taskTemplateSelected(string taskTemplateId)
    signal editTaskTemplateRequested(var taskTemplateData)
    signal toggleTaskTemplateRequested(var taskTemplateData)
    signal createTaskStepRequested(string taskTemplateId)
    signal taskStepSelected(string taskStepTemplateId)
    signal editTaskStepRequested(var taskStepData)
    signal toggleTaskStepRequested(var taskStepData)

    function indexOfValue(options, value) {
        for (let index = 0; index < options.length; index += 1) {
            if (String(options[index].value || "") === String(value || "")) {
                return index
            }
        }
        return 0
    }

    spacing: 12

    Rectangle {
        Layout.fillWidth: true
        radius: Theme.AppTheme.radiusLg
        color: Theme.AppTheme.surface
        implicitHeight: filtersLayout.implicitHeight + (Theme.AppTheme.marginLg * 2)

        GridLayout {
            id: filtersLayout

            anchors.fill: parent
            anchors.margins: Theme.AppTheme.marginLg
            columns: root.width > 980 ? 4 : 2
            rowSpacing: Theme.AppTheme.spacingSm
            columnSpacing: Theme.AppTheme.spacingSm

            AppControls.ComboBox {
                Layout.fillWidth: true
                model: root.templateLibraryState.activeOptions || []
                textRole: "label"
                currentIndex: root.indexOfValue(model, root.templateLibraryState.selectedActiveFilter)
                onActivated: function(index) {
                    const row = model[index]
                    root.activeFilterUpdated(row ? String(row.value || "all") : "all")
                }
            }

            AppControls.ComboBox {
                Layout.fillWidth: true
                model: root.templateLibraryState.maintenanceTypeOptions || []
                textRole: "label"
                currentIndex: root.indexOfValue(model, root.templateLibraryState.selectedMaintenanceTypeFilter)
                onActivated: function(index) {
                    const row = model[index]
                    root.maintenanceTypeFilterUpdated(row ? String(row.value || "all") : "all")
                }
            }

            AppControls.ComboBox {
                Layout.fillWidth: true
                model: root.templateLibraryState.statusOptions || []
                textRole: "label"
                currentIndex: root.indexOfValue(model, root.templateLibraryState.selectedStatusFilter)
                onActivated: function(index) {
                    const row = model[index]
                    root.statusFilterUpdated(row ? String(row.value || "all") : "all")
                }
            }

            AppControls.TextField {
                Layout.fillWidth: true
                text: root.templateLibraryState.searchText || ""
                placeholderText: "Template code, name, skill, or description"
                onEditingFinished: root.searchTextUpdated(text)
            }

            RowLayout {
                Layout.columnSpan: root.width > 980 ? 4 : 2
                Layout.fillWidth: true
                spacing: Theme.AppTheme.spacingSm

                AppControls.PrimaryButton {
                    text: "Refresh"
                    iconName: "refresh"
                    enabled: !root.isBusy
                    onClicked: root.refreshRequested()
                }

                AppControls.PrimaryButton {
                    text: "New Template"
                    iconName: "add"
                    enabled: !root.isBusy
                    onClicked: root.createTaskTemplateRequested()
                }

                Item { Layout.fillWidth: true }

                AppControls.PrimaryButton {
                    text: "New Step"
                    iconName: "add"
                    enabled: !root.isBusy && String(root.templateLibraryState.selectedTaskTemplateId || "").length > 0
                    onClicked: root.createTaskStepRequested(String(root.templateLibraryState.selectedTaskTemplateId || ""))
                }
            }
        }
    }

    GridLayout {
        Layout.fillWidth: true
        columns: root.width > 1180 ? 2 : 1
        columnSpacing: 12
        rowSpacing: 12

        MaintenanceWidgets.RecordListCard {
            Layout.fillWidth: true
            Layout.alignment: Qt.AlignTop
            title: root.templateLibraryState.templates.title || "Task Templates"
            subtitle: root.templateLibraryState.templates.subtitle || ""
            emptyState: root.templateLibraryState.templates.emptyState || ""
            items: root.templateLibraryState.templates.items || []
            selectedItemId: root.templateLibraryState.selectedTaskTemplateId || ""
            primaryActionLabel: "Edit"
            primaryActionIcon: "edit"
            secondaryActionLabel: "Toggle Active"
            secondaryActionIcon: "workflow"
            actionsEnabled: !root.isBusy

            onItemSelected: function(taskTemplateId) {
                root.taskTemplateSelected(taskTemplateId)
            }

            onPrimaryActionRequested: function(taskTemplateData) {
                root.editTaskTemplateRequested(taskTemplateData)
            }

            onSecondaryActionRequested: function(taskTemplateData) {
                root.toggleTaskTemplateRequested(taskTemplateData)
            }
        }

        PreventiveDetailSection {
            Layout.fillWidth: true
            Layout.alignment: Qt.AlignTop
            emptyTitle: "No task template selected"
            primaryActionLabel: "Edit"
            secondaryActionLabel: "Toggle Active"
            detailModel: root.templateLibraryState.selectedTaskTemplate || ({})
            isBusy: root.isBusy

            onPrimaryActionRequested: root.editTaskTemplateRequested(detailModel)
            onSecondaryActionRequested: root.toggleTaskTemplateRequested(detailModel)
        }
    }

    GridLayout {
        Layout.fillWidth: true
        columns: root.width > 1180 ? 2 : 1
        columnSpacing: 12
        rowSpacing: 12

        MaintenanceWidgets.RecordListCard {
            Layout.fillWidth: true
            Layout.alignment: Qt.AlignTop
            title: root.templateLibraryState.steps.title || "Task Steps"
            subtitle: root.templateLibraryState.steps.subtitle || ""
            emptyState: root.templateLibraryState.steps.emptyState || ""
            items: root.templateLibraryState.steps.items || []
            selectedItemId: root.templateLibraryState.selectedTaskStepId || ""
            primaryActionLabel: "Edit"
            primaryActionIcon: "edit"
            secondaryActionLabel: "Toggle Active"
            secondaryActionIcon: "workflow"
            actionsEnabled: !root.isBusy

            onItemSelected: function(taskStepTemplateId) {
                root.taskStepSelected(taskStepTemplateId)
            }

            onPrimaryActionRequested: function(taskStepData) {
                root.editTaskStepRequested(taskStepData)
            }

            onSecondaryActionRequested: function(taskStepData) {
                root.toggleTaskStepRequested(taskStepData)
            }
        }

        PreventiveDetailSection {
            Layout.fillWidth: true
            Layout.alignment: Qt.AlignTop
            emptyTitle: "No task step selected"
            primaryActionLabel: "Edit"
            secondaryActionLabel: "Toggle Active"
            detailModel: root.templateLibraryState.selectedTaskStep || ({})
            isBusy: root.isBusy

            onPrimaryActionRequested: root.editTaskStepRequested(detailModel)
            onSecondaryActionRequested: root.toggleTaskStepRequested(detailModel)
        }
    }
}

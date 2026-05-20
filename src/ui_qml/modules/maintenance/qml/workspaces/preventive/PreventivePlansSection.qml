import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme
import Maintenance.Widgets 1.0 as MaintenanceWidgets

ColumnLayout {
    id: root

    property var planLibraryState: ({
        "siteOptions": [],
        "assetOptions": [],
        "systemOptions": [],
        "activeOptions": [],
        "statusOptions": [],
        "planTypeOptions": [],
        "triggerModeOptions": [],
        "selectedSiteFilter": "all",
        "selectedAssetFilter": "all",
        "selectedSystemFilter": "all",
        "selectedActiveFilter": "all",
        "selectedStatusFilter": "all",
        "selectedPlanTypeFilter": "all",
        "selectedTriggerModeFilter": "all",
        "searchText": "",
        "plans": { "title": "", "subtitle": "", "emptyState": "", "items": [] },
        "selectedPlanId": "",
        "selectedPlan": { "id": "", "title": "", "statusLabel": "", "subtitle": "", "description": "", "emptyState": "", "fields": [], "state": {} },
        "planTasks": { "title": "", "subtitle": "", "emptyState": "", "items": [] },
        "selectedPlanTaskId": "",
        "selectedPlanTask": { "id": "", "title": "", "statusLabel": "", "subtitle": "", "description": "", "emptyState": "", "fields": [], "state": {} }
    })
    property bool isBusy: false

    signal siteFilterUpdated(string siteId)
    signal assetFilterUpdated(string assetId)
    signal systemFilterUpdated(string systemId)
    signal activeFilterUpdated(string activeFilter)
    signal statusFilterUpdated(string status)
    signal planTypeFilterUpdated(string planType)
    signal triggerModeFilterUpdated(string triggerMode)
    signal searchTextUpdated(string searchText)
    signal refreshRequested()
    signal createPlanRequested()
    signal planSelected(string planId)
    signal editPlanRequested(var planData)
    signal togglePlanRequested(var planData)
    signal createPlanTaskRequested(string planId)
    signal planTaskSelected(string planTaskId)
    signal editPlanTaskRequested(var planTaskData)

    function indexOfValue(options, value) {
        for (let index = 0; index < options.length; index += 1) {
            if (String(options[index].value || "") === String(value || "")) {
                return index
            }
        }
        return 0
    }

    function rowState(rowData) {
        return rowData && rowData.state ? rowData.state : (rowData || {})
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
            columns: root.width > 1180 ? 4 : 2
            rowSpacing: Theme.AppTheme.spacingSm
            columnSpacing: Theme.AppTheme.spacingSm

            ComboBox {
                Layout.fillWidth: true
                model: root.planLibraryState.siteOptions || []
                textRole: "label"
                currentIndex: root.indexOfValue(model, root.planLibraryState.selectedSiteFilter)
                onActivated: function(index) {
                    const row = model[index]
                    root.siteFilterUpdated(row ? String(row.value || "all") : "all")
                }
            }

            ComboBox {
                Layout.fillWidth: true
                model: root.planLibraryState.assetOptions || []
                textRole: "label"
                currentIndex: root.indexOfValue(model, root.planLibraryState.selectedAssetFilter)
                onActivated: function(index) {
                    const row = model[index]
                    root.assetFilterUpdated(row ? String(row.value || "all") : "all")
                }
            }

            ComboBox {
                Layout.fillWidth: true
                model: root.planLibraryState.systemOptions || []
                textRole: "label"
                currentIndex: root.indexOfValue(model, root.planLibraryState.selectedSystemFilter)
                onActivated: function(index) {
                    const row = model[index]
                    root.systemFilterUpdated(row ? String(row.value || "all") : "all")
                }
            }

            ComboBox {
                Layout.fillWidth: true
                model: root.planLibraryState.activeOptions || []
                textRole: "label"
                currentIndex: root.indexOfValue(model, root.planLibraryState.selectedActiveFilter)
                onActivated: function(index) {
                    const row = model[index]
                    root.activeFilterUpdated(row ? String(row.value || "all") : "all")
                }
            }

            ComboBox {
                Layout.fillWidth: true
                model: root.planLibraryState.statusOptions || []
                textRole: "label"
                currentIndex: root.indexOfValue(model, root.planLibraryState.selectedStatusFilter)
                onActivated: function(index) {
                    const row = model[index]
                    root.statusFilterUpdated(row ? String(row.value || "all") : "all")
                }
            }

            ComboBox {
                Layout.fillWidth: true
                model: root.planLibraryState.planTypeOptions || []
                textRole: "label"
                currentIndex: root.indexOfValue(model, root.planLibraryState.selectedPlanTypeFilter)
                onActivated: function(index) {
                    const row = model[index]
                    root.planTypeFilterUpdated(row ? String(row.value || "all") : "all")
                }
            }

            ComboBox {
                Layout.fillWidth: true
                model: root.planLibraryState.triggerModeOptions || []
                textRole: "label"
                currentIndex: root.indexOfValue(model, root.planLibraryState.selectedTriggerModeFilter)
                onActivated: function(index) {
                    const row = model[index]
                    root.triggerModeFilterUpdated(row ? String(row.value || "all") : "all")
                }
            }

            TextField {
                Layout.fillWidth: true
                text: root.planLibraryState.searchText || ""
                placeholderText: "Plan code, name, trigger, or anchor"
                onEditingFinished: root.searchTextUpdated(text)
            }

            RowLayout {
                Layout.columnSpan: root.width > 1180 ? 4 : 2
                Layout.fillWidth: true
                spacing: Theme.AppTheme.spacingSm

                AppControls.PrimaryButton {
                    text: "Refresh"
                    iconName: "refresh"
                    enabled: !root.isBusy
                    onClicked: root.refreshRequested()
                }

                AppControls.PrimaryButton {
                    text: "New Plan"
                    iconName: "add"
                    enabled: !root.isBusy
                    onClicked: root.createPlanRequested()
                }

                Item { Layout.fillWidth: true }

                AppControls.PrimaryButton {
                    text: "New Plan Task"
                    iconName: "add"
                    enabled: !root.isBusy && String(root.planLibraryState.selectedPlanId || "").length > 0
                    onClicked: root.createPlanTaskRequested(String(root.planLibraryState.selectedPlanId || ""))
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
            title: root.planLibraryState.plans.title || "Plan Library"
            subtitle: root.planLibraryState.plans.subtitle || ""
            emptyState: root.planLibraryState.plans.emptyState || ""
            items: root.planLibraryState.plans.items || []
            selectedItemId: root.planLibraryState.selectedPlanId || ""
            primaryActionLabel: "Edit"
            primaryActionIcon: "edit"
            secondaryActionLabel: "Toggle Active"
            secondaryActionIcon: "workflow"
            actionsEnabled: !root.isBusy

            onItemSelected: function(planId) {
                root.planSelected(planId)
            }

            onPrimaryActionRequested: function(planData) {
                root.editPlanRequested(planData)
            }

            onSecondaryActionRequested: function(planData) {
                root.togglePlanRequested(planData)
            }
        }

        PreventiveDetailSection {
            Layout.fillWidth: true
            Layout.alignment: Qt.AlignTop
            emptyTitle: "No preventive plan selected"
            primaryActionLabel: "Edit"
            secondaryActionLabel: "Toggle Active"
            detailModel: root.planLibraryState.selectedPlan || ({})
            isBusy: root.isBusy

            onPrimaryActionRequested: root.editPlanRequested(detailModel)
            onSecondaryActionRequested: root.togglePlanRequested(detailModel)
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
            title: root.planLibraryState.planTasks.title || "Plan Tasks"
            subtitle: root.planLibraryState.planTasks.subtitle || ""
            emptyState: root.planLibraryState.planTasks.emptyState || ""
            items: root.planLibraryState.planTasks.items || []
            selectedItemId: root.planLibraryState.selectedPlanTaskId || ""
            primaryActionLabel: "Edit"
            primaryActionIcon: "edit"
            actionsEnabled: !root.isBusy

            onItemSelected: function(planTaskId) {
                root.planTaskSelected(planTaskId)
            }

            onPrimaryActionRequested: function(planTaskData) {
                root.editPlanTaskRequested(planTaskData)
            }
        }

        PreventiveDetailSection {
            Layout.fillWidth: true
            Layout.alignment: Qt.AlignTop
            emptyTitle: "No plan task selected"
            primaryActionLabel: "Edit"
            secondaryActionLabel: ""
            detailModel: root.planLibraryState.selectedPlanTask || ({})
            isBusy: root.isBusy

            onPrimaryActionRequested: root.editPlanTaskRequested(detailModel)
        }
    }
}

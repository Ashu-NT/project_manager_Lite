import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme
import Maintenance.Widgets 1.0 as MaintenanceWidgets

ColumnLayout {
    id: root

    property var queueState: ({
        "siteOptions": [],
        "dueStateOptions": [],
        "selectedSiteFilter": "all",
        "selectedDueStateFilter": "all",
        "searchText": "",
        "plans": { "title": "", "subtitle": "", "emptyState": "", "items": [] },
        "selectedPlanId": "",
        "selectedPlan": { "id": "", "title": "", "statusLabel": "", "subtitle": "", "description": "", "emptyState": "", "fields": [], "state": {} },
        "forecastRows": { "title": "", "subtitle": "", "emptyState": "", "items": [] },
        "generationResults": { "title": "", "subtitle": "", "emptyState": "", "items": [] }
    })
    property bool isBusy: false

    signal siteFilterUpdated(string siteId)
    signal dueStateFilterUpdated(string dueState)
    signal searchTextUpdated(string searchText)
    signal refreshRequested()
    signal planSelected(string planId)
    signal regenerateRequested(string planId)
    signal generateRequested(string planId)

    function indexOfValue(options, value) {
        for (let index = 0; index < options.length; index += 1) {
            if (String(options[index].value || "") === String(value || "")) {
                return index
            }
        }
        return 0
    }

    function planState(planData) {
        return planData && planData.state ? planData.state : (planData || {})
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
                id: siteCombo
                Layout.fillWidth: true
                model: root.queueState.siteOptions || []
                textRole: "label"
                currentIndex: root.indexOfValue(model, root.queueState.selectedSiteFilter)
                onActivated: function(index) {
                    const row = model[index]
                    root.siteFilterUpdated(row ? String(row.value || "all") : "all")
                }
            }

            AppControls.ComboBox {
                id: dueStateCombo
                Layout.fillWidth: true
                model: root.queueState.dueStateOptions || []
                textRole: "label"
                currentIndex: root.indexOfValue(model, root.queueState.selectedDueStateFilter)
                onActivated: function(index) {
                    const row = model[index]
                    root.dueStateFilterUpdated(row ? String(row.value || "all") : "all")
                }
            }

            AppControls.TextField {
                id: searchField
                Layout.fillWidth: true
                text: root.queueState.searchText || ""
                placeholderText: "Plan code, anchor, due reason, or trigger"
                onEditingFinished: root.searchTextUpdated(text)
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.AppTheme.spacingSm

                AppControls.PrimaryButton {
                    text: "Refresh"
                    iconName: "refresh"
                    enabled: !root.isBusy
                    onClicked: root.refreshRequested()
                }

                Item { Layout.fillWidth: true }
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
            title: root.queueState.plans.title || "Generation Queue"
            subtitle: root.queueState.plans.subtitle || ""
            emptyState: root.queueState.plans.emptyState || ""
            items: root.queueState.plans.items || []
            selectedItemId: root.queueState.selectedPlanId || ""
            primaryActionLabel: "Refresh Schedule"
            primaryActionIcon: "refresh"
            secondaryActionLabel: "Generate Work"
            secondaryActionIcon: "add"
            actionsEnabled: !root.isBusy

            onItemSelected: function(planId) {
                root.planSelected(planId)
            }

            onPrimaryActionRequested: function(planData) {
                const state = root.planState(planData)
                root.regenerateRequested(String(state.planId || ""))
            }

            onSecondaryActionRequested: function(planData) {
                const state = root.planState(planData)
                root.generateRequested(String(state.planId || ""))
            }
        }

        PreventiveDetailSection {
            Layout.fillWidth: true
            Layout.alignment: Qt.AlignTop
            emptyTitle: "No queue plan selected"
            primaryActionLabel: "Refresh Schedule"
            primaryActionIcon: "refresh"
            secondaryActionLabel: "Generate Work"
            secondaryActionIcon: "add"
            detailModel: root.queueState.selectedPlan || ({})
            isBusy: root.isBusy

            onPrimaryActionRequested: {
                const state = root.planState(detailModel)
                root.regenerateRequested(String(state.planId || ""))
            }

            onSecondaryActionRequested: {
                const state = root.planState(detailModel)
                root.generateRequested(String(state.planId || ""))
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
            title: root.queueState.forecastRows.title || "Forecast"
            subtitle: root.queueState.forecastRows.subtitle || ""
            emptyState: root.queueState.forecastRows.emptyState || ""
            items: root.queueState.forecastRows.items || []
            selectedItemId: ""
            actionsEnabled: false
        }

        MaintenanceWidgets.RecordListCard {
            Layout.fillWidth: true
            Layout.alignment: Qt.AlignTop
            title: root.queueState.generationResults.title || "Latest generation results"
            subtitle: root.queueState.generationResults.subtitle || ""
            emptyState: root.queueState.generationResults.emptyState || ""
            items: root.queueState.generationResults.items || []
            selectedItemId: ""
            actionsEnabled: false
        }
    }
}

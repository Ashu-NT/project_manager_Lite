pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme
import ProjectManagement.Widgets 1.0 as ProjectManagementWidgets

Rectangle {
    id: root

    property var projectOptions: []
    property var scenarioOptions: []
    property var intakeItemsModel: ({ "items": [] })
    property var scenariosModel: ({
        "title": "",
        "subtitle": "",
        "emptyState": "",
        "items": []
    })
    property var evaluationModel: ({
        "title": "",
        "subtitle": "",
        "emptyState": "",
        "fields": []
    })
    property var comparisonModel: ({
        "title": "",
        "subtitle": "",
        "emptyState": "",
        "fields": []
    })
    property bool isBusy: false
    property var selectedProjectIds: []
    property var selectedIntakeIds: []

    signal createRequested(var payload)
    signal scenarioSelected(string scenarioId)

    function updateSelection(target, value, checked) {
        var nextValues = []
        for (var index = 0; index < target.length; index += 1) {
            if (String(target[index]) !== String(value)) {
                nextValues.push(String(target[index]))
            }
        }
        if (checked) {
            nextValues.push(String(value))
        }
        return nextValues
    }

    radius: Theme.AppTheme.radiusLg
    color: Theme.AppTheme.surface
    border.color: Theme.AppTheme.border
    implicitHeight: contentColumn.implicitHeight + (Theme.AppTheme.marginLg * 2)

    ColumnLayout {
        id: contentColumn

        anchors.fill: parent
        anchors.margins: Theme.AppTheme.marginLg
        spacing: Theme.AppTheme.spacingMd

        Label {
            Layout.fillWidth: true
            text: "New Scenario"
            color: Theme.AppTheme.textPrimary
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.bodySize
            font.bold: true
        }

        GridLayout {
            Layout.fillWidth: true
            columns: root.width > 760 ? 2 : 1
            columnSpacing: Theme.AppTheme.spacingMd
            rowSpacing: Theme.AppTheme.spacingSm

            TextField { id: scenarioName; Layout.fillWidth: true; enabled: !root.isBusy; placeholderText: "Balanced Q3 Plan" }
            TextField { id: budgetLimit; Layout.fillWidth: true; enabled: !root.isBusy; placeholderText: "750000.00" }
            TextField { id: capacityLimit; Layout.fillWidth: true; enabled: !root.isBusy; placeholderText: "320.0" }
        }

        TextArea {
            id: scenarioNotes
            Layout.fillWidth: true
            Layout.preferredHeight: 80
            enabled: !root.isBusy
            placeholderText: "Capture decision assumptions or what this scenario is optimizing for."
            wrapMode: TextEdit.WordWrap
        }

        Label {
            Layout.fillWidth: true
            text: "Include projects"
            color: Theme.AppTheme.textSecondary
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.smallSize
        }

        Flow {
            Layout.fillWidth: true
            spacing: Theme.AppTheme.spacingSm

            Repeater {
                model: root.projectOptions

                delegate: CheckBox {
                    id: projectOptionDelegate

                    required property var modelData
                    text: String(projectOptionDelegate.modelData.label || "")
                    enabled: !root.isBusy
                    checked: root.selectedProjectIds.indexOf(
                        String(projectOptionDelegate.modelData.value || "")
                    ) >= 0

                    onToggled: {
                        root.selectedProjectIds = root.updateSelection(
                            root.selectedProjectIds,
                            String(projectOptionDelegate.modelData.value || ""),
                            checked
                        )
                    }
                }
            }
        }

        Label {
            Layout.fillWidth: true
            text: "Include intake items"
            color: Theme.AppTheme.textSecondary
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.smallSize
        }

        Flow {
            Layout.fillWidth: true
            spacing: Theme.AppTheme.spacingSm

            Repeater {
                model: root.intakeItemsModel.items || []

                delegate: CheckBox {
                    id: intakeOptionDelegate

                    required property var modelData
                    text: String(intakeOptionDelegate.modelData.title || "")
                    enabled: !root.isBusy
                    checked: root.selectedIntakeIds.indexOf(
                        String(intakeOptionDelegate.modelData.id || "")
                    ) >= 0

                    onToggled: {
                        root.selectedIntakeIds = root.updateSelection(
                            root.selectedIntakeIds,
                            String(intakeOptionDelegate.modelData.id || ""),
                            checked
                        )
                    }
                }
            }
        }

        AppControls.PrimaryButton {
            text: "Save Scenario"
            enabled: !root.isBusy
            onClicked: {
                root.createRequested({
                    "name": scenarioName.text,
                    "budgetLimit": budgetLimit.text,
                    "capacityLimitPercent": capacityLimit.text,
                    "projectIds": root.selectedProjectIds,
                    "intakeItemIds": root.selectedIntakeIds,
                    "notes": scenarioNotes.text
                })
                scenarioName.text = ""
                budgetLimit.text = ""
                capacityLimit.text = ""
                scenarioNotes.text = ""
                root.selectedProjectIds = []
                root.selectedIntakeIds = []
            }
        }

        ProjectManagementWidgets.RecordListCard {
            Layout.fillWidth: true
            title: root.scenariosModel.title || "Scenario Library"
            subtitle: root.scenariosModel.subtitle || ""
            emptyState: root.scenariosModel.emptyState || ""
            items: root.scenariosModel.items || []
            actionsEnabled: !root.isBusy

            onItemSelected: function(itemId) {
                root.scenarioSelected(itemId)
            }
        }

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

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme
import ProjectManagement.Widgets 1.0 as ProjectManagementWidgets

Rectangle {
    id: root

    property var intakeStatusOptions: []
    property var templateOptions: []
    property var intakeItemsModel: ({
        "title": "",
        "subtitle": "",
        "emptyState": "",
        "items": []
    })
    property string selectedStatusFilter: "all"
    property bool isBusy: false

    signal createRequested(var payload)

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
            text: "New Intake Item"
            color: Theme.AppTheme.textPrimary
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.bodySize
            font.bold: true
        }

        GridLayout {
            Layout.fillWidth: true
            columns: root.width > 780 ? 2 : 1
            columnSpacing: Theme.AppTheme.spacingMd
            rowSpacing: Theme.AppTheme.spacingSm

            TextField { id: titleField; Layout.fillWidth: true; enabled: !root.isBusy; placeholderText: "Quarterly utilities optimization" }
            TextField { id: sponsorField; Layout.fillWidth: true; enabled: !root.isBusy; placeholderText: "Operations Director" }
            TextField { id: budgetField; Layout.fillWidth: true; enabled: !root.isBusy; placeholderText: "250000.00" }
            TextField { id: capacityField; Layout.fillWidth: true; enabled: !root.isBusy; placeholderText: "45.0" }
            TextField { id: startDateField; Layout.fillWidth: true; enabled: !root.isBusy; placeholderText: "YYYY-MM-DD" }
            ComboBox {
                id: statusCombo
                Layout.fillWidth: true
                model: root.intakeStatusOptions
                textRole: "label"
                enabled: !root.isBusy
            }
            ComboBox {
                id: templateCombo
                Layout.fillWidth: true
                model: root.templateOptions
                textRole: "label"
                enabled: !root.isBusy
            }
            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.AppTheme.spacingSm

                Label { text: "Strategic"; color: Theme.AppTheme.textSecondary }
                SpinBox { id: strategicSpin; from: 1; to: 5; value: 3; enabled: !root.isBusy }
                Label { text: "Value"; color: Theme.AppTheme.textSecondary }
                SpinBox { id: valueSpin; from: 1; to: 5; value: 3; enabled: !root.isBusy }
                Label { text: "Urgency"; color: Theme.AppTheme.textSecondary }
                SpinBox { id: urgencySpin; from: 1; to: 5; value: 3; enabled: !root.isBusy }
                Label { text: "Risk"; color: Theme.AppTheme.textSecondary }
                SpinBox { id: riskSpin; from: 1; to: 5; value: 3; enabled: !root.isBusy }
            }
        }

        TextArea {
            id: summaryArea
            Layout.fillWidth: true
            Layout.preferredHeight: 96
            enabled: !root.isBusy
            placeholderText: "Describe the opportunity, demand context, and expected delivery value."
            wrapMode: TextEdit.WordWrap
        }

        AppControls.PrimaryButton {
            text: "Add Intake Item"
            enabled: !root.isBusy
            onClicked: {
                var templateOption = templateCombo.currentIndex >= 0 ? root.templateOptions[templateCombo.currentIndex] : null
                var statusOption = statusCombo.currentIndex >= 0 ? root.intakeStatusOptions[statusCombo.currentIndex] : null
                root.createRequested({
                    "title": titleField.text,
                    "sponsorName": sponsorField.text,
                    "summary": summaryArea.text,
                    "requestedBudget": budgetField.text,
                    "requestedCapacityPercent": capacityField.text,
                    "targetStartDate": startDateField.text,
                    "status": statusOption ? statusOption.value : "PROPOSED",
                    "scoringTemplateId": templateOption ? templateOption.value : "",
                    "strategicScore": strategicSpin.value,
                    "valueScore": valueSpin.value,
                    "urgencyScore": urgencySpin.value,
                    "riskScore": riskSpin.value
                })
                titleField.text = ""
                sponsorField.text = ""
                budgetField.text = ""
                capacityField.text = ""
                startDateField.text = ""
                summaryArea.text = ""
            }
        }

        ProjectManagementWidgets.RecordListCard {
            Layout.fillWidth: true
            title: root.intakeItemsModel.title || "Portfolio Intake"
            subtitle: root.intakeItemsModel.subtitle || ""
            emptyState: root.intakeItemsModel.emptyState || ""
            items: root.intakeItemsModel.items || []
            actionsEnabled: !root.isBusy
        }
    }
}

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme
import ProjectManagement.Widgets 1.0 as ProjectManagementWidgets

Rectangle {
    id: root

    property string activeTemplateSummary: ""
    property var templatesModel: ({
        "title": "",
        "subtitle": "",
        "emptyState": "",
        "items": []
    })
    property bool isBusy: false

    signal createRequested(var payload)
    signal activateRequested(string templateId)

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
            text: root.activeTemplateSummary
            visible: text.length > 0
            color: Theme.AppTheme.textSecondary
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.smallSize
            wrapMode: Text.WordWrap
        }

        GridLayout {
            Layout.fillWidth: true
            columns: root.width > 760 ? 2 : 1
            columnSpacing: Theme.AppTheme.spacingMd
            rowSpacing: Theme.AppTheme.spacingSm

            TextField { id: nameField; Layout.fillWidth: true; enabled: !root.isBusy; placeholderText: "Balanced PMO" }
            TextField { id: summaryField; Layout.fillWidth: true; enabled: !root.isBusy; placeholderText: "Balanced scoring for strategic fit and delivery risk." }

            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.AppTheme.spacingSm
                Label { text: "Strategic"; color: Theme.AppTheme.textSecondary }
                SpinBox { id: strategicWeight; from: 1; to: 5; value: 3; enabled: !root.isBusy }
                Label { text: "Value"; color: Theme.AppTheme.textSecondary }
                SpinBox { id: valueWeight; from: 1; to: 5; value: 2; enabled: !root.isBusy }
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.AppTheme.spacingSm
                Label { text: "Urgency"; color: Theme.AppTheme.textSecondary }
                SpinBox { id: urgencyWeight; from: 1; to: 5; value: 2; enabled: !root.isBusy }
                Label { text: "Risk"; color: Theme.AppTheme.textSecondary }
                SpinBox { id: riskWeight; from: 1; to: 5; value: 1; enabled: !root.isBusy }
                CheckBox { id: activateBox; text: "Activate now"; enabled: !root.isBusy }
            }
        }

        AppControls.PrimaryButton {
            text: "Create Template"
            enabled: !root.isBusy
            onClicked: {
                root.createRequested({
                    "name": nameField.text,
                    "summary": summaryField.text,
                    "strategicWeight": strategicWeight.value,
                    "valueWeight": valueWeight.value,
                    "urgencyWeight": urgencyWeight.value,
                    "riskWeight": riskWeight.value,
                    "activate": activateBox.checked
                })
                nameField.text = ""
                summaryField.text = ""
                activateBox.checked = false
            }
        }

        ProjectManagementWidgets.RecordListCard {
            Layout.fillWidth: true
            title: root.templatesModel.title || "Scoring Templates"
            subtitle: root.templatesModel.subtitle || ""
            emptyState: root.templatesModel.emptyState || ""
            items: root.templatesModel.items || []
            primaryActionLabel: "Activate"
            actionsEnabled: !root.isBusy

            onPrimaryActionRequested: function(itemData) {
                var state = itemData && itemData.state ? itemData.state : {}
                if (state.templateId) {
                    root.activateRequested(String(state.templateId))
                }
            }
        }
    }
}

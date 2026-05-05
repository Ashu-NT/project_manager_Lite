import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme
import ProjectManagement.Widgets 1.0 as ProjectManagementWidgets

Rectangle {
    id: root

    property var reviewQueueModel: ({
        "title": "",
        "subtitle": "",
        "emptyState": "",
        "items": []
    })
    property var reviewDetail: ({
        "title": "",
        "subtitle": "",
        "emptyState": "",
        "fields": [],
        "state": {}
    })
    property string selectedQueuePeriodId: ""
    property bool isBusy: false

    signal queuePeriodSelected(string periodId)
    signal approveRequested(var payload)
    signal rejectRequested(var payload)

    radius: Theme.AppTheme.radiusLg
    color: Theme.AppTheme.surface
    border.color: Theme.AppTheme.border
    implicitHeight: contentColumn.implicitHeight + (Theme.AppTheme.marginLg * 2)

    ColumnLayout {
        id: contentColumn

        anchors.fill: parent
        anchors.margins: Theme.AppTheme.marginLg
        spacing: Theme.AppTheme.spacingMd

        ProjectManagementWidgets.RecordListCard {
            Layout.fillWidth: true
            title: root.reviewQueueModel.title || "Review Queue"
            subtitle: root.reviewQueueModel.subtitle || ""
            emptyState: root.reviewQueueModel.emptyState || ""
            items: root.reviewQueueModel.items || []
            selectedItemId: root.selectedQueuePeriodId
            actionsEnabled: !root.isBusy

            onItemSelected: function(itemId) {
                root.queuePeriodSelected(itemId)
            }
        }

        Label {
            Layout.fillWidth: true
            text: root.reviewDetail.title || "Review Detail"
            color: Theme.AppTheme.textPrimary
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.bodySize
            font.bold: true
            wrapMode: Text.WordWrap
        }

        Label {
            Layout.fillWidth: true
            visible: String(root.reviewDetail.subtitle || "").length > 0
            text: root.reviewDetail.subtitle || ""
            color: Theme.AppTheme.textSecondary
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.smallSize
            wrapMode: Text.WordWrap
        }

        Label {
            Layout.fillWidth: true
            visible: String(root.reviewDetail.description || "").length > 0
            text: root.reviewDetail.description || ""
            color: Theme.AppTheme.textPrimary
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.smallSize
            wrapMode: Text.WordWrap
        }

        Label {
            Layout.fillWidth: true
            visible: (root.reviewDetail.fields || []).length === 0 && String(root.reviewDetail.emptyState || "").length > 0
            text: root.reviewDetail.emptyState || ""
            color: Theme.AppTheme.textSecondary
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.smallSize
            wrapMode: Text.WordWrap
        }

        Repeater {
            model: root.reviewDetail.fields || []

            delegate: ColumnLayout {
                id: reviewFieldRow

                required property var modelData
                Layout.fillWidth: true
                spacing: Theme.AppTheme.spacingXs

                Label {
                    Layout.fillWidth: true
                    text: String(reviewFieldRow.modelData.label || "")
                    color: Theme.AppTheme.textSecondary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                }

                Label {
                    Layout.fillWidth: true
                    text: String(reviewFieldRow.modelData.value || "")
                    color: Theme.AppTheme.textPrimary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.bodySize
                    font.bold: true
                    wrapMode: Text.WordWrap
                }

                Label {
                    Layout.fillWidth: true
                    visible: String(reviewFieldRow.modelData.supportingText || "").length > 0
                    text: String(reviewFieldRow.modelData.supportingText || "")
                    color: Theme.AppTheme.textSecondary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                    wrapMode: Text.WordWrap
                }
            }
        }

        TextArea {
            id: decisionNoteArea
            Layout.fillWidth: true
            Layout.preferredHeight: 84
            enabled: !root.isBusy
            placeholderText: "Optional approval or rejection note for the selected period."
            wrapMode: TextEdit.WordWrap
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.AppTheme.spacingSm

            AppControls.PrimaryButton {
                text: "Approve"
                enabled: !root.isBusy && Boolean(root.reviewDetail.state.periodId)
                onClicked: root.approveRequested({
                    "periodId": root.reviewDetail.state.periodId || "",
                    "note": decisionNoteArea.text
                })
            }

            AppControls.PrimaryButton {
                text: "Reject"
                enabled: !root.isBusy && Boolean(root.reviewDetail.state.periodId)
                danger: true
                onClicked: root.rejectRequested({
                    "periodId": root.reviewDetail.state.periodId || "",
                    "note": decisionNoteArea.text
                })
            }
        }
    }
}

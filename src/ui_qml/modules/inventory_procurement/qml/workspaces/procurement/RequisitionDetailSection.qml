pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme
import App.Widgets 1.0 as AppWidgets

Item {
    id: root

    property var requisitionDetail: ({
        "id": "",
        "title": "",
        "statusLabel": "",
        "subtitle": "",
        "description": "",
        "emptyState": "",
        "fields": [],
        "state": {}
    })
    property bool isBusy: false

    signal editRequested()
    signal addLineRequested()
    signal submitRequested()
    signal cancelRequested()

    implicitHeight: contentColumn.implicitHeight

    ColumnLayout {
        id: contentColumn
        anchors.fill: parent
        spacing: Theme.AppTheme.spacingMd

        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.AppTheme.spacingSm

            ColumnLayout {
                Layout.fillWidth: true
                spacing: Theme.AppTheme.spacingXs

                Label {
                    Layout.fillWidth: true
                    text: root.requisitionDetail.title || "Requisition Detail"
                    color: Theme.AppTheme.textPrimary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.bodySize
                    font.bold: true
                    wrapMode: Text.WordWrap
                }

                Label {
                    Layout.fillWidth: true
                    text: root.requisitionDetail.subtitle || "Select a requisition to review demand details."
                    color: Theme.AppTheme.textSecondary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                    wrapMode: Text.WordWrap
                }
            }

            AppWidgets.StatusChip {
                visible: String(root.requisitionDetail.statusLabel || "").length > 0
                status: root.requisitionDetail.statusLabel || ""
            }
        }

        Label {
            Layout.fillWidth: true
            visible: String(root.requisitionDetail.emptyState || "").length > 0 && String(root.requisitionDetail.id || "").length === 0
            text: root.requisitionDetail.emptyState
            color: Theme.AppTheme.textSecondary
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.bodySize
            wrapMode: Text.WordWrap
        }

        Label {
            Layout.fillWidth: true
            visible: String(root.requisitionDetail.id || "").length > 0
            text: root.requisitionDetail.description || ""
            color: Theme.AppTheme.textPrimary
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.bodySize
            wrapMode: Text.WordWrap
        }

        Repeater {
            model: root.requisitionDetail.fields || []

            delegate: Rectangle {
                id: fieldCard
                required property var modelData

                Layout.fillWidth: true
                radius: Theme.AppTheme.radiusMd
                color: Theme.AppTheme.surfaceAlt
                implicitHeight: fieldLayout.implicitHeight + (Theme.AppTheme.marginMd * 2)

                ColumnLayout {
                    id: fieldLayout
                    anchors.fill: parent
                    anchors.margins: Theme.AppTheme.marginMd
                    spacing: Theme.AppTheme.spacingXs

                    Label {
                        Layout.fillWidth: true
                        text: String(fieldCard.modelData.label || "")
                        color: Theme.AppTheme.textMuted
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.smallSize
                        font.bold: true
                    }

                    Label {
                        Layout.fillWidth: true
                        text: String(fieldCard.modelData.value || "")
                        color: Theme.AppTheme.textPrimary
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.bodySize
                        wrapMode: Text.WordWrap
                    }
                }
            }
        }

        Flow {
            Layout.fillWidth: true
            visible: String(root.requisitionDetail.id || "").length > 0
            spacing: Theme.AppTheme.spacingSm

            AppControls.PrimaryButton {
                text: "Edit"
                enabled: !root.isBusy && !!(root.requisitionDetail.state && root.requisitionDetail.state.canEdit)
                onClicked: root.editRequested()
            }

            AppControls.PrimaryButton {
                text: "Add Line"
                enabled: !root.isBusy && !!(root.requisitionDetail.state && root.requisitionDetail.state.canAddLine)
                onClicked: root.addLineRequested()
            }

            AppControls.PrimaryButton {
                text: "Submit"
                enabled: !root.isBusy && !!(root.requisitionDetail.state && root.requisitionDetail.state.canSubmit)
                onClicked: root.submitRequested()
            }

            AppControls.PrimaryButton {
                text: "Cancel"
                danger: true
                enabled: !root.isBusy && !!(root.requisitionDetail.state && root.requisitionDetail.state.canCancel)
                onClicked: root.cancelRequested()
            }
        }
    }
}

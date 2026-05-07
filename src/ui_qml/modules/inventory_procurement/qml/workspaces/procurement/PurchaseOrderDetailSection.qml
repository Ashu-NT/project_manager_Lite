pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme

Rectangle {
    id: root

    property var purchaseOrderDetail: ({
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
    signal sendRequested()
    signal cancelRequested()
    signal closeRequested()
    signal postReceiptRequested()

    radius: Theme.AppTheme.radiusLg
    color: Theme.AppTheme.surface
    border.color: Theme.AppTheme.border
    implicitHeight: contentColumn.implicitHeight + (Theme.AppTheme.marginLg * 2)

    ColumnLayout {
        id: contentColumn
        anchors.fill: parent
        anchors.margins: Theme.AppTheme.marginLg
        spacing: Theme.AppTheme.spacingMd

        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.AppTheme.spacingSm

            ColumnLayout {
                Layout.fillWidth: true
                spacing: Theme.AppTheme.spacingXs

                Label {
                    Layout.fillWidth: true
                    text: root.purchaseOrderDetail.title || "Purchase-Order Detail"
                    color: Theme.AppTheme.textPrimary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.bodySize
                    font.bold: true
                    wrapMode: Text.WordWrap
                }

                Label {
                    Layout.fillWidth: true
                    text: root.purchaseOrderDetail.subtitle || "Select a purchase order to review supplier commitments."
                    color: Theme.AppTheme.textSecondary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                    wrapMode: Text.WordWrap
                }
            }

            Rectangle {
                visible: String(root.purchaseOrderDetail.statusLabel || "").length > 0
                radius: Theme.AppTheme.radiusMd
                color: Theme.AppTheme.accentSoft
                border.color: Theme.AppTheme.accent
                implicitHeight: 30
                implicitWidth: statusLabel.implicitWidth + (Theme.AppTheme.marginMd * 2)

                Label {
                    id: statusLabel
                    anchors.centerIn: parent
                    text: root.purchaseOrderDetail.statusLabel
                    color: Theme.AppTheme.accent
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                    font.bold: true
                }
            }
        }

        Label {
            Layout.fillWidth: true
            visible: String(root.purchaseOrderDetail.emptyState || "").length > 0 && String(root.purchaseOrderDetail.id || "").length === 0
            text: root.purchaseOrderDetail.emptyState
            color: Theme.AppTheme.textSecondary
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.bodySize
            wrapMode: Text.WordWrap
        }

        Label {
            Layout.fillWidth: true
            visible: String(root.purchaseOrderDetail.id || "").length > 0
            text: root.purchaseOrderDetail.description || ""
            color: Theme.AppTheme.textPrimary
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.bodySize
            wrapMode: Text.WordWrap
        }

        Repeater {
            model: root.purchaseOrderDetail.fields || []

            delegate: Rectangle {
                id: fieldCard
                required property var modelData

                Layout.fillWidth: true
                radius: Theme.AppTheme.radiusMd
                color: Theme.AppTheme.surfaceAlt
                border.color: Theme.AppTheme.border
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
            visible: String(root.purchaseOrderDetail.id || "").length > 0
            spacing: Theme.AppTheme.spacingSm

            AppControls.PrimaryButton {
                text: "Edit"
                enabled: !root.isBusy && !!(root.purchaseOrderDetail.state && root.purchaseOrderDetail.state.canEdit)
                onClicked: root.editRequested()
            }

            AppControls.PrimaryButton {
                text: "Add Line"
                enabled: !root.isBusy && !!(root.purchaseOrderDetail.state && root.purchaseOrderDetail.state.canAddLine)
                onClicked: root.addLineRequested()
            }

            AppControls.PrimaryButton {
                text: "Submit"
                enabled: !root.isBusy && !!(root.purchaseOrderDetail.state && root.purchaseOrderDetail.state.canSubmit)
                onClicked: root.submitRequested()
            }

            AppControls.PrimaryButton {
                text: "Send"
                enabled: !root.isBusy && !!(root.purchaseOrderDetail.state && root.purchaseOrderDetail.state.canSend)
                onClicked: root.sendRequested()
            }

            AppControls.PrimaryButton {
                text: "Cancel"
                danger: true
                enabled: !root.isBusy && !!(root.purchaseOrderDetail.state && root.purchaseOrderDetail.state.canCancel)
                onClicked: root.cancelRequested()
            }

            AppControls.PrimaryButton {
                text: "Close"
                enabled: !root.isBusy && !!(root.purchaseOrderDetail.state && root.purchaseOrderDetail.state.canClose)
                onClicked: root.closeRequested()
            }

            AppControls.PrimaryButton {
                text: "Post Receipt"
                enabled: !root.isBusy && !!(root.purchaseOrderDetail.state && root.purchaseOrderDetail.state.canPostReceipt)
                onClicked: root.postReceiptRequested()
            }
        }
    }
}

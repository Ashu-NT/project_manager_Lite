pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Mock 1.0 as AppMock
import App.Theme 1.0 as Theme
import App.Widgets 1.0 as AppWidgets

Item {
    id: root

    property var purchaseOrderDetail: AppMock.MockFactory.detail()
    property bool isBusy: false

    signal editRequested()
    signal addLineRequested()
    signal submitRequested()
    signal sendRequested()
    signal cancelRequested()
    signal closeRequested()
    signal postReceiptRequested()

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

            AppWidgets.StatusChip {
                visible: String(root.purchaseOrderDetail.statusLabel || "").length > 0
                status: root.purchaseOrderDetail.statusLabel || ""
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

            delegate: Item {
                id: fieldRow
                required property var modelData

                Layout.fillWidth: true
                implicitHeight: fieldLayout.implicitHeight + Theme.AppTheme.spacingMd + 1

                ColumnLayout {
                    id: fieldLayout
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.leftMargin: Theme.AppTheme.spacingSm
                    anchors.rightMargin: Theme.AppTheme.spacingSm
                    anchors.topMargin: Theme.AppTheme.spacingSm
                    spacing: Theme.AppTheme.spacingXs

                    Label {
                        Layout.fillWidth: true
                        text: String(fieldRow.modelData.label || "")
                        color: Theme.AppTheme.textMuted
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.smallSize
                        font.bold: true
                    }

                    Label {
                        Layout.fillWidth: true
                        text: String(fieldRow.modelData.value || "")
                        color: Theme.AppTheme.textPrimary
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.bodySize
                        wrapMode: Text.WordWrap
                    }
                }

                Rectangle {
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.bottom: parent.bottom
                    height: 1
                    color: Theme.AppTheme.divider
                }
            }
        }

        Flow {
            Layout.fillWidth: true
            visible: String(root.purchaseOrderDetail.id || "").length > 0
            spacing: Theme.AppTheme.spacingSm

            AppControls.SecondaryButton {
                text: "Edit"
                iconName: "edit"
                enabled: !root.isBusy && !!(root.purchaseOrderDetail.state && root.purchaseOrderDetail.state.canEdit)
                onClicked: root.editRequested()
            }

            AppControls.SecondaryButton {
                text: "Add Line"
                iconName: "add"
                enabled: !root.isBusy && !!(root.purchaseOrderDetail.state && root.purchaseOrderDetail.state.canAddLine)
                onClicked: root.addLineRequested()
            }

            AppControls.PrimaryButton {
                text: "Submit"
                iconName: "approve"
                enabled: !root.isBusy && !!(root.purchaseOrderDetail.state && root.purchaseOrderDetail.state.canSubmit)
                onClicked: root.submitRequested()
            }

            AppControls.PrimaryButton {
                text: "Send"
                iconName: "export"
                enabled: !root.isBusy && !!(root.purchaseOrderDetail.state && root.purchaseOrderDetail.state.canSend)
                onClicked: root.sendRequested()
            }

            AppControls.SecondaryButton {
                text: "Cancel"
                iconName: "close"
                danger: true
                enabled: !root.isBusy && !!(root.purchaseOrderDetail.state && root.purchaseOrderDetail.state.canCancel)
                onClicked: root.cancelRequested()
            }

            AppControls.SecondaryButton {
                text: "Close"
                iconName: "close"
                enabled: !root.isBusy && !!(root.purchaseOrderDetail.state && root.purchaseOrderDetail.state.canClose)
                onClicked: root.closeRequested()
            }

            AppControls.PrimaryButton {
                text: "Post Receipt"
                iconName: "approve"
                enabled: !root.isBusy && !!(root.purchaseOrderDetail.state && root.purchaseOrderDetail.state.canPostReceipt)
                onClicked: root.postReceiptRequested()
            }
        }
    }
}

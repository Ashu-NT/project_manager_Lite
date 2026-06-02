pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQml
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme
import App.Widgets 1.0 as AppWidgets

AppWidgets.EntityDialog {
    id: root

    property var purchaseOrderData: ({})
    property var purchaseOrderLines: []

    signal submitted(var payload)

    width: 860
    title: "Post Receipt"
    subtitle: "Post receipt quantities for the selected purchase order lines."
    primaryText: "Post Receipt"
    primaryIcon: "approve"
    onAccepted: root.submitDialog()
    onRejected: root.close()

    ListModel {
        id: receiptLineModel
    }

    function populateFromPurchaseOrder() {
        var state = root.purchaseOrderData && root.purchaseOrderData.state ? root.purchaseOrderData.state : (root.purchaseOrderData || {})
        supplierDeliveryReferenceField.text = ""
        notesField.text = ""
        receiptLineModel.clear()
        for (var index = 0; index < (root.purchaseOrderLines || []).length; index += 1) {
            var line = root.purchaseOrderLines[index] || {}
            var lineState = line.state || {}
            var outstandingQty = Number(lineState.outstandingQty || 0)
            if (outstandingQty <= 0) {
                continue
            }
            receiptLineModel.append({
                "purchaseOrderLineId": String(lineState.purchaseOrderLineId || ""),
                "title": String(line.title || ""),
                "subtitle": String(line.subtitle || ""),
                "supportingText": String(line.supportingText || ""),
                "uom": String(lineState.uom || ""),
                "unitPrice": String(lineState.unitPrice || ""),
                "outstandingQty": outstandingQty,
                "quantityAccepted": "",
                "quantityRejected": "",
                "notes": ""
            })
        }
        root.errorMessage = ""
    }

    function buildPayload() {
        var state = root.purchaseOrderData && root.purchaseOrderData.state ? root.purchaseOrderData.state : (root.purchaseOrderData || {})
        var lines = []
        for (var index = 0; index < receiptLineModel.count; index += 1) {
            var line = receiptLineModel.get(index)
            lines.push({
                "purchaseOrderLineId": String(line.purchaseOrderLineId || ""),
                "quantityAccepted": String(line.quantityAccepted || ""),
                "quantityRejected": String(line.quantityRejected || ""),
                "unitCost": String(line.unitPrice || ""),
                "notes": String(line.notes || "")
            })
        }
        return {
            "purchaseOrderId": String(state.purchaseOrderId || ""),
            "supplierDeliveryReference": supplierDeliveryReferenceField.text,
            "notes": notesField.text,
            "receiptLines": lines
        }
    }

    function submitDialog() {
        var hasAnyQuantity = false
        for (var index = 0; index < receiptLineModel.count; index += 1) {
            var line = receiptLineModel.get(index)
            if (Number(line.quantityAccepted || 0) > 0 || Number(line.quantityRejected || 0) > 0) {
                hasAnyQuantity = true
                break
            }
        }
        if (!hasAnyQuantity) {
            root.errorMessage = "Enter at least one accepted or rejected quantity before posting the receipt."
            return
        }
        root.errorMessage = ""
        root.submitted(root.buildPayload())
    }

    onOpened: root.populateFromPurchaseOrder()

    GridLayout {
        Layout.fillWidth: true
        columns: 2
        columnSpacing: Theme.AppTheme.spacingMd
        rowSpacing: Theme.AppTheme.spacingSm

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Delivery reference"
            AppControls.TextField { id: supplierDeliveryReferenceField; Layout.fillWidth: true; placeholderText: "Carrier or supplier slip number" }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Notes"
            AppControls.TextArea {
                id: notesField
                Layout.fillWidth: true
                Layout.preferredHeight: 72
                wrapMode: TextEdit.WordWrap
                placeholderText: "Receipt header notes, carrier remarks, or inspection summary."
            }
        }
    }

    ScrollView {
        Layout.fillWidth: true
        Layout.preferredHeight: 340
        clip: true

        ColumnLayout {
            width: parent.width
            spacing: Theme.AppTheme.spacingSm

            Repeater {
                model: receiptLineModel

                delegate: Rectangle {
                    id: receiptLineCard

                    required property int index
                    required property string title
                    required property string subtitle
                    required property string supportingText
                    required property string quantityAccepted
                    required property string quantityRejected
                    required property string unitPrice

                    Layout.fillWidth: true
                    radius: Theme.AppTheme.radiusMd
                    color: Theme.AppTheme.surfaceAlt
                    implicitHeight: lineLayout.implicitHeight + (Theme.AppTheme.marginMd * 2)

                    ColumnLayout {
                        id: lineLayout
                        anchors.fill: parent
                        anchors.margins: Theme.AppTheme.marginMd
                        spacing: Theme.AppTheme.spacingSm

                        AppControls.Label {
                            Layout.fillWidth: true
                            text: receiptLineCard.title
                            color: Theme.AppTheme.textPrimary
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.bodySize
                            font.bold: true
                            wrapMode: Text.WordWrap
                        }

                        AppControls.Label {
                            Layout.fillWidth: true
                            text: receiptLineCard.subtitle
                            color: Theme.AppTheme.textSecondary
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.smallSize
                            wrapMode: Text.WordWrap
                        }

                        AppControls.Label {
                            Layout.fillWidth: true
                            text: receiptLineCard.supportingText
                            color: Theme.AppTheme.textMuted
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.smallSize
                            wrapMode: Text.WordWrap
                        }

                        GridLayout {
                            Layout.fillWidth: true
                            columns: root.width > 720 ? 3 : 1
                            columnSpacing: Theme.AppTheme.spacingMd
                            rowSpacing: Theme.AppTheme.spacingSm

                            AppControls.TextField {
                                Layout.fillWidth: true
                                placeholderText: "Accepted qty"
                                text: receiptLineCard.quantityAccepted
                                inputMethodHints: Qt.ImhFormattedNumbersOnly
                                onTextChanged: receiptLineModel.setProperty(receiptLineCard.index, "quantityAccepted", text)
                            }

                            AppControls.TextField {
                                Layout.fillWidth: true
                                placeholderText: "Rejected qty"
                                text: receiptLineCard.quantityRejected
                                inputMethodHints: Qt.ImhFormattedNumbersOnly
                                onTextChanged: receiptLineModel.setProperty(receiptLineCard.index, "quantityRejected", text)
                            }

                            AppControls.TextField {
                                Layout.fillWidth: true
                                placeholderText: "Unit cost"
                                text: receiptLineCard.unitPrice
                                inputMethodHints: Qt.ImhFormattedNumbersOnly
                                onTextChanged: receiptLineModel.setProperty(receiptLineCard.index, "unitPrice", text)
                            }
                        }
                    }
                }
            }
        }
    }
}

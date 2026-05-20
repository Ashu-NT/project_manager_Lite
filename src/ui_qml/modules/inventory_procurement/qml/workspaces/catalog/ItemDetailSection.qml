pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme
import App.Widgets 1.0 as AppWidgets

Item {
    id: root

    property var itemDetail: ({
        "id": "",
        "title": "",
        "statusLabel": "",
        "subtitle": "",
        "description": "",
        "emptyState": "",
        "fields": [],
        "linkedDocuments": [],
        "state": {}
    })
    property bool isBusy: false

    signal editRequested()
    signal toggleRequested()
    signal linkDocumentRequested()
    signal unlinkDocumentRequested(var documentData)

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
                    text: root.itemDetail.title || "Item Detail"
                    color: Theme.AppTheme.textPrimary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.bodySize
                    font.bold: true
                    wrapMode: Text.WordWrap
                }

                Label {
                    Layout.fillWidth: true
                    text: root.itemDetail.subtitle || "Select an item to inspect details."
                    color: Theme.AppTheme.textSecondary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                    wrapMode: Text.WordWrap
                }
            }

            AppWidgets.StatusChip {
                visible: String(root.itemDetail.statusLabel || "").length > 0
                status: root.itemDetail.statusLabel || ""
            }
        }

        Label {
            Layout.fillWidth: true
            visible: String(root.itemDetail.emptyState || "").length > 0 && String(root.itemDetail.id || "").length === 0
            text: root.itemDetail.emptyState
            color: Theme.AppTheme.textSecondary
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.bodySize
            wrapMode: Text.WordWrap
        }

        Label {
            Layout.fillWidth: true
            visible: String(root.itemDetail.id || "").length > 0
            text: root.itemDetail.description || ""
            color: Theme.AppTheme.textPrimary
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.bodySize
            wrapMode: Text.WordWrap
        }

        Repeater {
            model: root.itemDetail.fields || []

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

                    Label {
                        Layout.fillWidth: true
                        visible: String(fieldCard.modelData.supportingText || "").length > 0
                        text: String(fieldCard.modelData.supportingText || "")
                        color: Theme.AppTheme.textSecondary
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.smallSize
                        wrapMode: Text.WordWrap
                    }
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            visible: String(root.itemDetail.id || "").length > 0
            radius: Theme.AppTheme.radiusMd
            color: Theme.AppTheme.surfaceAlt
            implicitHeight: documentsColumn.implicitHeight + (Theme.AppTheme.marginMd * 2)

            ColumnLayout {
                id: documentsColumn
                anchors.fill: parent
                anchors.margins: Theme.AppTheme.marginMd
                spacing: Theme.AppTheme.spacingSm

                RowLayout {
                    Layout.fillWidth: true

                    Label {
                        Layout.fillWidth: true
                        text: "Linked Documents"
                        color: Theme.AppTheme.textPrimary
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.bodySize
                        font.bold: true
                    }

                    AppControls.PrimaryButton {
                        text: "Link Document"
                        iconName: "import"
                        enabled: !root.isBusy
                        onClicked: root.linkDocumentRequested()
                    }
                }

                Label {
                    Layout.fillWidth: true
                    visible: (root.itemDetail.linkedDocuments || []).length === 0
                    text: "No linked documents"
                    color: Theme.AppTheme.textSecondary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                }

                Repeater {
                    model: root.itemDetail.linkedDocuments || []

                    delegate: Rectangle {
                        id: docCard
                        required property var modelData

                        Layout.fillWidth: true
                        radius: Theme.AppTheme.radiusMd
                        color: Theme.AppTheme.surface
                        implicitHeight: docLayout.implicitHeight + (Theme.AppTheme.marginMd * 2)

                        RowLayout {
                            id: docLayout
                            anchors.fill: parent
                            anchors.margins: Theme.AppTheme.marginMd
                            spacing: Theme.AppTheme.spacingSm

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: Theme.AppTheme.spacingXs

                                Label {
                                    Layout.fillWidth: true
                                    text: String(docCard.modelData.label || "")
                                    color: Theme.AppTheme.textPrimary
                                    font.family: Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.smallSize
                                    font.bold: true
                                    wrapMode: Text.WordWrap
                                }

                                Label {
                                    Layout.fillWidth: true
                                    text: String(docCard.modelData.documentType || "") + " | " + String(docCard.modelData.storageKind || "")
                                    color: Theme.AppTheme.textSecondary
                                    font.family: Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.smallSize
                                    wrapMode: Text.WordWrap
                                }
                            }

                            AppControls.PrimaryButton {
                                text: "Unlink"
                                iconName: "delete"
                                enabled: !root.isBusy
                                onClicked: root.unlinkDocumentRequested(docCard.modelData)
                            }
                        }
                    }
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            visible: String(root.itemDetail.id || "").length > 0
            spacing: Theme.AppTheme.spacingSm

            AppControls.PrimaryButton {
                text: "Edit"
                iconName: "edit"
                enabled: !root.isBusy
                onClicked: root.editRequested()
            }

            AppControls.PrimaryButton {
                text: root.itemDetail.state && root.itemDetail.state.isActive ? "Deactivate" : "Activate"
                iconName: root.itemDetail.state && root.itemDetail.state.isActive ? "reject" : "approve"
                enabled: !root.isBusy
                onClicked: root.toggleRequested()
            }

            Item {
                Layout.fillWidth: true
            }
        }
    }
}

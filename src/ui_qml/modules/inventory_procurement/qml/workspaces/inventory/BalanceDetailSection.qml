pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme
import App.Widgets 1.0 as AppWidgets

Item {
    id: root

    property var balanceDetail: ({
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

    signal adjustmentRequested()
    signal issueRequested()
    signal returnRequested()
    signal transferRequested()

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
                    text: root.balanceDetail.title || "Balance Detail"
                    color: Theme.AppTheme.textPrimary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.bodySize
                    font.bold: true
                    wrapMode: Text.WordWrap
                }

                Label {
                    Layout.fillWidth: true
                    text: root.balanceDetail.subtitle || "Select a balance row to review position or launch movement actions."
                    color: Theme.AppTheme.textSecondary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                    wrapMode: Text.WordWrap
                }
            }

            AppWidgets.StatusChip {
                visible: String(root.balanceDetail.statusLabel || "").length > 0
                status: root.balanceDetail.statusLabel || ""
            }
        }

        Label {
            Layout.fillWidth: true
            visible: String(root.balanceDetail.emptyState || "").length > 0 && String(root.balanceDetail.id || "").length === 0
            text: root.balanceDetail.emptyState
            color: Theme.AppTheme.textSecondary
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.bodySize
            wrapMode: Text.WordWrap
        }

        Label {
            Layout.fillWidth: true
            visible: String(root.balanceDetail.id || "").length > 0
            text: root.balanceDetail.description || ""
            color: Theme.AppTheme.textPrimary
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.bodySize
            wrapMode: Text.WordWrap
        }

        Repeater {
            model: root.balanceDetail.fields || []

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

        RowLayout {
            Layout.fillWidth: true
            visible: String(root.balanceDetail.id || "").length > 0
            spacing: Theme.AppTheme.spacingSm

            AppControls.PrimaryButton {
                text: "Adjust"
                enabled: !root.isBusy
                onClicked: root.adjustmentRequested()
            }

            AppControls.PrimaryButton {
                text: "Issue"
                enabled: !root.isBusy
                onClicked: root.issueRequested()
            }

            AppControls.PrimaryButton {
                text: "Return"
                enabled: !root.isBusy
                onClicked: root.returnRequested()
            }

            AppControls.PrimaryButton {
                text: "Transfer"
                enabled: !root.isBusy
                onClicked: root.transferRequested()
            }

            Item {
                Layout.fillWidth: true
            }
        }
    }
}

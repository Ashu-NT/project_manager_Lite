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

    property var balanceDetail: AppMock.MockFactory.detail()
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

                    Label {
                        Layout.fillWidth: true
                        visible: String(fieldRow.modelData.supportingText || "").length > 0
                        text: String(fieldRow.modelData.supportingText || "")
                        color: Theme.AppTheme.textSecondary
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.smallSize
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

        RowLayout {
            Layout.fillWidth: true
            visible: String(root.balanceDetail.id || "").length > 0
            spacing: Theme.AppTheme.spacingSm

            AppControls.SecondaryButton {
                text: "Adjust"
                iconName: "edit"
                enabled: !root.isBusy
                onClicked: root.adjustmentRequested()
            }

            AppControls.PrimaryButton {
                text: "Issue"
                iconName: "approve"
                enabled: !root.isBusy
                onClicked: root.issueRequested()
            }

            AppControls.SecondaryButton {
                text: "Return"
                iconName: "import"
                enabled: !root.isBusy
                onClicked: root.returnRequested()
            }

            AppControls.SecondaryButton {
                text: "Transfer"
                iconName: "export"
                enabled: !root.isBusy
                onClicked: root.transferRequested()
            }

            Item {
                Layout.fillWidth: true
            }
        }
    }
}

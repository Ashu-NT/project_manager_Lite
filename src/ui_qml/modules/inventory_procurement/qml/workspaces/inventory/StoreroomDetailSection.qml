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

    property var storeroomDetail: AppMock.MockFactory.detail()
    property bool isBusy: false

    signal editRequested()
    signal toggleRequested()
    signal openingBalanceRequested()

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
                    text: root.storeroomDetail.title || "Storeroom Detail"
                    color: Theme.AppTheme.textPrimary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.bodySize
                    font.bold: true
                    wrapMode: Text.WordWrap
                }

                Label {
                    Layout.fillWidth: true
                    text: root.storeroomDetail.subtitle || "Select a storeroom to review governance and capability settings."
                    color: Theme.AppTheme.textSecondary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                    wrapMode: Text.WordWrap
                }
            }

            AppWidgets.StatusChip {
                visible: String(root.storeroomDetail.statusLabel || "").length > 0
                status: root.storeroomDetail.statusLabel || ""
            }
        }

        Label {
            Layout.fillWidth: true
            visible: String(root.storeroomDetail.emptyState || "").length > 0 && String(root.storeroomDetail.id || "").length === 0
            text: root.storeroomDetail.emptyState
            color: Theme.AppTheme.textSecondary
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.bodySize
            wrapMode: Text.WordWrap
        }

        Label {
            Layout.fillWidth: true
            visible: String(root.storeroomDetail.id || "").length > 0
            text: root.storeroomDetail.description || ""
            color: Theme.AppTheme.textPrimary
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.bodySize
            wrapMode: Text.WordWrap
        }

        Repeater {
            model: root.storeroomDetail.fields || []

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
            visible: String(root.storeroomDetail.id || "").length > 0
            spacing: Theme.AppTheme.spacingSm

            AppControls.PrimaryButton {
                text: "Edit"
                iconName: "edit"
                enabled: !root.isBusy
                onClicked: root.editRequested()
            }

            AppControls.SecondaryButton {
                text: root.storeroomDetail.state && root.storeroomDetail.state.isActive ? "Deactivate" : "Activate"
                iconName: root.storeroomDetail.state && root.storeroomDetail.state.isActive ? "reject" : "approve"
                enabled: !root.isBusy
                onClicked: root.toggleRequested()
            }

            AppControls.SecondaryButton {
                text: "Opening Balance"
                iconName: "import"
                enabled: !root.isBusy
                onClicked: root.openingBalanceRequested()
            }

            Item {
                Layout.fillWidth: true
            }
        }
    }
}

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

    property var workRequestDetail: AppMock.MockFactory.detail()
    property bool isBusy: false
    property var detailPage: null

    signal editRequested()
    signal statusRequested()

    implicitHeight: _mainCol.implicitHeight

    Column {
        id: _mainCol
        width: parent.width
        spacing: 0

        AppWidgets.SectionAnchor { sectionIndex: 0; detailPage: root.detailPage }
        AppWidgets.SectionHeading { width: parent.width; label: "Overview" }

        Item {
            width: parent.width
            height: overviewCol.implicitHeight + Theme.AppTheme.spacingMd * 2

            ColumnLayout {
                id: overviewCol
                anchors {
                    left: parent.left; right: parent.right
                    top: parent.top
                    margins: Theme.AppTheme.spacingMd
                }
                spacing: Theme.AppTheme.spacingMd

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.AppTheme.spacingSm

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: Theme.AppTheme.spacingXs

                        AppControls.Label {
                            Layout.fillWidth: true
                            text: root.workRequestDetail.title || "Work Request Detail"
                            color: Theme.AppTheme.textPrimary
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.bodySize
                            font.bold: true
                            wrapMode: Text.WordWrap
                        }

                        AppControls.Label {
                            Layout.fillWidth: true
                            text: root.workRequestDetail.subtitle || "Select a work request to inspect its intake context, triage state, and update actions."
                            color: Theme.AppTheme.textSecondary
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.smallSize
                            wrapMode: Text.WordWrap
                        }
                    }

                    AppWidgets.StatusChip {
                        visible: String(root.workRequestDetail.statusLabel || "").length > 0
                        status: root.workRequestDetail.statusLabel || ""
                    }
                }

                AppControls.Label {
                    Layout.fillWidth: true
                    visible: String(root.workRequestDetail.emptyState || "").length > 0 && String(root.workRequestDetail.id || "").length === 0
                    text: root.workRequestDetail.emptyState
                    color: Theme.AppTheme.textSecondary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.bodySize
                    wrapMode: Text.WordWrap
                }

                AppControls.Label {
                    Layout.fillWidth: true
                    visible: String(root.workRequestDetail.id || "").length > 0
                    text: root.workRequestDetail.description || ""
                    color: Theme.AppTheme.textPrimary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.bodySize
                    wrapMode: Text.WordWrap
                }
            }
        }

        AppWidgets.SectionAnchor { sectionIndex: 1; detailPage: root.detailPage }
        AppWidgets.SectionHeading { width: parent.width; label: "Details" }

        Item {
            width: parent.width
            height: detailsCol.implicitHeight + Theme.AppTheme.spacingMd * 2
            visible: String(root.workRequestDetail.id || "").length > 0

            ColumnLayout {
                id: detailsCol
                anchors {
                    left: parent.left; right: parent.right
                    top: parent.top
                    margins: Theme.AppTheme.spacingMd
                }
                spacing: Theme.AppTheme.spacingSm

                Repeater {
                    model: root.workRequestDetail.fields || []

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

                            AppControls.Label {
                                Layout.fillWidth: true
                                text: String(fieldCard.modelData.label || "")
                                color: Theme.AppTheme.textMuted
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.smallSize
                                font.bold: true
                            }

                            AppControls.Label {
                                Layout.fillWidth: true
                                text: String(fieldCard.modelData.value || "")
                                color: Theme.AppTheme.textPrimary
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.bodySize
                                wrapMode: Text.WordWrap
                            }

                            AppControls.Label {
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
            }
        }

        AppWidgets.SectionAnchor { sectionIndex: 2; detailPage: root.detailPage }
        AppWidgets.SectionHeading { width: parent.width; label: "Actions" }

        Item {
            width: parent.width
            height: actionsRow.implicitHeight + Theme.AppTheme.spacingMd * 2
            visible: String(root.workRequestDetail.id || "").length > 0

            RowLayout {
                id: actionsRow
                anchors {
                    left: parent.left; right: parent.right
                    top: parent.top
                    margins: Theme.AppTheme.spacingMd
                }
                spacing: Theme.AppTheme.spacingSm

                AppControls.PrimaryButton {
                    text: "Edit"
                    iconName: "edit"
                    enabled: !root.isBusy && !!(root.workRequestDetail.state && root.workRequestDetail.state.canPrimaryAction)
                    onClicked: root.editRequested()
                }

                AppControls.PrimaryButton {
                    text: "Status"
                    iconName: "workflow"
                    enabled: !root.isBusy && !!(root.workRequestDetail.state && root.workRequestDetail.state.canSecondaryAction)
                    onClicked: root.statusRequested()
                }

                Item { Layout.fillWidth: true }
            }
        }
    }
}

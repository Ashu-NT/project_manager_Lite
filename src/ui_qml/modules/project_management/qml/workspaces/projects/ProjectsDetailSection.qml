pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Mock 1.0 as AppMock
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

Item {
    id: root

    property var projectDetail: AppMock.MockFactory.detail()
    property bool isBusy: false
    property var detailPage: null

    signal editRequested()
    signal statusRequested()
    signal deleteRequested()

    implicitHeight: _mainCol.implicitHeight

    Column {
        id: _mainCol
        width: parent.width
        spacing: 0

        // ── Section 0: Overview ──────────────────────────────────────────
        AppWidgets.SectionAnchor { sectionIndex: 0; detailPage: root.detailPage }
        AppWidgets.SectionHeading { label: "Overview" }

        Item {
            width: parent.width
            implicitHeight: overviewContent.implicitHeight + Theme.AppTheme.spacingMd * 2

            ColumnLayout {
                id: overviewContent
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.topMargin: Theme.AppTheme.spacingMd
                anchors.leftMargin: Theme.AppTheme.spacingMd
                anchors.rightMargin: Theme.AppTheme.spacingMd
                anchors.bottomMargin: Theme.AppTheme.spacingMd
                spacing: Theme.AppTheme.spacingMd

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.AppTheme.spacingSm

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: Theme.AppTheme.spacingXs

                        Label {
                            Layout.fillWidth: true
                            text: root.projectDetail.title || "Project Detail"
                            color: Theme.AppTheme.textPrimary
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.bodySize
                            font.bold: true
                            wrapMode: Text.WordWrap
                        }

                        Label {
                            Layout.fillWidth: true
                            text: root.projectDetail.subtitle || "Select a project to inspect details."
                            color: Theme.AppTheme.textSecondary
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.smallSize
                            wrapMode: Text.WordWrap
                        }
                    }

                    AppWidgets.StatusChip {
                        visible: String(root.projectDetail.statusLabel || "").length > 0
                        status: root.projectDetail.statusLabel || ""
                    }
                }

                Label {
                    Layout.fillWidth: true
                    visible: String(root.projectDetail.emptyState || "").length > 0
                        && String(root.projectDetail.id || "").length === 0
                    text: root.projectDetail.emptyState || ""
                    color: Theme.AppTheme.textMuted
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.bodySize
                    wrapMode: Text.WordWrap
                    horizontalAlignment: Text.AlignHCenter
                }

                Label {
                    Layout.fillWidth: true
                    visible: String(root.projectDetail.id || "").length > 0
                        && String(root.projectDetail.description || "").length > 0
                    text: root.projectDetail.description || ""
                    color: Theme.AppTheme.textPrimary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.bodySize
                    wrapMode: Text.WordWrap
                }

                Repeater {
                    model: root.projectDetail.fields || []

                    delegate: Item {
                        id: fieldCard
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
                    visible: String(root.projectDetail.id || "").length > 0
                    spacing: Theme.AppTheme.spacingSm

                    AppControls.PrimaryButton {
                        text: "Edit"
                        iconName: "edit"
                        enabled: !root.isBusy
                        onClicked: root.editRequested()
                    }

                    AppControls.SecondaryButton {
                        text: "Status"
                        iconName: "approve"
                        enabled: !root.isBusy
                        onClicked: root.statusRequested()
                    }

                    AppControls.SecondaryButton {
                        text: "Delete"
                        iconName: "delete"
                        danger: true
                        enabled: !root.isBusy
                        onClicked: root.deleteRequested()
                    }

                    Item { Layout.fillWidth: true }
                }
            }
        }

        // ── Section 1: Activity ──────────────────────────────────────────
        AppWidgets.SectionAnchor { sectionIndex: 1; detailPage: root.detailPage }
        AppWidgets.SectionHeading { label: "Activity" }

        Rectangle {
            width: parent.width
            height: 80
            color: "transparent"

            Label {
                anchors.centerIn: parent
                text: "Project activity feed coming soon"
                color: Theme.AppTheme.textMuted
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.bodySize
            }
        }

        // ── Section 2: Settings ──────────────────────────────────────────
        AppWidgets.SectionAnchor { sectionIndex: 2; detailPage: root.detailPage }
        AppWidgets.SectionHeading { label: "Settings" }

        Rectangle {
            width: parent.width
            height: 80
            color: "transparent"

            Label {
                anchors.centerIn: parent
                text: "Project settings coming soon"
                color: Theme.AppTheme.textMuted
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.bodySize
            }
        }
    }
}

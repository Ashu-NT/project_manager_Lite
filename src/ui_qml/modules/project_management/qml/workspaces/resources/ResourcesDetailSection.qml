pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

Rectangle {
    id: root

    property var resourceDetail: ({
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
    signal toggleRequested()
    signal deleteRequested()

    color: Theme.AppTheme.surface
    border.color: Theme.AppTheme.border
    border.width: 1
    radius: Theme.AppTheme.radiusMd
    clip: true

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        AppWidgets.DetailTabBar {
            id: tabBar
            Layout.fillWidth: true
            tabs: ["Profile", "Assignments", "Capacity"]
            currentIndex: 0
            onTabSelected: function(index) { tabBar.currentIndex = index }
        }

        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: tabBar.currentIndex

            // Tab 0: Profile
            Flickable {
                clip: true
                contentWidth: width
                contentHeight: profileContent.implicitHeight + Theme.AppTheme.spacingLg
                ScrollBar.vertical: ScrollBar {}

                ColumnLayout {
                    id: profileContent
                    width: parent.width
                    anchors.top: parent.top
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.margins: Theme.AppTheme.spacingMd
                    spacing: Theme.AppTheme.spacingMd

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Theme.AppTheme.spacingSm

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: Theme.AppTheme.spacingXs

                            Label {
                                Layout.fillWidth: true
                                text: root.resourceDetail.title || "Resource Detail"
                                color: Theme.AppTheme.textPrimary
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.bodySize
                                font.bold: true
                                wrapMode: Text.WordWrap
                            }

                            Label {
                                Layout.fillWidth: true
                                text: root.resourceDetail.subtitle || "Select a resource to inspect details."
                                color: Theme.AppTheme.textSecondary
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.smallSize
                                wrapMode: Text.WordWrap
                            }
                        }

                        AppWidgets.StatusChip {
                            visible: String(root.resourceDetail.statusLabel || "").length > 0
                            status: root.resourceDetail.statusLabel || ""
                        }
                    }

                    Label {
                        Layout.fillWidth: true
                        visible: String(root.resourceDetail.emptyState || "").length > 0
                            && String(root.resourceDetail.id || "").length === 0
                        text: root.resourceDetail.emptyState || ""
                        color: Theme.AppTheme.textMuted
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.bodySize
                        wrapMode: Text.WordWrap
                        horizontalAlignment: Text.AlignHCenter
                    }

                    Label {
                        Layout.fillWidth: true
                        visible: String(root.resourceDetail.id || "").length > 0
                            && String(root.resourceDetail.description || "").length > 0
                        text: root.resourceDetail.description || ""
                        color: Theme.AppTheme.textPrimary
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.bodySize
                        wrapMode: Text.WordWrap
                    }

                    Repeater {
                        model: root.resourceDetail.fields || []

                        delegate: Rectangle {
                            id: fieldCard
                            required property var modelData

                            Layout.fillWidth: true
                            radius: Theme.AppTheme.radiusMd
                            color: Theme.AppTheme.surfaceAlt
                            implicitHeight: fieldLayout.implicitHeight + Theme.AppTheme.spacingMd * 2

                            ColumnLayout {
                                id: fieldLayout
                                anchors.fill: parent
                                anchors.margins: Theme.AppTheme.spacingMd
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
                        visible: String(root.resourceDetail.id || "").length > 0
                        spacing: Theme.AppTheme.spacingSm

                        AppControls.PrimaryButton {
                            text: "Edit"
                            enabled: !root.isBusy
                            onClicked: root.editRequested()
                        }

                        AppControls.PrimaryButton {
                            text: root.resourceDetail.state && root.resourceDetail.state.isActive
                                ? "Deactivate" : "Activate"
                            enabled: !root.isBusy
                            onClicked: root.toggleRequested()
                        }

                        AppControls.PrimaryButton {
                            text: "Delete"
                            danger: true
                            enabled: !root.isBusy
                            onClicked: root.deleteRequested()
                        }

                        Item { Layout.fillWidth: true }
                    }
                }
            }

            // Tab 1: Assignments (placeholder)
            Item {
                Label {
                    anchors.centerIn: parent
                    text: "Project assignments coming soon"
                    color: Theme.AppTheme.textMuted
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.bodySize
                }
            }

            // Tab 2: Capacity
            Flickable {
                clip: true
                contentWidth: width
                contentHeight: capacityContent.implicitHeight + Theme.AppTheme.spacingLg
                ScrollBar.vertical: ScrollBar {}

                ColumnLayout {
                    id: capacityContent
                    width: parent.width
                    anchors.top: parent.top
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.margins: Theme.AppTheme.spacingMd
                    spacing: Theme.AppTheme.spacingMd

                    Label {
                        Layout.fillWidth: true
                        text: "Capacity"
                        color: Theme.AppTheme.textSecondary
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.captionSize
                        font.bold: true
                    }

                    // Capacity progress bar
                    Rectangle {
                        Layout.fillWidth: true
                        height: 56
                        radius: Theme.AppTheme.radiusMd
                        color: Theme.AppTheme.surfaceAlt

                        readonly property real _capacityValue: {
                            const state = root.resourceDetail.state || {}
                            return parseFloat(state.capacityPercent || "0") / 100.0
                        }
                        readonly property string _capacityLabel: {
                            const state = root.resourceDetail.state || {}
                            return state.capacityLabel || "—"
                        }

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: Theme.AppTheme.spacingMd
                            spacing: Theme.AppTheme.spacingXs

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: Theme.AppTheme.spacingXs

                                Label {
                                    text: "Capacity"
                                    color: Theme.AppTheme.textMuted
                                    font.family: Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.captionSize
                                    font.bold: true
                                }

                                Item { Layout.fillWidth: true }

                                Label {
                                    text: parent.parent.parent._capacityLabel
                                    color: Theme.AppTheme.textPrimary
                                    font.family: Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.captionSize
                                    font.bold: true
                                }
                            }

                            AppWidgets.ProgressBar {
                                Layout.fillWidth: true
                                value: parent.parent._capacityValue
                                implicitHeight: 6
                            }
                        }
                    }

                    // Hourly rate card
                    Rectangle {
                        Layout.fillWidth: true
                        visible: String((root.resourceDetail.state || {}).hourlyRateLabel || "").length > 0
                        height: 44
                        radius: Theme.AppTheme.radiusMd
                        color: Theme.AppTheme.surfaceAlt

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: Theme.AppTheme.spacingMd
                            anchors.rightMargin: Theme.AppTheme.spacingMd
                            spacing: Theme.AppTheme.spacingSm

                            Label {
                                text: "Hourly Rate"
                                color: Theme.AppTheme.textMuted
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.smallSize
                                font.bold: true
                            }

                            Item { Layout.fillWidth: true }

                            Label {
                                text: String((root.resourceDetail.state || {}).hourlyRateLabel || "—")
                                color: Theme.AppTheme.textPrimary
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.bodySize
                                font.bold: true
                            }
                        }
                    }
                }
            }
        }
    }
}

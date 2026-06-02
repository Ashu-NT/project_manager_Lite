pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Widgets 1.0 as AppWidgets
import App.Icons 1.0 as AppIcons
import App.Theme 1.0 as Theme
import App.Controls 1.0 as AppControls

Item {
    id: root

    property bool hasResource: false
    property var availabilityModel: ({
        "resourceId": "", "peakLoadPercent": 0, "averageLoadPercent": 0,
        "overloadedDays": 0, "availableDays": 0, "isAvailable": true,
        "fromDateLabel": "", "toDateLabel": "", "days": []
    })

    implicitHeight: _col.implicitHeight

    Column {
        id: _col
        width: parent.width
        spacing: 0

        AppWidgets.SectionHeading { width: parent.width; label: "Availability" }

        // ── No resource selected ──────────────────────────────────────────
        AppWidgets.EmptyState {
            width: parent.width
            visible: !root.hasResource
            title: "No resource selected"
            message: "Select a resource to review its 90-day capacity outlook."
        }

        // ── Main availability content ─────────────────────────────────────
        ColumnLayout {
            width: parent.width
            spacing: Theme.AppTheme.spacingMd
            visible: root.hasResource

            Item { Layout.preferredHeight: Theme.AppTheme.spacingSm }

            // ── Status header ─────────────────────────────────────────────
            Rectangle {
                Layout.fillWidth: true
                Layout.leftMargin: Theme.AppTheme.marginMd
                Layout.rightMargin: Theme.AppTheme.marginMd
                implicitHeight: _statusRow.implicitHeight + Theme.AppTheme.spacingMd * 2
                radius: Theme.AppTheme.radiusMd
                color: {
                    const over = root.availabilityModel.overloadedDays || 0
                    const peak = root.availabilityModel.peakLoadPercent || 0
                    if (over > 0) return Theme.AppTheme.dangerSoft
                    if (peak >= 80) return Theme.AppTheme.warningSoft
                    return Theme.AppTheme.successSoft
                }
                border.width: 1
                border.color: {
                    const over = root.availabilityModel.overloadedDays || 0
                    const peak = root.availabilityModel.peakLoadPercent || 0
                    if (over > 0) return Theme.AppTheme.dangerSoftBorder
                    if (peak >= 80) return Theme.AppTheme.warningSoftBorder
                    return Theme.AppTheme.successSoftBorder
                }

                RowLayout {
                    id: _statusRow
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    anchors.margins: Theme.AppTheme.spacingMd
                    spacing: Theme.AppTheme.spacingSm

                    AppIcons.AppIcon {
                        name: (root.availabilityModel.overloadedDays || 0) > 0 ? "risk" : "approve"
                        size: Theme.AppTheme.iconMd
                        iconColor: (root.availabilityModel.overloadedDays || 0) > 0
                            ? Theme.AppTheme.danger : Theme.AppTheme.success
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2

                        AppControls.Label {
                            text: (root.availabilityModel.overloadedDays || 0) > 0
                                ? "Capacity conflict detected"
                                : (root.availabilityModel.peakLoadPercent || 0) >= 80
                                    ? "Near capacity threshold"
                                    : "Resource available"
                            color: (root.availabilityModel.overloadedDays || 0) > 0
                                ? Theme.AppTheme.danger
                                : (root.availabilityModel.peakLoadPercent || 0) >= 80
                                    ? Theme.AppTheme.warning
                                    : Theme.AppTheme.success
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.smallSize
                            font.bold: true
                        }

                        AppControls.Label {
                            text: {
                                const from = root.availabilityModel.fromDateLabel || ""
                                const to   = root.availabilityModel.toDateLabel   || ""
                                return (from && to) ? from + "  –  " + to : "90-day outlook"
                            }
                            color: Theme.AppTheme.textMuted
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.captionSize
                        }
                    }
                }
            }

            // ── 4 KPI tiles ───────────────────────────────────────────────
            RowLayout {
                Layout.fillWidth: true
                Layout.leftMargin: Theme.AppTheme.marginMd
                Layout.rightMargin: Theme.AppTheme.marginMd
                spacing: Theme.AppTheme.spacingSm

                Repeater {
                    model: [
                        {
                            label: "Peak Load",
                            value: (root.availabilityModel.peakLoadPercent || 0).toFixed(0) + "%",
                            danger: (root.availabilityModel.peakLoadPercent || 0) > 100,
                            warn:   (root.availabilityModel.peakLoadPercent || 0) >= 80,
                            icon: "dashboard"
                        },
                        {
                            label: "Avg Load",
                            value: (root.availabilityModel.averageLoadPercent || 0).toFixed(0) + "%",
                            danger: false,
                            warn:   false,
                            icon: "financials"
                        },
                        {
                            label: "Overloaded Days",
                            value: String(root.availabilityModel.overloadedDays || 0),
                            danger: (root.availabilityModel.overloadedDays || 0) > 0,
                            warn:   false,
                            icon: "risk"
                        },
                        {
                            label: "Available Days",
                            value: String(root.availabilityModel.availableDays || 0),
                            danger: false,
                            warn:   false,
                            icon: "calendar"
                        }
                    ]

                    delegate: Rectangle {
                        id: _kpiTile
                        required property var modelData
                        Layout.fillWidth: true
                        implicitHeight: _kpiCol.implicitHeight + Theme.AppTheme.spacingMd * 2
                        radius: Theme.AppTheme.radiusMd
                        color: Theme.AppTheme.surfaceOverlay
                        border.color: Theme.AppTheme.subtleBorder
                        border.width: 1

                        ColumnLayout {
                            id: _kpiCol
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.verticalCenter: parent.verticalCenter
                            anchors.margins: Theme.AppTheme.spacingSm
                            spacing: 3

                            AppIcons.AppIcon {
                                name: _kpiTile.modelData.icon
                                size: Theme.AppTheme.iconSm
                                iconColor: _kpiTile.modelData.danger
                                    ? Theme.AppTheme.danger
                                    : _kpiTile.modelData.warn
                                        ? Theme.AppTheme.warning
                                        : Theme.AppTheme.textMuted
                            }

                            AppControls.Label {
                                Layout.fillWidth: true
                                text: _kpiTile.modelData.value
                                color: _kpiTile.modelData.danger
                                    ? Theme.AppTheme.danger
                                    : _kpiTile.modelData.warn
                                        ? Theme.AppTheme.warning
                                        : Theme.AppTheme.textPrimary
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.subtitleSize
                                font.bold: true
                            }

                            AppControls.Label {
                                Layout.fillWidth: true
                                text: _kpiTile.modelData.label
                                color: Theme.AppTheme.textMuted
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.captionSize
                                wrapMode: Text.WordWrap
                            }
                        }
                    }
                }
            }

            // ── Peak load bar ─────────────────────────────────────────────
            ColumnLayout {
                Layout.fillWidth: true
                Layout.leftMargin: Theme.AppTheme.marginMd
                Layout.rightMargin: Theme.AppTheme.marginMd
                spacing: Theme.AppTheme.spacingXs

                RowLayout {
                    Layout.fillWidth: true

                    AppControls.Label {
                        text: "Peak utilisation"
                        color: Theme.AppTheme.textSecondary
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.captionSize
                        font.bold: true
                    }

                    Item { Layout.fillWidth: true }

                    AppControls.Label {
                        text: (root.availabilityModel.peakLoadPercent || 0).toFixed(0) + "% of 100% capacity"
                        color: Theme.AppTheme.textMuted
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.captionSize
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    implicitHeight: 8
                    radius: 4
                    color: Theme.AppTheme.surfaceAlt

                    Rectangle {
                        width: Math.min(parent.width, parent.width * Math.min((root.availabilityModel.peakLoadPercent || 0) / 100.0, 1.5))
                        height: parent.height
                        radius: parent.radius
                        color: (root.availabilityModel.peakLoadPercent || 0) > 100
                            ? Theme.AppTheme.danger
                            : (root.availabilityModel.peakLoadPercent || 0) >= 80
                                ? Theme.AppTheme.warning
                                : Theme.AppTheme.success

                        Behavior on width { NumberAnimation { duration: 400; easing.type: Easing.OutCubic } }
                    }

                    Rectangle {
                        x: parent.width - 1
                        width: 2
                        height: parent.height + 4
                        y: -2
                        radius: 1
                        color: Theme.AppTheme.borderStrong
                    }
                }
            }

            // ── Daily load timeline chart ─────────────────────────────────
            ColumnLayout {
                Layout.fillWidth: true
                Layout.leftMargin: Theme.AppTheme.marginMd
                Layout.rightMargin: Theme.AppTheme.marginMd
                spacing: Theme.AppTheme.spacingXs
                visible: (root.availabilityModel.days || []).length > 0

                AppControls.Label {
                    text: "Daily load — 90-day outlook"
                    color: Theme.AppTheme.textSecondary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.captionSize
                    font.bold: true
                }

                Item {
                    Layout.fillWidth: true
                    implicitHeight: 56

                    Row {
                        anchors.fill: parent
                        spacing: 1

                        Repeater {
                            model: root.availabilityModel.days || []
                            delegate: Item {
                                id: _barItem
                                required property var modelData
                                width: Math.max(2, (parent.width - ((root.availabilityModel.days || []).length - 1)) /
                                       Math.max(1, (root.availabilityModel.days || []).length))
                                height: parent.height

                                readonly property real _pct: Math.min(parseFloat(_barItem.modelData.allocationPercent || 0) / 100.0, 1.5)
                                readonly property real _barH: Math.max(2, Math.round(_barItem._pct * (parent.height - 4)))
                                readonly property color _barColor: _barItem.modelData.overloaded
                                    ? Theme.AppTheme.danger
                                    : parseFloat(_barItem.modelData.allocationPercent || 0) >= 80
                                        ? Theme.AppTheme.warning
                                        : parseFloat(_barItem.modelData.allocationPercent || 0) > 0
                                            ? Theme.AppTheme.success
                                            : Theme.AppTheme.surfaceAlt

                                Rectangle {
                                    anchors.bottom: parent.bottom
                                    anchors.bottomMargin: 2
                                    width: parent.width
                                    height: _barItem._barH
                                    radius: 1
                                    color: _barItem._barColor
                                    opacity: 0.85

                                    ToolTip.visible: _barTip.containsMouse
                                    ToolTip.text: String(_barItem.modelData.dateLabel || "") + ": " + String(_barItem.modelData.allocationLabel || "0%")
                                    ToolTip.delay: 400

                                    MouseArea {
                                        id: _barTip
                                        anchors.fill: parent
                                        hoverEnabled: true
                                    }
                                }
                            }
                        }
                    }

                    Rectangle {
                        anchors.top: parent.top
                        anchors.topMargin: 2
                        width: parent.width
                        height: 1
                        color: Theme.AppTheme.borderStrong
                        opacity: 0.5
                    }
                }

                Row {
                    spacing: Theme.AppTheme.spacingMd

                    Repeater {
                        model: [
                            { color: Theme.AppTheme.success, label: "Available" },
                            { color: Theme.AppTheme.warning, label: "Near limit" },
                            { color: Theme.AppTheme.danger,  label: "Overloaded" }
                        ]
                        delegate: Row {
                            id: _legendRow
                            required property var modelData
                            spacing: Theme.AppTheme.spacingXs
                            Rectangle {
                                width: 10; height: 10
                                radius: 2
                                color: _legendRow.modelData.color
                                anchors.verticalCenter: parent.verticalCenter
                            }
                            AppControls.Label {
                                text: _legendRow.modelData.label
                                color: Theme.AppTheme.textMuted
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.captionSize
                                anchors.verticalCenter: parent.verticalCenter
                            }
                        }
                    }
                }
            }

            AppWidgets.InlineMessage {
                Layout.fillWidth: true
                Layout.leftMargin: Theme.AppTheme.marginMd
                Layout.rightMargin: Theme.AppTheme.marginMd
                visible: (root.availabilityModel.days || []).length === 0
                    && root.hasResource
                tone: "info"
                message: "No active task assignments in the 90-day window. This resource is fully available."
            }

            Item { Layout.preferredHeight: Theme.AppTheme.spacingMd }
        }
    }
}

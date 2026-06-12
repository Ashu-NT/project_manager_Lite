pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import App.Controls 1.0 as AppControls

Item {
    id: root

    property var resourceDetail: ({ "id": "", "title": "", "state": {} })
    property bool isBusy: false

    readonly property bool _hasResource: String(root.resourceDetail.id || "").length > 0

    function _sv(key) {
        const s = root.resourceDetail.state || {}
        return String(s[key] || "")
    }

    implicitHeight: _col.implicitHeight

    Column {
        id: _col
        width: parent.width
        spacing: 0

        AppWidgets.ContextualActionToolbar {
            width: parent.width
            title: root._hasResource ? root.resourceDetail.title : "Capacity"
            subtitle: root._hasResource ? "Portfolio allocation and cost rate configuration" : ""
            busy: root.isBusy
            actions: []
        }

        Item { width: parent.width; implicitHeight: Theme.AppTheme.spacingMd }

        AppWidgets.EmptyState {
            width: parent.width
            visible: !root._hasResource
            title: "No resource selected"
            message: "Select a resource to review its allocation and cost rate configuration."
        }

        ColumnLayout {
            visible: root._hasResource
            width: parent.width
            spacing: Theme.AppTheme.spacingMd

            AppWidgets.InlineMessage {
                Layout.fillWidth: true
                tone: "info"
                message: "Daily capacity is derived from the assigned working calendar and is never stored as a fixed value. The portfolio allocation fraction below configures the share of this resource's time available to PM scheduling. See the Calendar section for the derived capacity breakdown."
            }

            AppWidgets.SectionCard {
                Layout.fillWidth: true
                title: "Portfolio Allocation"
                outlined: true
                implicitHeight: _allocationContent.implicitHeight + Theme.AppTheme.spacingMd * 2

                ColumnLayout {
                    id: _allocationContent
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: Theme.AppTheme.marginMd
                    spacing: Theme.AppTheme.spacingSm

                    RowLayout {
                        Layout.fillWidth: true

                        AppControls.Label {
                            text: "Allocation Fraction"
                            color: Theme.AppTheme.textMuted
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.captionSize
                            font.bold: true
                        }

                        Item { Layout.fillWidth: true }

                        AppControls.Label {
                            text: {
                                const s = root.resourceDetail.state || {}
                                const pct = parseFloat(s.capacityPercent || "0")
                                return String(s.capacityLabel || (pct.toFixed(0) + "%"))
                            }
                            color: Theme.AppTheme.textPrimary
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.captionSize
                            font.bold: true
                        }
                    }

                    AppWidgets.ProgressBar {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 6
                        value: {
                            const s = root.resourceDetail.state || {}
                            return Math.min(parseFloat(s.capacityPercent || "0"), 100.0) / 100.0
                        }
                    }
                }
            }

            AppWidgets.SectionCard {
                Layout.fillWidth: true
                title: "Cost Rate"
                outlined: true
                implicitHeight: _rateGrid.implicitHeight + Theme.AppTheme.spacingMd * 2

                GridLayout {
                    id: _rateGrid
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: Theme.AppTheme.marginMd
                    columns: 2
                    columnSpacing: Theme.AppTheme.spacingLg
                    rowSpacing: Theme.AppTheme.spacingSm

                    Repeater {
                        model: [
                            { "label": "Hourly Rate", "value": root._sv("hourlyRateLabel") || "-" },
                            { "label": "Currency",    "value": root._sv("currency") || "-" },
                            { "label": "Cost Type",   "value": root._sv("costTypeLabel") || "-" },
                            { "label": "Worker Type", "value": root._sv("workerTypeLabel") || "-" }
                        ]

                        delegate: ColumnLayout {
                            required property var modelData
                            Layout.fillWidth: true
                            spacing: 2

                            AppControls.Label {
                                Layout.fillWidth: true
                                text: String(modelData.label || "")
                                color: Theme.AppTheme.textMuted
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.captionSize
                                font.bold: true
                            }

                            AppControls.Label {
                                Layout.fillWidth: true
                                text: String(modelData.value || "-")
                                color: Theme.AppTheme.textPrimary
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.smallSize
                            }
                        }
                    }
                }
            }

            Item { Layout.preferredHeight: Theme.AppTheme.spacingXs }
        }

        Item { width: parent.width; implicitHeight: Theme.AppTheme.spacingMd }
    }
}

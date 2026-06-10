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
            title: root._hasResource ? root.resourceDetail.title : "Cost Rates"
            subtitle: root._hasResource ? "Billing rate, cost classification, and worker type" : ""
            busy: root.isBusy
            actions: []
        }

        Item { width: parent.width; implicitHeight: Theme.AppTheme.spacingMd }

        AppWidgets.EmptyState {
            width: parent.width
            visible: !root._hasResource
            title: "No cost rate data"
            message: "Select a resource to review its cost rate configuration."
        }

        ColumnLayout {
            visible: root._hasResource
            width: parent.width
            spacing: Theme.AppTheme.spacingMd

            AppWidgets.SectionCard {
                Layout.fillWidth: true
                title: "Rate Configuration"
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
                            { "label": "Hourly Rate",  "value": root._sv("hourlyRateLabel") || "-" },
                            { "label": "Currency",     "value": root._sv("currency") || "-" },
                            { "label": "Cost Type",    "value": root._sv("costTypeLabel") || "-" },
                            { "label": "Worker Type",  "value": root._sv("workerTypeLabel") || "-" }
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

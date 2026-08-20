pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import workspaces.scheduling.components 1.0

Item {
    id: root

    property var workspaceController: null
    property var overviewModel: ({ "title": "", "subtitle": "", "metrics": [] })

    readonly property var _primaryKpiLabels: ["Activities", "Critical", "Delayed", "Open ends", "Infeasible", "Overloads"]
    readonly property var _primaryMetrics: (root.overviewModel.metrics || []).filter(function(metric) {
        return root._primaryKpiLabels.indexOf(String(metric.label || "")) >= 0
    })
    readonly property var _secondaryMetrics: (root.overviewModel.metrics || []).filter(function(metric) {
        return root._primaryKpiLabels.indexOf(String(metric.label || "")) < 0
    })
    readonly property string _secondaryMetricsText: root._secondaryMetrics.map(function(metric) {
        return String(metric.label || "") + " " + String(metric.value || "")
    }).join("  |  ")

    readonly property var _criticalRows: root.workspaceController
        ? (root.workspaceController.scheduleRows || []).filter(function(row) {
            const critical = String(row.critical || "")
            return critical === "Critical" || critical === "Infeasible"
        })
        : []
    readonly property var _delayedRows: root.workspaceController ? (root.workspaceController.delayedActivityRows || []) : []
    readonly property var _overloadedRows: root.workspaceController
        ? (root.workspaceController.resourceLoadingRows || []).filter(function(row) {
            return String(row.status || "") === "Overloaded"
        })
        : []

    readonly property var _attentionItems: {
        const items = []
        for (let i = 0; i < root._criticalRows.length; i++) {
            const row = root._criticalRows[i]
            items.push({
                "tone": row.critical === "Infeasible" ? "danger" : "warning",
                "message": String(row.critical || "") + ": " + String(row.taskName || "")
                    + " (WBS " + String(row.wbs || "-") + ", float " + String(row.float || "-") + ")"
            })
        }
        for (let j = 0; j < root._delayedRows.length; j++) {
            const delayed = root._delayedRows[j]
            items.push({
                "tone": "warning",
                "message": "Delayed: " + String(delayed.activity || "") + " (finish " + String(delayed.finish || "-")
                    + ", deadline " + String(delayed.deadline || "-") + ", " + String(delayed.delay || "") + ")"
            })
        }
        for (let k = 0; k < root._overloadedRows.length; k++) {
            const overloaded = root._overloadedRows[k]
            items.push({
                "tone": "danger",
                "message": "Overloaded: " + String(overloaded.resource || "") + " (utilization " + String(overloaded.utilization || "-") + ")"
            })
        }
        return items
    }

    SchedulingPanelFrame {
        anchors.fill: parent
        title: "Overview"
        subtitle: "Current schedule health at a glance."

        ScrollView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.margins: Theme.AppTheme.marginMd
            contentWidth: availableWidth
            clip: true

            ColumnLayout {
                width: parent.width
                spacing: Theme.AppTheme.spacingSm

                AppWidgets.KpiStrip {
                    Layout.fillWidth: true
                    metrics: root._primaryMetrics
                }

                AppControls.Label {
                    Layout.fillWidth: true
                    visible: root._secondaryMetricsText.length > 0
                    text: root._secondaryMetricsText
                    color: Theme.AppTheme.textMuted
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.captionSize
                }

                AppControls.Label {
                    Layout.fillWidth: true
                    Layout.topMargin: Theme.AppTheme.spacingMd
                    text: "What needs attention"
                    color: Theme.AppTheme.textPrimary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                    font.bold: true
                }

                AppWidgets.InlineMessage {
                    Layout.fillWidth: true
                    visible: root._attentionItems.length === 0
                    tone: "success"
                    message: "No critical, delayed, infeasible, or overloaded items -- the schedule is clear."
                }

                Repeater {
                    model: root._attentionItems
                    delegate: AppWidgets.InlineMessage {
                        required property var modelData
                        Layout.fillWidth: true
                        tone: String(modelData.tone || "warning")
                        message: String(modelData.message || "")
                    }
                }

                Item { Layout.preferredHeight: Theme.AppTheme.marginMd }
            }
        }
    }
}

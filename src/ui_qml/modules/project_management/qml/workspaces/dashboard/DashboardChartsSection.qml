pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Theme 1.0 as Theme
import ProjectManagement.Controllers 1.0 as ProjectManagementControllers
import ProjectManagement.Widgets 1.0 as ProjectManagementWidgets

Item {
    id: root

    property ProjectManagementControllers.ProjectManagementDashboardWorkspaceController workspaceController

    readonly property var chartModels: root.workspaceController
        ? (root.workspaceController.charts || [])
        : []
    readonly property var scheduleChart: root.chartModels.length > 0 ? root.chartModels[0] : null
    readonly property var costChart: root.chartModels.length > 1 ? root.chartModels[1] : null
    readonly property var resourceChart: root.chartModels.length > 2 ? root.chartModels[2] : null
    readonly property bool portfolioBarLayout: root.scheduleChart !== null
        && root.costChart !== null
        && String(root.scheduleChart.chartType || "") !== "line"
        && String(root.costChart.chartType || "") !== "line"
    readonly property bool threeColumnBarLayout: root.portfolioBarLayout
        && root.resourceChart !== null
        && String(root.resourceChart.chartType || "") !== "line"
        && width >= 1680
    readonly property bool twoColumnBarLayout: root.portfolioBarLayout
        && !root.threeColumnBarLayout
        && width >= 1100
    readonly property bool splitLayout: !root.portfolioBarLayout
        && width >= 1220
        && root.resourceChart !== null
    readonly property int splitLinePanelHeight: width >= 1680
        ? 228
        : width >= 1440
            ? 206
            : 184
    readonly property int splitResourcePanelHeight: width >= 1680
        ? 456
        : width >= 1440
            ? 412
            : 368
    readonly property int stackedLinePanelHeight: width >= 1280
        ? 268
        : width >= 900
            ? 236
            : 208
    readonly property int stackedBarPanelHeight: width >= 1280
        ? 286
        : width >= 900
            ? 252
            : 224

    implicitHeight: chartsLayout.implicitHeight
    visible: root.chartModels.length > 0

    ColumnLayout {
        id: chartsLayout

        anchors.fill: parent
        spacing: Theme.AppTheme.spacingSm

        GridLayout {
            Layout.fillWidth: true
            columns: root.threeColumnBarLayout ? 3 : (root.twoColumnBarLayout ? 2 : 1)
            columnSpacing: Theme.AppTheme.spacingSm
            rowSpacing: Theme.AppTheme.spacingSm
            visible: root.portfolioBarLayout

            DashboardPanelFrame {
                Layout.fillWidth: true
                Layout.preferredHeight: root.threeColumnBarLayout ? 248 : 214
                Layout.minimumHeight: 190
                title: root.scheduleChart ? root.scheduleChart.title || "Portfolio Status" : ""
                subtitle: root.scheduleChart ? root.scheduleChart.subtitle || "" : ""

                ProjectManagementWidgets.DashboardChartCard {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    title: ""
                    subtitle: ""
                    chartType: root.scheduleChart ? root.scheduleChart.chartType || "bar" : "bar"
                    emptyState: root.scheduleChart ? root.scheduleChart.emptyState || "" : ""
                    points: root.scheduleChart ? (root.scheduleChart.points || []) : []
                }
            }

            DashboardPanelFrame {
                Layout.fillWidth: true
                Layout.preferredHeight: root.threeColumnBarLayout ? 248 : 214
                Layout.minimumHeight: 190
                title: root.costChart ? root.costChart.title || "Cost Pressure" : ""
                subtitle: root.costChart ? root.costChart.subtitle || "" : ""

                ProjectManagementWidgets.DashboardChartCard {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    title: ""
                    subtitle: ""
                    chartType: root.costChart ? root.costChart.chartType || "bar" : "bar"
                    emptyState: root.costChart ? root.costChart.emptyState || "" : ""
                    points: root.costChart ? (root.costChart.points || []) : []
                }
            }

            DashboardPanelFrame {
                Layout.fillWidth: true
                Layout.columnSpan: root.threeColumnBarLayout ? 1 : (root.twoColumnBarLayout ? 2 : 1)
                Layout.preferredHeight: root.threeColumnBarLayout ? 248 : 256
                Layout.minimumHeight: 210
                visible: root.resourceChart !== null
                title: root.resourceChart ? root.resourceChart.title || "Resource Load" : ""
                subtitle: root.resourceChart ? root.resourceChart.subtitle || "" : ""

                ProjectManagementWidgets.DashboardChartCard {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    title: ""
                    subtitle: ""
                    chartType: root.resourceChart ? root.resourceChart.chartType || "bar" : "bar"
                    emptyState: root.resourceChart ? root.resourceChart.emptyState || "" : ""
                    points: root.resourceChart ? (root.resourceChart.points || []) : []
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.AppTheme.spacingSm
            visible: root.splitLayout

            ColumnLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: Theme.AppTheme.spacingSm

                DashboardPanelFrame {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.preferredHeight: root.splitLinePanelHeight
                    Layout.minimumHeight: 156
                    visible: root.scheduleChart !== null
                    title: root.scheduleChart ? root.scheduleChart.title || "Schedule Trend" : ""
                    subtitle: root.scheduleChart ? root.scheduleChart.subtitle || "" : ""

                    ProjectManagementWidgets.DashboardChartCard {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        title: ""
                        subtitle: ""
                        chartType: root.scheduleChart ? root.scheduleChart.chartType || "line" : "line"
                        emptyState: root.scheduleChart ? root.scheduleChart.emptyState || "" : ""
                        points: root.scheduleChart ? (root.scheduleChart.points || []) : []
                    }
                }

                DashboardPanelFrame {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.preferredHeight: root.splitLinePanelHeight
                    Layout.minimumHeight: 156
                    visible: root.costChart !== null
                    title: root.costChart ? root.costChart.title || "Cost Trend" : ""
                    subtitle: root.costChart ? root.costChart.subtitle || "" : ""

                    ProjectManagementWidgets.DashboardChartCard {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        title: ""
                        subtitle: ""
                        chartType: root.costChart ? root.costChart.chartType || "line" : "line"
                        emptyState: root.costChart ? root.costChart.emptyState || "" : ""
                        points: root.costChart ? (root.costChart.points || []) : []
                    }
                }
            }

            DashboardPanelFrame {
                Layout.preferredWidth: Math.max(360, root.width * 0.33)
                Layout.fillHeight: true
                Layout.preferredHeight: root.splitResourcePanelHeight
                Layout.minimumHeight: 248
                visible: root.resourceChart !== null
                title: root.resourceChart ? root.resourceChart.title || "Resource Utilization" : ""
                subtitle: root.resourceChart ? root.resourceChart.subtitle || "" : ""

                ProjectManagementWidgets.DashboardChartCard {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    title: ""
                    subtitle: ""
                    chartType: root.resourceChart ? root.resourceChart.chartType || "bar" : "bar"
                    emptyState: root.resourceChart ? root.resourceChart.emptyState || "" : ""
                    points: root.resourceChart ? (root.resourceChart.points || []) : []
                }
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            spacing: Theme.AppTheme.spacingSm
            visible: !root.splitLayout && !root.portfolioBarLayout

            Repeater {
                model: root.chartModels

                delegate: DashboardPanelFrame {
                    id: stackedChartFrame
                    required property var modelData

                    Layout.fillWidth: true
                    Layout.preferredHeight: String(stackedChartFrame.modelData.chartType || "") === "line"
                        ? root.stackedLinePanelHeight
                        : root.stackedBarPanelHeight
                    Layout.minimumHeight: String(stackedChartFrame.modelData.chartType || "") === "line"
                        ? 176
                        : 190
                    title: stackedChartFrame.modelData.title || ""
                    subtitle: stackedChartFrame.modelData.subtitle || ""

                    ProjectManagementWidgets.DashboardChartCard {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        title: ""
                        subtitle: ""
                        chartType: stackedChartFrame.modelData.chartType || "bar"
                        emptyState: stackedChartFrame.modelData.emptyState || ""
                        points: stackedChartFrame.modelData.points || []
                    }
                }
            }
        }
    }
}

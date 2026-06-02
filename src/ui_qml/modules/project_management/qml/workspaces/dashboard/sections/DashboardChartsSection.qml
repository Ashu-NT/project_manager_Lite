pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Theme 1.0 as Theme
import ProjectManagement.Controllers 1.0 as ProjectManagementControllers
import ProjectManagement.Widgets 1.0 as ProjectManagementWidgets
import "../components"

Item {
    id: root

    property ProjectManagementControllers.ProjectManagementDashboardWorkspaceController workspaceController

    readonly property var chartModels: root.workspaceController
        ? (root.workspaceController.charts || [])
        : []
    readonly property var scheduleChart: root.chartModels.length > 0 ? root.chartModels[0] : null
    readonly property var costChart: root.chartModels.length > 1 ? root.chartModels[1] : null
    readonly property bool portfolioBarLayout: root.scheduleChart !== null
        && root.costChart !== null
        && String(root.scheduleChart.chartType || "") !== "line"
        && String(root.costChart.chartType || "") !== "line"
    readonly property bool twoColumnLayout: width >= 1120
    readonly property int linePanelHeight: width >= 1700
        ? 396
        : width >= 1450
            ? 364
            : width >= 1120
                ? 332
                : width >= 900
                    ? 304
                    : 280
    readonly property int barPanelHeight: width >= 1700
        ? 272
        : width >= 1300
            ? 244
            : 220

    implicitHeight: chartsLayout.implicitHeight
    visible: root.chartModels.length > 0

    ColumnLayout {
        id: chartsLayout

        anchors.fill: parent
        spacing: Theme.AppTheme.spacingSm

        GridLayout {
            Layout.fillWidth: true
            columns: root.twoColumnLayout ? 2 : 1
            columnSpacing: Theme.AppTheme.spacingSm
            rowSpacing: Theme.AppTheme.spacingSm
            visible: root.portfolioBarLayout

            DashboardPanelFrame {
                Layout.fillWidth: true
                Layout.preferredHeight: root.barPanelHeight
                Layout.minimumHeight: 208
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
                Layout.preferredHeight: root.barPanelHeight
                Layout.minimumHeight: 208
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
        }

        GridLayout {
            Layout.fillWidth: true
            columns: root.twoColumnLayout ? 2 : 1
            columnSpacing: Theme.AppTheme.spacingSm
            rowSpacing: Theme.AppTheme.spacingSm
            visible: !root.portfolioBarLayout

            DashboardPanelFrame {
                Layout.fillWidth: true
                Layout.preferredHeight: root.linePanelHeight
                Layout.minimumHeight: 280
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
                Layout.preferredHeight: root.linePanelHeight
                Layout.minimumHeight: 280
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
    }
}


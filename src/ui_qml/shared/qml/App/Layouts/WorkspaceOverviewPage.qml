pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Theme 1.0 as Theme
import App.Widgets 1.0 as AppWidgets
import App.Controls 1.0 as AppControls

// Reusable Overview-page shell: generalizes the KPI-strip + highlight-card +
// activity-feed pattern already proven by Admin Console's own overview data
// and by Control/Settings' own KPI strips (design doc §6/§16). Business
// pages provide the data; this shell only lays it out.
WorkspaceFrame {
    id: root

    // -- KPI row ------------------------------------------------------
    property string metricsHeading: "Workforce"
    property var metrics: []
    property bool metricsClickable: false
    signal metricActivated(int index)

    // -- Highlight cards (small metric-style summary boxes) -----------
    // Each entry: { title, rows: [{ label, value, supportingText }], emptyState }
    property string highlightsHeading: "Access & Governance"
    property var highlightCards: []

    // -- Activity feed --------------------------------------------------
    property string activityTitle: "Recent Activity"
    property var activityItems: []
    property string activityEmptyText: "No recent activity"
    signal activityItemActivated(var item)

    // -- Optional banner (e.g. "breakdowns not yet available") --------
    property string warningText: ""

    // -- Not-yet-backed breakdowns (shown as labeled placeholder cards,
    // not silently omitted) -- each entry: { title, message }
    property string breakdownsHeading: "Coverage"
    property var unavailableBreakdowns: []

    ColumnLayout {
        anchors.fill: parent
        spacing: Theme.AppTheme.sectionGap

        AppControls.Label {
            Layout.fillWidth: true
            visible: root.metricsHeading.length > 0 && root.metrics.length > 0
            text: root.metricsHeading
            color: Theme.AppTheme.textPrimary
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.typePageTitleSize
            font.bold: true
        }

        AppWidgets.KpiStrip {
            Layout.fillWidth: true
            metrics: root.metrics
            clickable: root.metricsClickable
            onMetricActivated: function(index) { root.metricActivated(index) }
        }

        AppControls.Label {
            Layout.fillWidth: true
            visible: root.highlightsHeading.length > 0
                && (root.highlightCards.length > 0 || root.activityItems.length >= 0)
            text: root.highlightsHeading
            color: Theme.AppTheme.textPrimary
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.typePageTitleSize
            font.bold: true
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.AppTheme.sectionGap

            ColumnLayout {
                Layout.preferredWidth: 260
                Layout.fillWidth: false
                Layout.alignment: Qt.AlignTop
                spacing: Theme.AppTheme.spacingMd
                visible: root.highlightCards.length > 0

                Repeater {
                    model: root.highlightCards

                    delegate: Rectangle {
                        id: _cardRow
                        required property var modelData

                        Layout.fillWidth: true
                        implicitHeight: _card.implicitHeight + Theme.AppTheme.marginMd * 2
                        radius: Theme.AppTheme.radiusMd
                        color: Theme.AppTheme.surfaceRaised

                        AppWidgets.OverviewSectionCard {
                            id: _card
                            anchors.fill: parent
                            anchors.margins: Theme.AppTheme.marginMd
                            title: String(_cardRow.modelData.title || "")
                            rows: _cardRow.modelData.rows || []
                            emptyState: String(_cardRow.modelData.emptyState || "")
                        }
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.alignment: Qt.AlignTop
                implicitHeight: Math.max(_activityCol.implicitHeight + Theme.AppTheme.marginMd * 2, 120)
                radius: Theme.AppTheme.radiusMd
                color: Theme.AppTheme.surfaceRaised

                ColumnLayout {
                    id: _activityCol
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: Theme.AppTheme.marginMd
                    spacing: Theme.AppTheme.spacingSm

                    AppControls.Label {
                        Layout.fillWidth: true
                        text: root.activityTitle
                        color: Theme.AppTheme.textPrimary
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.bodySize
                        font.bold: true
                    }

                    AppWidgets.ActivityFeed {
                        Layout.fillWidth: true
                        items: root.activityItems
                        emptyText: root.activityEmptyText
                        onItemActivated: function(item) { root.activityItemActivated(item) }
                    }
                }
            }
        }

        AppControls.Label {
            Layout.fillWidth: true
            visible: root.breakdownsHeading.length > 0 && root.unavailableBreakdowns.length > 0
            text: root.breakdownsHeading
            color: Theme.AppTheme.textPrimary
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.typePageTitleSize
            font.bold: true
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.AppTheme.sectionGap
            visible: root.unavailableBreakdowns.length > 0

            Repeater {
                model: root.unavailableBreakdowns

                delegate: Rectangle {
                    id: _breakdownCard
                    required property var modelData

                    Layout.fillWidth: true
                    Layout.preferredHeight: 96
                    radius: Theme.AppTheme.radiusMd
                    color: Theme.AppTheme.surfaceRaised
                    border.color: Theme.AppTheme.divider
                    border.width: Theme.AppTheme.borderWidthThin

                    AppWidgets.EmptyState {
                        anchors.fill: parent
                        title: String(_breakdownCard.modelData.title || "")
                        message: String(_breakdownCard.modelData.message || "Not yet available")
                    }
                }
            }
        }

        AppWidgets.InlineMessage {
            Layout.fillWidth: true
            visible: root.warningText.length > 0
            tone: "warning"
            message: root.warningText
        }
    }
}

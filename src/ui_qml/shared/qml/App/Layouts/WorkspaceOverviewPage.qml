pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Theme 1.0 as Theme
import App.Widgets 1.0 as AppWidgets
import App.Controls 1.0 as AppControls

// Reusable Overview-page shell: generalizes the KPI-strip + highlight-card +
// breakdown-card pattern already proven by Admin Console's own overview data
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

    // -- Optional banner (e.g. "breakdowns not yet available") --------
    property string warningText: ""

    // -- Breakdown cards (same shape as highlightCards) ----------------
    // Each entry: { title, rows: [{ label, value, supportingText }], emptyState }
    property string breakdownsHeading: "Workforce Breakdown"
    property var breakdownCards: []

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
            visible: root.highlightsHeading.length > 0 && root.highlightCards.length > 0
            text: root.highlightsHeading
            color: Theme.AppTheme.textPrimary
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.typePageTitleSize
            font.bold: true
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.AppTheme.sectionGap
            visible: root.highlightCards.length > 0

            Repeater {
                model: root.highlightCards

                delegate: Rectangle {
                    id: _cardRow
                    required property var modelData

                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignTop
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

        AppControls.Label {
            Layout.fillWidth: true
            visible: root.breakdownsHeading.length > 0 && root.breakdownCards.length > 0
            text: root.breakdownsHeading
            color: Theme.AppTheme.textPrimary
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.typePageTitleSize
            font.bold: true
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.AppTheme.sectionGap
            visible: root.breakdownCards.length > 0

            Repeater {
                model: root.breakdownCards

                delegate: Rectangle {
                    id: _breakdownCard
                    required property var modelData

                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignTop
                    implicitHeight: _breakdownCardContent.implicitHeight + Theme.AppTheme.marginMd * 2
                    radius: Theme.AppTheme.radiusMd
                    color: Theme.AppTheme.surfaceRaised

                    AppWidgets.OverviewSectionCard {
                        id: _breakdownCardContent
                        anchors.fill: parent
                        anchors.margins: Theme.AppTheme.marginMd
                        title: String(_breakdownCard.modelData.title || "")
                        rows: _breakdownCard.modelData.rows || []
                        emptyState: String(_breakdownCard.modelData.emptyState || "Not yet available")
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

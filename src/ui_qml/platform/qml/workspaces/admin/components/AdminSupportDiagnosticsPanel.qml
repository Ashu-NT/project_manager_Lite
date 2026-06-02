pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

ColumnLayout {
    id: root

    property var  bundleState: ({})
    property bool isBusy:      false
    property string incidentId: ""

    signal exportDiagnosticsRequested()
    signal reportIncidentRequested()
    signal newIncidentIdRequested()
    signal copyIncidentIdRequested()
    signal setIncidentIdRequested(string id)
    signal openLatestDiagnosticsRequested()
    signal openLatestIncidentReportRequested()

    onIncidentIdChanged: incidentField.text = root.incidentId

    Layout.fillWidth: true
    spacing: 0

    AppWidgets.SectionHeading { Layout.fillWidth: true; label: "Incident Diagnostics" }

    // Active trace panel
    Rectangle {
        Layout.fillWidth: true
        implicitHeight:   _tracePanel.implicitHeight + Theme.AppTheme.spacingSm * 2
        color:            Theme.AppTheme.surfaceOverlay

        Rectangle { anchors { bottom: parent.bottom; left: parent.left; right: parent.right }; height: 1; color: Theme.AppTheme.divider }

        ColumnLayout {
            id: _tracePanel
            anchors { left: parent.left; right: parent.right; top: parent.top; leftMargin: Theme.AppTheme.marginMd; rightMargin: Theme.AppTheme.marginMd; topMargin: Theme.AppTheme.spacingSm }
            spacing: Theme.AppTheme.spacingXs

            AppControls.Label { text: "ACTIVE TRACE"; color: Theme.AppTheme.textMuted; font.family: Theme.AppTheme.fontFamily; font.pixelSize: Theme.AppTheme.captionSize; font.bold: true; font.letterSpacing: 0.8 }

            RowLayout {
                Layout.fillWidth: true; spacing: Theme.AppTheme.spacingSm

                AppControls.TextField {
                    id: incidentField
                    Layout.fillWidth: true
                    enabled:         !root.isBusy
                    placeholderText: "Incident trace ID"
                    onEditingFinished: root.setIncidentIdRequested(text.trim())
                }
                AppControls.SecondaryButton { text: "New Trace"; iconName: "add";    enabled: !root.isBusy; onClicked: root.newIncidentIdRequested() }
                AppControls.SecondaryButton { text: "Copy";      iconName: "export"; enabled: !root.isBusy; onClicked: root.copyIncidentIdRequested() }
            }
        }
    }

    SupportPathRow {
        rowLabel: "Last Diagnostics";    rowValue: String(root.bundleState.lastDiagnosticsPath || "")
        canOpen:  String(root.bundleState.lastDiagnosticsUrl || "").length > 0
        onOpenRequested: root.openLatestDiagnosticsRequested()
    }
    SupportPathRow {
        rowLabel: "Last Incident Report"; rowValue: String(root.bundleState.lastIncidentReportPath || "")
        canOpen:  String(root.bundleState.lastIncidentReportUrl || "").length > 0
        onOpenRequested: root.openLatestIncidentReportRequested()
    }

    // Diagnostics action bar
    Rectangle {
        Layout.fillWidth: true; Layout.preferredHeight: Theme.AppTheme.toolbarHeight
        color: Theme.AppTheme.surfaceOverlay

        Rectangle { anchors { top: parent.top; left: parent.left; right: parent.right }; height: 1; color: Theme.AppTheme.divider }
        Rectangle { anchors { bottom: parent.bottom; left: parent.left; right: parent.right }; height: 1; color: Theme.AppTheme.divider }

        RowLayout {
            anchors.fill: parent; anchors.leftMargin: Theme.AppTheme.marginMd; anchors.rightMargin: Theme.AppTheme.marginMd
            spacing: Theme.AppTheme.spacingSm

            AppControls.SecondaryButton { text: "Export Diagnostics"; iconName: "export"; enabled: !root.isBusy; onClicked: root.exportDiagnosticsRequested() }
            AppControls.PrimaryButton   { text: "Report Incident";    iconName: "approve"; enabled: !root.isBusy; onClicked: root.reportIncidentRequested() }
            Item { Layout.fillWidth: true }
        }
    }
}

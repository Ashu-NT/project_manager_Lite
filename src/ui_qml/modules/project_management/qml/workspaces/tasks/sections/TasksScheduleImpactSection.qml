pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import App.Controls 1.0 as AppControls

Item {
    id: root

    property var scheduleImpactModel: ({
        "available": false, "taskId": "", "summary": "Select a task to view schedule impact analysis.",
        "rows": [], "affectedCount": 0, "maxProjectFinishShiftDays": 0,
        "requiresApproval": false, "approvalLabel": "",
        "newlyCriticalCount": 0, "noLongerCriticalCount": 0
    })
    property var sectionErrors: ({})
    property bool isBusy: false

    implicitHeight: _impactCol.implicitHeight

    ColumnLayout {
        id: _impactCol
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        spacing: 0

        AppWidgets.ContextualActionToolbar {
            Layout.fillWidth: true
            title: "Schedule Impact"
            subtitle: String(root.scheduleImpactModel.summary || "Simulating a 1-day start slip to show downstream ripple.")
            busy: root.isBusy
            actions: []
        }

        AppWidgets.InlineMessage {
            Layout.fillWidth: true
            visible: String(root.sectionErrors["scheduleImpact"] || "").length > 0
            tone: "danger"
            message: String(root.sectionErrors["scheduleImpact"] || "")
        }

        AppWidgets.InlineMessage {
            Layout.fillWidth: true
            Layout.leftMargin: Theme.AppTheme.marginMd
            Layout.rightMargin: Theme.AppTheme.marginMd
            Layout.topMargin: Theme.AppTheme.spacingSm
            visible: root.scheduleImpactModel.requiresApproval === true
            tone: "warning"
            message: "A change of this magnitude would require baseline approval."
        }

        AppWidgets.EmptyState {
            Layout.fillWidth: true
            visible: root.scheduleImpactModel.available !== true
            title: "Schedule impact analysis not available."
            message: String(root.scheduleImpactModel.summary
                || "This task needs a start date and a connected scheduling service.")
        }

        Repeater {
            model: root.scheduleImpactModel.available === true
                ? (root.scheduleImpactModel.rows || [])
                : []

            delegate: ColumnLayout {
                id: _impactRow
                required property var modelData
                Layout.fillWidth: true
                spacing: 0

                RowLayout {
                    Layout.fillWidth: true
                    Layout.leftMargin: Theme.AppTheme.marginMd
                    Layout.rightMargin: Theme.AppTheme.marginMd
                    Layout.topMargin: Theme.AppTheme.spacingSm
                    Layout.bottomMargin: Theme.AppTheme.spacingSm
                    spacing: Theme.AppTheme.spacingMd

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2

                        AppControls.Label {
                            Layout.fillWidth: true
                            text: String(_impactRow.modelData.taskName || "")
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.smallSize
                            font.bold: _impactRow.modelData.isChanged === true
                            color: _impactRow.modelData.isChanged === true
                                ? Theme.AppTheme.textAccent
                                : Theme.AppTheme.textPrimary
                        }

                        AppControls.Label {
                            Layout.fillWidth: true
                            text: "Start " + String(_impactRow.modelData.startShift || "No change")
                                + "  |  Finish " + String(_impactRow.modelData.finishShift || "No change")
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.captionSize
                            color: Theme.AppTheme.textSecondary
                        }
                    }

                    AppWidgets.StatusChip {
                        visible: String(_impactRow.modelData.criticalLabel || "").length > 0
                        status: String(_impactRow.modelData.criticalLabel || "")
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    height: 1
                    color: Theme.AppTheme.divider
                }
            }
        }

        AppWidgets.EmptyState {
            Layout.fillWidth: true
            visible: root.scheduleImpactModel.available === true
                && (root.scheduleImpactModel.rows || []).length === 0
            title: "No downstream tasks would be affected."
            message: "A 1-day start slip on this task would not shift any other scheduled tasks."
        }
    }
}

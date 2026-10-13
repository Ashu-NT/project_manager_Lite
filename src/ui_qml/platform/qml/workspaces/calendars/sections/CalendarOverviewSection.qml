pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

// Calendar Detail's Overview tab: Calendar Information / Standard Working
// Week / Operational Rules (main column) plus Usage / Upcoming Exceptions /
// Recent Activity / Related Actions (summary rail) -- the same information
// architecture as Site/Organization Overview, specialized for Calendar's
// own richer engine without exposing its backend tables as separate tabs.
// A presentational section only -- all data is supplied by the orchestrator
// (AdminCalendarDetailPage.qml).
Column {
    id: root
    spacing: 0

    property var calendarInfoFields: []
    property var workingRules: []
    property int exceptionsCount: 0
    property int recurringRulesCount: 0
    property string shiftPatternLabel: ""
    property var usage: ({
        "isOrganizationDefault": false, "sites": 0, "departments": 0,
        "employees": 0, "projects": 0, "resources": 0
    })
    property var upcomingExceptions: []
    property var recentActivity: []

    signal manageExceptionsRequested()
    signal manageRecurringRulesRequested()
    signal viewAllActivityRequested()
    signal navigateToDestination(string destinationId)

    readonly property var _weekdayNames: [
        "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"
    ]
    readonly property var _weekRows: {
        const rows = []
        for (let day = 0; day < 7; day += 1) {
            let rule = null
            for (let i = 0; i < root.workingRules.length; i += 1) {
                if (root.workingRules[i].weekday === day) { rule = root.workingRules[i]; break }
            }
            rows.push({
                "dayLabel": root._weekdayNames[day],
                "isWorkingDay": rule ? !!rule.isWorkingDay : false,
                "timeLabel": (rule && rule.isWorkingDay)
                    ? String(rule.startTime || "-") + " – " + String(rule.endTime || "-")
                    : "Non-working",
                "hoursLabel": (rule && rule.isWorkingDay && rule.computedHours)
                    ? (Number(rule.computedHours) % 1 === 0
                        ? Number(rule.computedHours) + " h"
                        : Number(rule.computedHours).toFixed(1) + " h")
                    : "",
                "breakLabel": (rule && rule.isWorkingDay && rule.breakStartTime && rule.breakEndTime)
                    ? String(rule.breakStartTime) + " – " + String(rule.breakEndTime)
                    : ""
            })
        }
        return rows
    }
    readonly property var _operationalRuleRows: {
        const rows = []
        rows.push({ "label": "Exceptions", "value": String(root.exceptionsCount) + " configured", "actionId": "exceptions" })
        rows.push({ "label": "Recurring Rules", "value": String(root.recurringRulesCount) + (root.recurringRulesCount === 1 ? " active" : " active"), "actionId": "recurring" })
        if (root.shiftPatternLabel.length > 0) {
            rows.push({ "label": "Shift Pattern", "value": root.shiftPatternLabel, "actionId": "" })
        }
        return rows
    }
    readonly property var _usageRows: {
        const rows = []
        rows.push({ "label": "Organization Default", "value": root.usage.isOrganizationDefault ? "Yes" : "No" })
        if (root.usage.sites > 0) rows.push({ "label": "Sites", "value": String(root.usage.sites) })
        if (root.usage.departments > 0) rows.push({ "label": "Departments", "value": String(root.usage.departments) })
        if (root.usage.employees > 0) rows.push({ "label": "Employees", "value": String(root.usage.employees) })
        if (root.usage.projects > 0) rows.push({ "label": "Projects", "value": String(root.usage.projects) })
        if (root.usage.resources > 0) rows.push({ "label": "Resources", "value": String(root.usage.resources) })
        return rows
    }
    readonly property var _relatedActions: [
        { "id": "assignments", "label": "View Assignments", "icon": "chevron_right" },
        { "id": "activity", "label": "View Activity", "icon": "history" }
    ]

    function _onOperationalRuleActivated(actionId) {
        if (actionId === "exceptions") root.manageExceptionsRequested()
        else if (actionId === "recurring") root.manageRecurringRulesRequested()
    }

    Item {
        width: root.width
        implicitHeight: overviewGrid.implicitHeight + Theme.AppTheme.spacingMd * 2

        GridLayout {
            id: overviewGrid
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.margins: Theme.AppTheme.spacingMd
            columns: root.width < 640 ? 1 : 2
            columnSpacing: Theme.AppTheme.spacingMd
            rowSpacing: Theme.AppTheme.spacingMd

            // -- Main column: Calendar Information / Standard Working Week /
            // Operational Rules -- ~2/3 width on desktop.
            ColumnLayout {
                Layout.fillWidth: true
                Layout.preferredWidth: overviewGrid.columns === 2
                    ? Math.round(overviewGrid.width * 0.66)
                    : overviewGrid.width
                Layout.alignment: Qt.AlignTop
                spacing: Theme.AppTheme.spacingMd

                AppWidgets.SectionCard {
                    Layout.fillWidth: true
                    title: "Calendar Information"
                    outlined: true

                    GridLayout {
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.margins: Theme.AppTheme.marginMd
                        columns: 2
                        columnSpacing: Theme.AppTheme.spacingLg
                        rowSpacing: Theme.AppTheme.spacingSm

                        Repeater {
                            model: root.calendarInfoFields

                            delegate: ColumnLayout {
                                required property var modelData
                                Layout.fillWidth: true
                                spacing: 2

                                AppControls.Label {
                                    Layout.fillWidth: true
                                    text: String(modelData.label || "")
                                    color: Theme.AppTheme.textMuted
                                    font.pixelSize: Theme.AppTheme.captionSize
                                    font.bold: true
                                }

                                AppControls.Label {
                                    Layout.fillWidth: true
                                    text: String(modelData.value || "-")
                                    color: Theme.AppTheme.textPrimary
                                    font.pixelSize: Theme.AppTheme.smallSize
                                    wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                                }
                            }
                        }
                    }
                }

                AppWidgets.SectionCard {
                    Layout.fillWidth: true
                    title: "Standard Working Week"
                    outlined: true

                    ColumnLayout {
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.margins: Theme.AppTheme.marginMd
                        spacing: Theme.AppTheme.spacingXs

                        Repeater {
                            model: root._weekRows

                            delegate: RowLayout {
                                required property var modelData
                                Layout.fillWidth: true
                                spacing: Theme.AppTheme.spacingSm

                                AppControls.Label {
                                    Layout.preferredWidth: 100
                                    text: String(modelData.dayLabel)
                                    color: Theme.AppTheme.textPrimary
                                    font.pixelSize: Theme.AppTheme.smallSize
                                    font.bold: modelData.isWorkingDay
                                }

                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 0

                                    AppControls.Label {
                                        text: String(modelData.timeLabel)
                                        color: modelData.isWorkingDay ? Theme.AppTheme.textPrimary : Theme.AppTheme.textMuted
                                        font.pixelSize: Theme.AppTheme.smallSize
                                    }

                                    AppControls.Label {
                                        visible: String(modelData.breakLabel || "").length > 0
                                        text: "Break  " + String(modelData.breakLabel)
                                        color: Theme.AppTheme.textMuted
                                        font.pixelSize: Theme.AppTheme.captionSize
                                    }
                                }

                                AppControls.Label {
                                    Layout.alignment: Qt.AlignRight
                                    visible: String(modelData.hoursLabel || "").length > 0
                                    text: String(modelData.hoursLabel)
                                    color: Theme.AppTheme.textMuted
                                    font.pixelSize: Theme.AppTheme.smallSize
                                }
                            }
                        }
                    }
                }

                AppWidgets.SectionCard {
                    Layout.fillWidth: true
                    title: "Operational Rules"
                    outlined: true

                    ColumnLayout {
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.margins: Theme.AppTheme.marginMd
                        spacing: Theme.AppTheme.spacingSm

                        Repeater {
                            model: root._operationalRuleRows

                            delegate: RowLayout {
                                required property var modelData
                                Layout.fillWidth: true
                                spacing: Theme.AppTheme.spacingSm

                                AppControls.Label {
                                    Layout.fillWidth: true
                                    text: String(modelData.label) + "  —  " + String(modelData.value)
                                    color: Theme.AppTheme.textPrimary
                                    font.pixelSize: Theme.AppTheme.smallSize
                                }

                                AppControls.Label {
                                    visible: String(modelData.actionId || "").length > 0
                                    text: modelData.actionId === "exceptions" ? "Manage Exceptions" : "Manage Recurring Rules"
                                    color: Theme.AppTheme.accent
                                    font.pixelSize: Theme.AppTheme.smallSize
                                    font.bold: true

                                    HoverHandler { cursorShape: Qt.PointingHandCursor }
                                    TapHandler { onTapped: root._onOperationalRuleActivated(modelData.actionId) }
                                }
                            }
                        }
                    }
                }
            }

            // -- Summary rail: Usage, Upcoming Exceptions, Recent Activity,
            // Related Actions -- one consolidated column (~1/3 width).
            ColumnLayout {
                Layout.fillWidth: true
                Layout.preferredWidth: overviewGrid.columns === 2
                    ? overviewGrid.width - Math.round(overviewGrid.width * 0.66) - overviewGrid.columnSpacing
                    : overviewGrid.width
                Layout.alignment: Qt.AlignTop
                spacing: Theme.AppTheme.spacingMd

                AppWidgets.SectionCard {
                    Layout.fillWidth: true
                    title: "Usage"
                    outlined: true

                    ColumnLayout {
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.margins: Theme.AppTheme.marginMd
                        spacing: Theme.AppTheme.spacingXs

                        Repeater {
                            model: root._usageRows

                            delegate: RowLayout {
                                required property var modelData
                                Layout.fillWidth: true
                                spacing: Theme.AppTheme.spacingSm

                                AppControls.Label {
                                    text: String(modelData.label)
                                    color: Theme.AppTheme.textMuted
                                    font.pixelSize: Theme.AppTheme.captionSize
                                }

                                Item { Layout.fillWidth: true }

                                AppControls.Label {
                                    text: String(modelData.value)
                                    color: Theme.AppTheme.textPrimary
                                    font.pixelSize: Theme.AppTheme.captionSize
                                    font.bold: true
                                }
                            }
                        }

                        AppControls.Label {
                            Layout.fillWidth: true
                            Layout.alignment: Qt.AlignRight
                            Layout.topMargin: Theme.AppTheme.spacingXs
                            horizontalAlignment: Text.AlignRight
                            text: "View Assignments"
                            color: Theme.AppTheme.accent
                            font.pixelSize: Theme.AppTheme.smallSize
                            font.bold: true

                            HoverHandler { cursorShape: Qt.PointingHandCursor }
                            TapHandler { onTapped: root.navigateToDestination("assignments") }
                        }
                    }
                }

                AppWidgets.SectionCard {
                    Layout.fillWidth: true
                    title: "Upcoming Exceptions"
                    outlined: true

                    ColumnLayout {
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.margins: Theme.AppTheme.marginMd
                        spacing: Theme.AppTheme.spacingSm

                        AppControls.Label {
                            Layout.fillWidth: true
                            visible: root.upcomingExceptions.length === 0
                            text: "No upcoming exceptions configured for this calendar."
                            color: Theme.AppTheme.textMuted
                            font.pixelSize: Theme.AppTheme.smallSize
                            wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                        }

                        Repeater {
                            model: root.upcomingExceptions

                            delegate: ColumnLayout {
                                required property var modelData
                                Layout.fillWidth: true
                                spacing: 0

                                AppControls.Label {
                                    Layout.fillWidth: true
                                    text: String(modelData.exceptionDate) + "  ·  " + String(modelData.name)
                                    color: Theme.AppTheme.textPrimary
                                    font.pixelSize: Theme.AppTheme.smallSize
                                    font.bold: true
                                    wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                                }
                                AppControls.Label {
                                    Layout.fillWidth: true
                                    text: String(modelData.impactType).toLowerCase() === "unavailable" ? "Non-working" : String(modelData.impactType)
                                    color: Theme.AppTheme.textMuted
                                    font.pixelSize: Theme.AppTheme.captionSize
                                }
                            }
                        }

                        AppControls.Label {
                            Layout.fillWidth: true
                            Layout.alignment: Qt.AlignRight
                            horizontalAlignment: Text.AlignRight
                            text: "View Calendar →"
                            color: Theme.AppTheme.accent
                            font.pixelSize: Theme.AppTheme.smallSize
                            font.bold: true

                            HoverHandler { cursorShape: Qt.PointingHandCursor }
                            TapHandler { onTapped: root.navigateToDestination("calendar") }
                        }
                    }
                }

                AppWidgets.SectionCard {
                    Layout.fillWidth: true
                    title: "Recent Activity"
                    outlined: true

                    ColumnLayout {
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.margins: Theme.AppTheme.marginMd
                        spacing: Theme.AppTheme.spacingSm

                        AppControls.Label {
                            Layout.alignment: Qt.AlignRight
                            visible: (root.recentActivity || []).length > 0
                            text: "View all"
                            color: Theme.AppTheme.accent
                            font.pixelSize: Theme.AppTheme.smallSize
                            font.bold: true

                            HoverHandler { cursorShape: Qt.PointingHandCursor }
                            TapHandler { onTapped: root.viewAllActivityRequested() }
                        }

                        AppWidgets.ActivityFeed {
                            Layout.fillWidth: true
                            items: root.recentActivity || []
                            emptyText: "No activity yet. Business activity for this calendar will appear here."
                        }
                    }
                }

                AppWidgets.SectionCard {
                    Layout.fillWidth: true
                    title: "Related Actions"
                    outlined: true

                    ColumnLayout {
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.margins: Theme.AppTheme.marginMd
                        spacing: Theme.AppTheme.spacingSm

                        Repeater {
                            model: root._relatedActions

                            delegate: AppWidgets.ActionTile {
                                required property var modelData
                                Layout.fillWidth: true

                                label: String(modelData.label || "")
                                iconName: String(modelData.icon || "")

                                onActivated: root.navigateToDestination(String(modelData.id || ""))
                            }
                        }
                    }
                }
            }
        }
    }
}

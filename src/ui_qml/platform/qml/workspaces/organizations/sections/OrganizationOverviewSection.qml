pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

// Organization Detail's Overview tab: Basic Information / Registered
// Address / Contact (main column) plus Key Statistics / Recent Activity /
// Related Actions (summary rail + full-width tile row). A presentational
// section only -- all data and the isDestinationAccessible check are
// supplied by the orchestrator (AdminOrganizationDetailPage.qml).
Column {
    id: root
    spacing: 0

    property var basicInfoFields: []
    property var addressFields: []
    property var contactFields: []
    property var statistics: ({})
    property var relatedActions: []
    property var recentActivity: []
    property var isDestinationAccessible: function(_destinationId) { return false }
    property var calendarSummary: ({
        "hasCalendar": false, "calendarName": "", "workingWeekLabel": "",
        "timeZone": "", "holidaySetLabel": ""
    })

    signal navigateToDestination(string destinationId)
    signal viewAllActivityRequested()
    signal manageCalendarRequested()

    // Real backend/read-model fields only -- see build_calendar_summary()
    // (organization_catalog_presenter.py). No calendar identifiers are ever
    // shown here, only the display labels already resolved server-side.
    readonly property var _calendarFields: root.calendarSummary.hasCalendar ? [
        { "label": "Default Calendar", "value": String(root.calendarSummary.calendarName || "-") },
        { "label": "Working Week", "value": String(root.calendarSummary.workingWeekLabel || "-") },
        { "label": "Time Zone", "value": String(root.calendarSummary.timeZone || "-") },
        { "label": "Holiday Set", "value": String(root.calendarSummary.holidaySetLabel || "-") }
    ] : []

    Item {
        width: root.width
        implicitHeight: overviewGrid.implicitHeight + Theme.AppTheme.spacingMd * 2

        GridLayout {
            id: overviewGrid
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.margins: Theme.AppTheme.spacingMd
            // root.width is the section CONTENT column, already net of the
            // shell/platform/detail-page nav rails -- not the window width.
            // 640 keeps both 1600x1000 and 1366x768 desktop breakpoints
            // two-column while a ~1000px window (content ~290px) still stacks.
            columns: root.width < 640 ? 1 : 2
            columnSpacing: Theme.AppTheme.spacingMd
            rowSpacing: Theme.AppTheme.spacingMd

            // -- Main column: Basic Information / Registered Address / Contact
            // ~2/3 width on desktop; content-driven height only -- never a
            // fixed/computed override that can under-report a card's real
            // height and get clipped by SectionCard's own clip: true.
            ColumnLayout {
                Layout.fillWidth: true
                Layout.preferredWidth: overviewGrid.columns === 2
                    ? Math.round(overviewGrid.width * 0.66)
                    : overviewGrid.width
                Layout.alignment: Qt.AlignTop
                spacing: Theme.AppTheme.spacingMd

                AppWidgets.SectionCard {
                    Layout.fillWidth: true
                    title: "Basic Information"
                    outlined: true

                    GridLayout {
                        id: basicInfoGrid
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.margins: Theme.AppTheme.marginMd
                        columns: 2
                        columnSpacing: Theme.AppTheme.spacingLg
                        rowSpacing: Theme.AppTheme.spacingSm

                        Repeater {
                            model: root.basicInfoFields

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
                    title: "Registered Address"
                    outlined: true

                    GridLayout {
                        id: addressGrid
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.margins: Theme.AppTheme.marginMd
                        columns: 2
                        columnSpacing: Theme.AppTheme.spacingLg
                        rowSpacing: Theme.AppTheme.spacingSm

                        Repeater {
                            model: root.addressFields

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
                    title: "Contact Information"
                    outlined: true

                    GridLayout {
                        id: contactGrid
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.margins: Theme.AppTheme.marginMd
                        columns: 2
                        columnSpacing: Theme.AppTheme.spacingLg
                        rowSpacing: Theme.AppTheme.spacingSm

                        Repeater {
                            model: root.contactFields

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
            }

            // -- Summary rail: statistics + activity + actions (~1/3 width)
            ColumnLayout {
                Layout.fillWidth: true
                Layout.preferredWidth: overviewGrid.columns === 2
                    ? overviewGrid.width - Math.round(overviewGrid.width * 0.66) - overviewGrid.columnSpacing
                    : overviewGrid.width
                Layout.alignment: Qt.AlignTop
                spacing: Theme.AppTheme.spacingMd

                AppWidgets.SectionCard {
                    Layout.fillWidth: true
                    title: "Key Statistics"
                    outlined: true

                    GridLayout {
                        id: statsGrid
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.margins: Theme.AppTheme.marginMd
                        columns: 2
                        columnSpacing: Theme.AppTheme.spacingSm
                        rowSpacing: Theme.AppTheme.spacingSm

                        AppWidgets.OverviewMetricTile {
                            Layout.fillWidth: true
                            compact: true
                            label: "Sites"
                            value: String(root.statistics.siteCount !== undefined ? root.statistics.siteCount : "--")
                            clickable: root.isDestinationAccessible("sites")
                            onActivated: root.navigateToDestination("sites")
                        }
                        AppWidgets.OverviewMetricTile {
                            Layout.fillWidth: true
                            compact: true
                            label: "Departments"
                            value: String(root.statistics.departmentCount !== undefined ? root.statistics.departmentCount : "--")
                            clickable: root.isDestinationAccessible("departments")
                            onActivated: root.navigateToDestination("departments")
                        }
                        AppWidgets.OverviewMetricTile {
                            Layout.fillWidth: true
                            compact: true
                            label: "Employees"
                            value: String(root.statistics.employeeCount !== undefined ? root.statistics.employeeCount : "--")
                            clickable: root.isDestinationAccessible("employees")
                            onActivated: root.navigateToDestination("employees")
                        }
                        AppWidgets.OverviewMetricTile {
                            Layout.fillWidth: true
                            compact: true
                            label: "Documents"
                            value: String(root.statistics.documentCount !== undefined ? root.statistics.documentCount : "--")
                            clickable: root.isDestinationAccessible("documents")
                            onActivated: root.navigateToDestination("documents")
                        }
                    }
                }

                AppWidgets.SectionCard {
                    Layout.fillWidth: true
                    title: "Recent Activity"
                    outlined: true

                    ColumnLayout {
                        id: activityColumn
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
                            emptyText: "No recent administrative activity for this organization."
                        }
                    }
                }
            }
        }
    }

    // -- Operational Calendar: the organization's one default calendar,
    // compact + read-only. Full editing (working rules, exceptions, shift
    // patterns) lives exclusively in Platform > Calendars -- "Manage
    // Calendar" below navigates there, opened to this organization's
    // calendar; this card never lets you create or edit calendar data.
    Item {
        width: root.width
        implicitHeight: calendarCard.implicitHeight + Theme.AppTheme.spacingMd * 2

        AppWidgets.SectionCard {
            id: calendarCard
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.margins: Theme.AppTheme.spacingMd
            title: "Operational Calendar"
            outlined: true

            ColumnLayout {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.margins: Theme.AppTheme.marginMd
                spacing: Theme.AppTheme.spacingMd

                AppControls.Label {
                    Layout.fillWidth: true
                    visible: !root.calendarSummary.hasCalendar
                    text: "No operational calendar is configured for this organization."
                    color: Theme.AppTheme.textMuted
                    font.pixelSize: Theme.AppTheme.smallSize
                    wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                }

                GridLayout {
                    Layout.fillWidth: true
                    visible: root.calendarSummary.hasCalendar
                    // Container-width breakpoints (this card's own width,
                    // not the window) so the four fields stay one readable
                    // horizontal row on desktop and stack cleanly on narrow
                    // layouts -- same technique as overviewGrid above.
                    columns: root.width < 420 ? 1 : (root.width < 760 ? 2 : 4)
                    columnSpacing: Theme.AppTheme.spacingLg
                    rowSpacing: Theme.AppTheme.spacingSm

                    Repeater {
                        model: root._calendarFields

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

                AppControls.Label {
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignRight
                    horizontalAlignment: Text.AlignRight
                    visible: root.calendarSummary.hasCalendar
                    text: "Manage Calendar"
                    color: Theme.AppTheme.accent
                    font.pixelSize: Theme.AppTheme.smallSize
                    font.bold: true

                    HoverHandler { cursorShape: Qt.PointingHandCursor }
                    TapHandler { onTapped: root.manageCalendarRequested() }
                }
            }
        }
    }

    // -- Related Actions: full content width (not confined to the ~1/3
    // summary rail) so its tiles get real room to lay out horizontally
    // instead of always falling back to a stack.
    Item {
        width: root.width
        implicitHeight: root.relatedActions.length > 0
            ? relatedActionsCard.implicitHeight + Theme.AppTheme.spacingMd * 2
            : 0
        visible: root.relatedActions.length > 0

        AppWidgets.SectionCard {
            id: relatedActionsCard
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.margins: Theme.AppTheme.spacingMd
            title: "Related Actions"
            outlined: true

            GridLayout {
                id: actionsGrid
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.margins: Theme.AppTheme.marginMd
                columnSpacing: Theme.AppTheme.spacingSm
                rowSpacing: Theme.AppTheme.spacingSm
                // Responsive tiling driven by the card's own available width
                // (a container query, not a window breakpoint): one row if
                // every tile fits at its minimum readable width, else a
                // 2-column wrap, else a single column.
                readonly property int _minTileWidth: 150
                readonly property int _actionCount: root.relatedActions.length
                columns: {
                    if (actionsGrid._actionCount <= 1) return 1
                    const perRow = Math.max(
                        1,
                        Math.floor(
                            (actionsGrid.width + actionsGrid.columnSpacing)
                            / (actionsGrid._minTileWidth + actionsGrid.columnSpacing)
                        )
                    )
                    if (perRow >= actionsGrid._actionCount) return actionsGrid._actionCount
                    return perRow >= 2 ? 2 : 1
                }

                Repeater {
                    model: root.relatedActions

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

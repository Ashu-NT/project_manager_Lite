pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

// Employee Detail's Overview tab: Employee Information / Employment /
// Organizational Assignment / Contact Information (main column) plus System
// Access / Operational Calendar / Recent Activity / Related Actions
// (summary rail) -- the same information architecture as Organization/
// Site/Department Overview, specialized for Employee's own business
// semantics. System Access replaces the old standalone "User Account" tab
// with a real relationship card: Employee<->User is an optional one-to-one
// link (see link_employee_user_account/unlink_employee_user_account), never
// a mandatory profile field. A presentational section only -- all data is
// supplied by the orchestrator (AdminEmployeeDetailPage.qml).
Column {
    id: root
    spacing: 0

    property var employeeInformationFields: []
    property var employmentFields: []
    property var organizationalAssignmentFields: []
    property var contactFields: []
    property var relatedActions: []
    property var recentActivity: []
    // { "linked": bool, "identity": "", "isActive": bool }
    property var systemAccess: ({ "linked": false, "identity": "", "isActive": false })
    property bool canManageSystemAccess: false
    property var calendarSummary: ({
        "hasCalendar": false, "calendarName": "", "source": "",
        "workingWeekLabel": "", "timeZone": "", "holidaySetLabel": ""
    })

    signal navigateToDestination(string destinationId)
    signal viewAllActivityRequested()
    signal manageCalendarRequested()
    signal linkUserAccountRequested()
    signal unlinkUserAccountRequested()
    signal openUserAccountRequested()

    readonly property var _calendarDetailFields: root.calendarSummary.hasCalendar ? [
        { "label": "Working Week", "value": String(root.calendarSummary.workingWeekLabel || "-") },
        { "label": "Time Zone", "value": String(root.calendarSummary.timeZone || "-") },
        { "label": "Holiday Rules", "value": String(root.calendarSummary.holidaySetLabel || "-") }
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
            columns: root.width < 640 ? 1 : 2
            columnSpacing: Theme.AppTheme.spacingMd
            rowSpacing: Theme.AppTheme.spacingMd

            // -- Main column: Employee Information / Employment /
            // Organizational Assignment / Contact Information -- ~2/3 width
            // on desktop; content-driven height only, never a fixed/
            // computed override that can under-report a card's real height
            // and get clipped by SectionCard's own clip: true.
            ColumnLayout {
                Layout.fillWidth: true
                Layout.preferredWidth: overviewGrid.columns === 2
                    ? Math.round(overviewGrid.width * 0.66)
                    : overviewGrid.width
                Layout.alignment: Qt.AlignTop
                spacing: Theme.AppTheme.spacingMd

                AppWidgets.SectionCard {
                    Layout.fillWidth: true
                    title: "Employee Information"
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
                            model: root.employeeInformationFields

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
                    title: "Employment"
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
                            model: root.employmentFields

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
                    title: "Organizational Assignment"
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
                            model: root.organizationalAssignmentFields

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

            // -- Summary rail: System Access, operational calendar, recent
            // activity, and related actions -- one consolidated column
            // (~1/3 width) rather than separate full-width cards below the
            // grid, so the page reads as a single summary rail next to the
            // main profile information.
            ColumnLayout {
                Layout.fillWidth: true
                Layout.preferredWidth: overviewGrid.columns === 2
                    ? overviewGrid.width - Math.round(overviewGrid.width * 0.66) - overviewGrid.columnSpacing
                    : overviewGrid.width
                Layout.alignment: Qt.AlignTop
                spacing: Theme.AppTheme.spacingMd

                AppWidgets.SectionCard {
                    Layout.fillWidth: true
                    title: "System Access"
                    outlined: true

                    ColumnLayout {
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.margins: Theme.AppTheme.marginMd
                        spacing: Theme.AppTheme.spacingSm

                        AppControls.Label {
                            Layout.fillWidth: true
                            visible: !root.systemAccess.linked
                            text: "No user account linked."
                            color: Theme.AppTheme.textMuted
                            font.pixelSize: Theme.AppTheme.smallSize
                            wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            visible: root.systemAccess.linked
                            spacing: Theme.AppTheme.spacingXs

                            AppControls.Label {
                                Layout.fillWidth: true
                                text: "User Account"
                                color: Theme.AppTheme.textMuted
                                font.pixelSize: Theme.AppTheme.captionSize
                                font.bold: true
                            }
                            AppControls.Label {
                                Layout.fillWidth: true
                                text: String(root.systemAccess.identity || "-")
                                color: Theme.AppTheme.textPrimary
                                font.pixelSize: Theme.AppTheme.smallSize
                                wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                            }

                            AppControls.Label {
                                Layout.fillWidth: true
                                Layout.topMargin: Theme.AppTheme.spacingXs
                                text: "Account Status"
                                color: Theme.AppTheme.textMuted
                                font.pixelSize: Theme.AppTheme.captionSize
                                font.bold: true
                            }
                            AppWidgets.StatusChip {
                                status: root.systemAccess.isActive ? "Active" : "Inactive"
                                tone: root.systemAccess.isActive ? "success" : "neutral"
                            }
                        }

                        AppControls.Label {
                            Layout.fillWidth: true
                            Layout.topMargin: Theme.AppTheme.spacingXs
                            visible: root.systemAccess.linked
                            text: "Open User Account"
                            color: Theme.AppTheme.accent
                            font.pixelSize: Theme.AppTheme.smallSize
                            font.bold: true

                            HoverHandler { cursorShape: Qt.PointingHandCursor }
                            TapHandler { onTapped: root.openUserAccountRequested() }
                        }

                        AppControls.Label {
                            Layout.fillWidth: true
                            Layout.topMargin: Theme.AppTheme.spacingXs
                            visible: root.systemAccess.linked && root.canManageSystemAccess
                            text: "Unlink User Account"
                            color: Theme.AppTheme.danger
                            font.pixelSize: Theme.AppTheme.smallSize
                            font.bold: true

                            HoverHandler { cursorShape: Qt.PointingHandCursor }
                            TapHandler { onTapped: root.unlinkUserAccountRequested() }
                        }

                        AppControls.PrimaryButton {
                            Layout.fillWidth: true
                            Layout.topMargin: Theme.AppTheme.spacingXs
                            visible: !root.systemAccess.linked && root.canManageSystemAccess
                            text: "Link User Account"
                            iconName: "add"
                            onClicked: root.linkUserAccountRequested()
                        }
                    }
                }

                AppWidgets.SectionCard {
                    Layout.fillWidth: true
                    title: "Operational Calendar"
                    outlined: true

                    ColumnLayout {
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.margins: Theme.AppTheme.marginMd
                        spacing: Theme.AppTheme.spacingSm

                        AppControls.Label {
                            Layout.fillWidth: true
                            visible: !root.calendarSummary.hasCalendar
                            text: "No calendar is configured for this employee, their department, site, or organization."
                            color: Theme.AppTheme.textMuted
                            font.pixelSize: Theme.AppTheme.smallSize
                            wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            visible: root.calendarSummary.hasCalendar
                            spacing: 2

                            AppControls.Label {
                                Layout.fillWidth: true
                                text: String(root.calendarSummary.calendarName || "-")
                                color: Theme.AppTheme.textPrimary
                                font.pixelSize: Theme.AppTheme.bodySize
                                font.bold: true
                                wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                            }
                            AppControls.Label {
                                Layout.fillWidth: true
                                text: String(root.calendarSummary.source || "Inherited from Organization")
                                color: Theme.AppTheme.textMuted
                                font.pixelSize: Theme.AppTheme.captionSize
                                wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                            }
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            Layout.topMargin: Theme.AppTheme.spacingXs
                            visible: root.calendarSummary.hasCalendar
                            spacing: Theme.AppTheme.spacingXs

                            Repeater {
                                model: root._calendarDetailFields

                                delegate: RowLayout {
                                    required property var modelData
                                    Layout.fillWidth: true
                                    spacing: Theme.AppTheme.spacingSm

                                    AppControls.Label {
                                        text: String(modelData.label || "")
                                        color: Theme.AppTheme.textMuted
                                        font.pixelSize: Theme.AppTheme.captionSize
                                    }

                                    Item { Layout.fillWidth: true }

                                    AppControls.Label {
                                        text: String(modelData.value || "-")
                                        color: Theme.AppTheme.textPrimary
                                        font.pixelSize: Theme.AppTheme.captionSize
                                        horizontalAlignment: Text.AlignRight
                                    }
                                }
                            }
                        }

                        AppControls.Label {
                            Layout.fillWidth: true
                            Layout.alignment: Qt.AlignRight
                            Layout.topMargin: Theme.AppTheme.spacingXs
                            horizontalAlignment: Text.AlignRight
                            text: "Manage Calendar"
                            color: Theme.AppTheme.accent
                            font.pixelSize: Theme.AppTheme.smallSize
                            font.bold: true

                            HoverHandler { cursorShape: Qt.PointingHandCursor }
                            TapHandler { onTapped: root.manageCalendarRequested() }
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
                            emptyText: "No activity yet. Business activity for this employee will appear here."
                        }
                    }
                }

                // -- Related Actions: Manage Calendar is a context-
                // preserving local action (this employee's own Calendar
                // tab). Open User Account (when linked)/Open Resource in
                // Project Management (when a real navigation target
                // resolves) are real external cross-module navigation --
                // neither is a tab here.
                AppWidgets.SectionCard {
                    Layout.fillWidth: true
                    visible: root.relatedActions.length > 0
                    title: "Related Actions"
                    outlined: true

                    ColumnLayout {
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.margins: Theme.AppTheme.marginMd
                        spacing: Theme.AppTheme.spacingSm

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
    }
}

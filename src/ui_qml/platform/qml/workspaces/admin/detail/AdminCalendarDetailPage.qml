pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme
import App.Widgets 1.0 as AppWidgets
import Platform.Controllers 1.0 as PlatformControllers
import "../components"

Item {
    id: root

    property PlatformControllers.PlatformAdminWorkspaceController workspaceController
    property var calendar: ({})
    property bool busy: false
    property string errorMessage: ""
    property string feedbackMessage: ""
    property int activeSectionIndex: 0
    property string selectedHolidayId: ""
    property string calculationResult: ""

    signal backRequested()
    signal editRequested()
    signal addHolidayRequested()
    signal openAuditRequested()

    readonly property var _state: (root.calendar && root.calendar.state) ? root.calendar.state : ({})
    readonly property string _title: String(root.calendar && root.calendar.title ? root.calendar.title : "Working Calendar")
    readonly property string _workingDaysText: String(root._state.workingDaysText || "No working days configured")
    readonly property string _hoursPerDayLabel: String(root._state.hoursPerDayLabel || root._state.hoursPerDay || "8")
    readonly property var _holidayRows: root._state.holidays || []
    readonly property var _sections: [
        { "label": "Overview" },
        { "label": "Holidays", "count": root._holidayRows.length },
        { "label": "Calculator" },
        { "label": "Audit" }
    ]
    readonly property string _activeSectionLabel: {
        const section = root._sections[root.activeSectionIndex]
        return section ? String(section.label || "") : "Overview"
    }
    readonly property var _toolbarActions: {
        if (root._activeSectionLabel === "Overview") {
            return [
                { "id": "edit", "label": "Edit Calendar", "icon": "edit" },
                { "id": "refresh", "label": "Refresh", "icon": "refresh" }
            ]
        }
        if (root._activeSectionLabel === "Holidays") {
            return [
                { "id": "add_holiday", "label": "Add Exception", "icon": "add" },
                { "id": "delete_holiday", "label": "Delete Exception", "icon": "delete", "danger": true, "enabled": root.selectedHolidayId.length > 0 },
                { "id": "refresh", "label": "Refresh", "icon": "refresh" }
            ]
        }
        if (root._activeSectionLabel === "Calculator") {
            return [
                { "id": "calculate", "label": "Calculate Days", "icon": "refresh" }
            ]
        }
        return [
            { "id": "open_audit", "label": "Open Audit", "icon": "history" }
        ]
    }
    readonly property string _toolbarSubtitle: {
        switch (root._activeSectionLabel) {
        case "Overview":
            return "Shared working-week rules owned by Platform and consumed by PM Scheduling and other modules."
        case "Holidays":
            return "Holiday and non-working-day exceptions for the shared working calendar."
        case "Calculator":
            return "Preview working-day finish dates using the current shared calendar."
        case "Audit":
            return "Calendar governance stays in the shared platform audit and approval flow."
        default:
            return ""
        }
    }
    readonly property var _holidayColumns: [
        { "key": "date", "label": "Date", "flex": 1.0, "sortable": true },
        { "key": "name", "label": "Exception", "flex": 1.8 },
        { "key": "calendar", "label": "Calendar", "flex": 1.4 },
        { "key": "details", "label": "Details", "flex": 1.8 }
    ]
    readonly property var _overviewFields: [
        { "label": "Calendar Name", "value": root._title },
        { "label": "Ownership", "value": "Platform Shared Master" },
        { "label": "Hours / Day", "value": root._hoursPerDayLabel + "h" },
        { "label": "Working Days", "value": root._workingDaysText },
        { "label": "Exceptions", "value": String(root._holidayRows.length) },
        { "label": "Calendar ID", "value": root._state.calendarId || "default" }
    ]

    function _tableHeightForCount(count) {
        const visibleRows = Math.max(1, Math.min(count, 8))
        return Theme.AppTheme.headerHeight + (visibleRows * Theme.AppTheme.normalRowHeight) + Theme.AppTheme.spacingLg
    }

    function _runCalculation() {
        if (root.workspaceController === null)
            return
        const result = root.workspaceController.calculateCalendarWorkingDays({
            "startDate": calcStartField.text,
            "workingDays": calcDaysField.text
        })
        if (result && result.ok === true) {
            root.calculationResult = String(result.message || "")
        } else {
            root.calculationResult = ""
        }
    }

    AppWidgets.SectionDetailPage {
        id: detailPage
        anchors.fill: parent
        open: true
        title: root._title
        isBusy: root.busy
        showEdit: false
        showDelete: false
        sections: root._sections

        onBackRequested: root.backRequested()
        onSectionChanged: function(index) {
            root.activeSectionIndex = index
        }

        AppWidgets.InlineMessage {
            width: parent ? parent.width : root.width
            visible: root.errorMessage.length > 0
            tone: "danger"
            message: root.errorMessage
        }

        AppWidgets.InlineMessage {
            width: parent ? parent.width : root.width
            visible: root.feedbackMessage.length > 0 && root.errorMessage.length === 0
            tone: "success"
            message: root.feedbackMessage
        }

        AppWidgets.ContextualActionToolbar {
            width: parent ? parent.width : root.width
            title: root._activeSectionLabel
            subtitle: root._toolbarSubtitle
            busy: root.busy
            actions: root._toolbarActions
            onActionTriggered: function(actionId) {
                if (actionId === "edit") {
                    root.editRequested()
                } else if (actionId === "add_holiday") {
                    root.addHolidayRequested()
                } else if (actionId === "delete_holiday") {
                    if (root.workspaceController !== null && root.selectedHolidayId.length > 0) {
                        const result = root.workspaceController.deleteCalendarHoliday(root.selectedHolidayId)
                        if (result && result.ok === true)
                            root.selectedHolidayId = ""
                    }
                } else if (actionId === "refresh") {
                    if (root.workspaceController !== null)
                        root.workspaceController.refresh()
                } else if (actionId === "calculate") {
                    root._runCalculation()
                } else if (actionId === "open_audit") {
                    root.openAuditRequested()
                }
            }
        }

        Item {
            width: parent ? parent.width : root.width
            implicitHeight: root.activeSectionIndex === 0 ? overviewLoader.implicitHeight : 0
            height: implicitHeight
            visible: implicitHeight > 0

            AppWidgets.LazySectionLoader {
                id: overviewLoader
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                active: root.activeSectionIndex === 0
                keepLoaded: true
                loadingMessage: "Loading calendar overview..."
                sourceComponent: Component {
                    Column {
                        width: parent ? parent.width : 0
                        spacing: 0

                        AppWidgets.SectionHeading {
                            width: parent.width
                            label: "Overview"
                        }

                        Item {
                            width: parent.width
                            implicitHeight: overviewColumn.implicitHeight + Theme.AppTheme.spacingMd * 2

                            ColumnLayout {
                                id: overviewColumn
                                anchors.top: parent.top
                                anchors.left: parent.left
                                anchors.right: parent.right
                                anchors.topMargin: Theme.AppTheme.spacingMd
                                anchors.leftMargin: Theme.AppTheme.spacingMd
                                anchors.rightMargin: Theme.AppTheme.spacingMd
                                spacing: Theme.AppTheme.spacingMd

                                AppWidgets.InlineMessage {
                                    Layout.fillWidth: true
                                    tone: "info"
                                    message: "This shared calendar is managed in Platform Admin and consumed read-only by PM scheduling workspaces."
                                }

                                AppWidgets.SectionCard {
                                    Layout.fillWidth: true
                                    implicitHeight: overviewGrid.implicitHeight + Theme.AppTheme.spacingMd * 2
                                    title: "Calendar Summary"
                                    outlined: true

                                    GridLayout {
                                        id: overviewGrid
                                        anchors.left: parent.left
                                        anchors.right: parent.right
                                        anchors.top: parent.top
                                        anchors.margins: Theme.AppTheme.marginMd
                                        columns: 2
                                        columnSpacing: Theme.AppTheme.spacingLg
                                        rowSpacing: Theme.AppTheme.spacingSm

                                        Repeater {
                                            model: root._overviewFields

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
                                                    text: modelData.value === undefined || modelData.value === null || String(modelData.value).length === 0
                                                        ? "-"
                                                        : String(modelData.value)
                                                    color: Theme.AppTheme.textPrimary
                                                    font.pixelSize: Theme.AppTheme.smallSize
                                                    wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        Item {
            width: parent ? parent.width : root.width
            implicitHeight: root.activeSectionIndex === 1 ? holidaysLoader.implicitHeight : 0
            height: implicitHeight
            visible: implicitHeight > 0

            AppWidgets.LazySectionLoader {
                id: holidaysLoader
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                active: root.activeSectionIndex === 1
                keepLoaded: true
                loadingMessage: "Loading calendar exceptions..."
                sourceComponent: Component {
                    AdminDetailTableSection {
                        sectionLabel: "Holiday Exceptions"
                        infoMessage: "These exceptions are shared across any module that consumes the Platform working calendar."
                        rows: root._holidayRows
                        columns: root._holidayColumns
                        selectedRowId: root.selectedHolidayId
                        emptyTitle: "No exceptions yet"
                        emptyMessage: "No holiday or non-working-day exceptions are configured."
                        tableHeight: root._tableHeightForCount(root._holidayRows.length)
                        onRowSelected: function(rowId) {
                            root.selectedHolidayId = String(rowId || "")
                        }
                        onRowActivated: function(rowId) {
                            root.selectedHolidayId = String(rowId || "")
                        }
                    }
                }
            }
        }

        Item {
            width: parent ? parent.width : root.width
            implicitHeight: root.activeSectionIndex === 2 ? calculatorLoader.implicitHeight : 0
            height: implicitHeight
            visible: implicitHeight > 0

            AppWidgets.LazySectionLoader {
                id: calculatorLoader
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                active: root.activeSectionIndex === 2
                keepLoaded: true
                loadingMessage: "Loading calendar calculator..."
                sourceComponent: Component {
                    Column {
                        width: parent ? parent.width : 0
                        spacing: 0

                        AppWidgets.SectionHeading {
                            width: parent.width
                            label: "Calculator"
                        }

                        Item {
                            width: parent.width
                            implicitHeight: calculatorColumn.implicitHeight + Theme.AppTheme.spacingMd * 2

                            ColumnLayout {
                                id: calculatorColumn
                                anchors.top: parent.top
                                anchors.left: parent.left
                                anchors.right: parent.right
                                anchors.topMargin: Theme.AppTheme.spacingMd
                                anchors.leftMargin: Theme.AppTheme.spacingMd
                                anchors.rightMargin: Theme.AppTheme.spacingMd
                                spacing: Theme.AppTheme.spacingMd

                                AppWidgets.SectionCard {
                                    Layout.fillWidth: true
                                    implicitHeight: calculatorForm.implicitHeight + Theme.AppTheme.spacingMd * 2
                                    title: "Working-Day Preview"
                                    outlined: true

                                    ColumnLayout {
                                        id: calculatorForm
                                        anchors.left: parent.left
                                        anchors.right: parent.right
                                        anchors.top: parent.top
                                        anchors.margins: Theme.AppTheme.marginMd
                                        spacing: Theme.AppTheme.spacingMd

                                        AppControls.Label {
                                            Layout.fillWidth: true
                                            text: "Preview finish dates using the shared Platform working calendar."
                                            color: Theme.AppTheme.textSecondary
                                            font.pixelSize: Theme.AppTheme.smallSize
                                            wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                                        }

                                        RowLayout {
                                            Layout.fillWidth: true
                                            spacing: Theme.AppTheme.spacingMd

                                            AppWidgets.FormField {
                                                Layout.fillWidth: true
                                                label: "Start Date"

                                                AppControls.DateField {
                                                    id: calcStartField
                                                    Layout.fillWidth: true
                                                    placeholderText: "YYYY-MM-DD"
                                                }
                                            }

                                            AppWidgets.FormField {
                                                Layout.preferredWidth: 140
                                                label: "Working Days"

                                                AppControls.TextField {
                                                    id: calcDaysField
                                                    Layout.fillWidth: true
                                                    placeholderText: "e.g. 5"
                                                }
                                            }
                                        }

                                        AppWidgets.InlineMessage {
                                            Layout.fillWidth: true
                                            visible: root.calculationResult.length > 0
                                            tone: "success"
                                            message: root.calculationResult
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        Item {
            width: parent ? parent.width : root.width
            implicitHeight: root.activeSectionIndex === 3 ? auditLoader.implicitHeight : 0
            height: implicitHeight
            visible: implicitHeight > 0

            AppWidgets.LazySectionLoader {
                id: auditLoader
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                active: root.activeSectionIndex === 3
                keepLoaded: true
                loadingMessage: "Loading audit guidance..."
                sourceComponent: Component {
                    AdminInformationalDetailSection {
                        sectionLabel: "Audit"
                        infoMessage: "Shared calendar changes participate in platform governance and can affect PM scheduling calculations."
                        cardTitle: "Audit & Ownership"
                        notes: [
                            "Platform owns shared working-calendar rules, holiday exceptions, and working-day calculations.",
                            "Project Management consumes this calendar for schedule logic and preview calculations, but does not own the CRUD workflow.",
                            "Use the shared audit workspace to review change history and operational follow-up."
                        ]
                    }
                }
            }
        }
    }
}

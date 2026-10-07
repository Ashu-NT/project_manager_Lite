pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import QtQuick.Window
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import Platform.Controllers 1.0 as PlatformControllers

// Calendar tab's "Exceptions" view: holidays, shutdowns, and other
// date-specific overrides for this calendar. Selecting a row opens the
// shared InspectorPanel on the right -- the same interaction model as the
// Month view's day selection, never a separate detail page per exception.
Item {
    id: root

    property PlatformControllers.PlatformAdminWorkspaceController workspaceController
    property string calendarId: ""
    property var exceptions: []
    property var workingRules: []
    property string selectedExceptionId: ""
    property bool canWrite: true
    // Shared fixed height for the Month/Exceptions/Recurring content area
    // (see CalendarScheduleSection.qml) -- 0 means "size to this view's own
    // row count" so it still works when used standalone/in tests.
    property int fixedContentHeight: 0

    signal addExceptionRequested()
    signal editExceptionRequested(string exceptionId)
    signal deleteExceptionRequested()
    signal exceptionSelected(string exceptionId)

    implicitHeight: _layout.implicitHeight

    property string _searchText: ""
    property string _typeFilter: "All"
    property string _impactFilter: "All"
    property string _statusFilter: "All"
    property var _resolvedDay: null

    readonly property bool _showInspector: root._selectedException !== null

    readonly property int _naturalTableHeight: Theme.AppTheme.headerHeight
        + Math.max(1, Math.min(root._tableRows.length, 8)) * Theme.AppTheme.normalRowHeight
        + Theme.AppTheme.spacingLg
    readonly property int _tableHeight: root.fixedContentHeight > 0 ? root.fixedContentHeight : root._naturalTableHeight

    readonly property var _columns: [
        { "key": "dateLabel", "label": "Date", "flex": 0.8 },
        { "key": "name", "label": "Exception", "flex": 1.4 },
        { "key": "typeLabel", "label": "Type", "flex": 1.0 },
        { "key": "impactChip", "label": "Impact", "flex": 1.0, "type": "status" },
        { "key": "statusChip", "label": "Status", "flex": 0.8, "type": "status" }
    ]

    function _uniqueLabels(key) {
        const seen = {}
        const values = []
        for (let i = 0; i < root.exceptions.length; i += 1) {
            const label = String(root.exceptions[i][key] || "")
            if (label.length > 0 && !seen[label]) { seen[label] = true; values.push(label) }
        }
        return ["All"].concat(values.sort())
    }
    readonly property var _typeOptions: root._uniqueLabels("typeLabel")
    readonly property var _impactOptions: root._uniqueLabels("impactLabel")
    readonly property var _statusOptions: root._uniqueLabels("statusLabel")

    readonly property var _filteredRows: {
        const query = root._searchText.trim().toLowerCase()
        return root.exceptions.filter(function(row) {
            if (root._typeFilter !== "All" && row.typeLabel !== root._typeFilter) return false
            if (root._impactFilter !== "All" && row.impactLabel !== root._impactFilter) return false
            if (root._statusFilter !== "All" && row.statusLabel !== root._statusFilter) return false
            if (query.length === 0) return true
            return String(row.name || "").toLowerCase().indexOf(query) >= 0
                || String(row.dateLabel || "").toLowerCase().indexOf(query) >= 0
        })
    }
    readonly property var _tableRows: root._filteredRows.map(function(row) {
        return Object.assign({}, row, {
            "impactChip": { "label": row.impactLabel, "tone": row.impactTone },
            "statusChip": { "label": row.statusLabel, "tone": row.statusTone }
        })
    })

    readonly property var _selectedException: {
        for (let i = 0; i < root.exceptions.length; i += 1) {
            if (String(root.exceptions[i].id) === root.selectedExceptionId) return root.exceptions[i]
        }
        return null
    }

    // Weekday-of-a-given-calendar-date is pure calendar arithmetic (which
    // day of the week does 2026-10-20 fall on), never a "what is today"
    // business question -- same category as CalendarMonthView's own grid
    // boundary math, not a re-implementation of working-hours business logic.
    function _weekdayOf(isoDate) {
        const parts = isoDate.split("-")
        const d = new Date(parseInt(parts[0], 10), parseInt(parts[1], 10) - 1, parseInt(parts[2], 10))
        return (d.getDay() + 6) % 7
    }

    function _normalWorkingRuleFor(isoDate) {
        if (!isoDate) return null
        const weekday = root._weekdayOf(isoDate)
        for (let i = 0; i < root.workingRules.length; i += 1) {
            if (root.workingRules[i].weekday === weekday) return root.workingRules[i]
        }
        return null
    }

    function _refreshResolvedDay() {
        root._resolvedDay = null
        const exc = root._selectedException
        if (!exc || !root.workspaceController || root.calendarId.length === 0) return
        const result = root.workspaceController.calendarMonthRange(root.calendarId, exc.exceptionDate, exc.exceptionDate)
        if (result && result.ok === true && result.days && result.days.length > 0) {
            root._resolvedDay = result.days[0]
        }
    }
    onSelectedExceptionIdChanged: root._refreshResolvedDay()
    onExceptionsChanged: root._refreshResolvedDay()

    readonly property var _inspectorGroups: {
        const exc = root._selectedException
        if (!exc) return []
        const normalRule = root._normalWorkingRuleFor(exc.exceptionDate)
        const normalLabel = (normalRule && normalRule.isWorkingDay)
            ? String(normalRule.startTime || "-") + "–" + String(normalRule.endTime || "-")
            : "Non-working"
        const exceptionLabel = (exc.startTimeLabel && exc.endTimeLabel)
            ? exc.startTimeLabel + "–" + exc.endTimeLabel
            : normalLabel
        const availableLabel = root._resolvedDay
            ? (Number(root._resolvedDay.availableHours) + " h")
            : ""

        const groups = [
            {
                "title": "Details",
                "rows": [
                    { "label": "Type", "value": exc.typeLabel },
                    { "label": "Impact", "value": exc.impactLabel },
                    { "label": "Status", "value": exc.statusLabel }
                ]
            },
            {
                "title": "Working Time",
                "rows": [
                    { "label": "Normal", "value": normalLabel },
                    { "label": "Exception", "value": exceptionLabel },
                    { "label": "Available", "value": availableLabel }
                ]
            },
            {
                "title": "Validity",
                "rows": [
                    { "label": "Date", "value": exc.dateLabel }
                ]
            }
        ]
        if (String(exc.description || "").length > 0) {
            groups.push({ "title": "Description", "rows": [{ "label": "", "value": exc.description }] })
        }
        return groups
    }

    ColumnLayout {
        id: _layout
        width: parent ? parent.width : root.width
        spacing: Theme.AppTheme.spacingMd

        AppWidgets.TableToolbar {
            Layout.fillWidth: true
            searchText: root._searchText
            searchPlaceholder: "Search exceptions..."
            showFilter: false
            showCreate: root.canWrite
            createLabel: "Add Exception"
            onSearchChanged: function(text) { root._searchText = text }
            onCreateRequested: root.addExceptionRequested()
            onRefreshRequested: root._refreshResolvedDay()

            AppControls.ComboBox {
                model: root._typeOptions
                currentIndex: Math.max(0, root._typeOptions.indexOf(root._typeFilter))
                onActivated: function(index) { root._typeFilter = root._typeOptions[index] }
            }
            AppControls.ComboBox {
                model: root._impactOptions
                currentIndex: Math.max(0, root._impactOptions.indexOf(root._impactFilter))
                onActivated: function(index) { root._impactFilter = root._impactOptions[index] }
            }
            AppControls.ComboBox {
                model: root._statusOptions
                currentIndex: Math.max(0, root._statusOptions.indexOf(root._statusFilter))
                onActivated: function(index) { root._statusFilter = root._statusOptions[index] }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.AppTheme.spacingMd

            AppWidgets.DataTable {
                objectName: "calendarExceptionsTable"
                Layout.fillWidth: true
                Layout.preferredHeight: root._tableHeight
                rows: root._tableRows
                columns: root._columns
                selectedRowId: root.selectedExceptionId
                emptyText: "No exceptions defined for this calendar."
                onRowSelected: function(rowId) { root.exceptionSelected(String(rowId || "")) }
                onRowActivated: function(rowId) { root.exceptionSelected(String(rowId || "")) }
            }

            AppWidgets.InspectorPanel {
                id: _inspector
                objectName: "calendarExceptionInspector"
                visible: root._showInspector && Window.width >= Theme.AppTheme.compactContentBreakpoint
                Layout.alignment: Qt.AlignTop
                Layout.preferredHeight: root._tableHeight

                preferredWidth: 260
                minimumWidth: 190
                availableWidth: root._showInspector ? Math.round(_layout.width * 0.3) : -1

                title: root._selectedException ? String(root._selectedException.name || "") : ""
                statusLabel: root._selectedException ? String(root._selectedException.impactLabel || "") : ""
                statusTone: root._selectedException ? String(root._selectedException.impactTone || "neutral") : "neutral"
                groups: root._inspectorGroups

                showEditAction: root.canWrite
                editActionLabel: "Edit Exception"
                menuActions: root.canWrite ? [
                    { "id": "delete", "label": "Delete Exception", "icon": "delete", "danger": true, "enabled": true }
                ] : []
                menuTriggerLabel: "Actions"

                onCloseRequested: root.exceptionSelected("")
                onEditRequested: root.editExceptionRequested(root.selectedExceptionId)
                onMenuActionTriggered: function(id) {
                    if (id === "delete") root.deleteExceptionRequested()
                }
            }
        }
    }
}

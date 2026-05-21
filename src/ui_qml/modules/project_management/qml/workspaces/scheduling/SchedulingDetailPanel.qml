pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme
import App.Widgets 1.0 as AppWidgets

Item {
    id: root

    property var detailPage
    property var activityDetail: ({})
    property var dependenciesModel: ({ "items": [], "emptyState": "" })
    property var constraintsModel: ({ "items": [], "emptyState": "" })
    property var calendarModel: ({ "summaryText": "", "workingDays": [], "hoursPerDay": "8", "holidays": [], "emptyState": "" })
    property var baselinesModel: ({ "options": [], "rows": [], "selectedBaselineAId": "", "selectedBaselineBId": "", "includeUnchanged": false, "summaryText": "", "emptyState": "" })
    property var baselineRegisterModel: ({ "items": [], "emptyState": "" })
    property var resourceLoadingModel: ({ "items": [], "emptyState": "" })
    property var activityFeedModel: ({ "items": [], "emptyState": "" })
    property string calculatorResult: ""
    property bool isBusy: false

    property string selectedDependencyId: ""
    property string selectedBaselineRegisterId: ""
    property string selectedHolidayId: ""
    property var workingDayDraft: []
    property string hoursPerDayDraft: "8"

    signal createDependencyRequested()
    signal editDependencyRequested(var dependencyData)
    signal deleteDependencyRequested(var dependencyData)
    signal saveCalendarRequested(var payload)
    signal addHolidayRequested(var payload)
    signal deleteHolidayRequested(string holidayId)
    signal calculateRequested(var payload)
    signal baselineASelected(string baselineId)
    signal baselineBSelected(string baselineId)
    signal includeUnchangedUpdated(bool includeUnchanged)
    signal createBaselineRequested(var payload)
    signal deleteBaselineRequested(string baselineId)

    function _indexForValue(options, value) {
        const optionList = options || []
        for (let i = 0; i < optionList.length; i += 1) {
            if (String(optionList[i].value || "") === String(value || "")) {
                return i
            }
        }
        return optionList.length > 0 ? 0 : -1
    }

    function _currentSectionIndex() {
        return detailPage ? detailPage.activeSectionIndex : 0
    }

    function _findItem(items, itemId) {
        const list = items || []
        for (let i = 0; i < list.length; i += 1) {
            if (String(list[i].id || "") === String(itemId || "")) {
                return list[i]
            }
        }
        return null
    }

    function _syncCalendarDraft() {
        const dayOptions = root.calendarModel.workingDays || []
        const selected = []
        for (let i = 0; i < dayOptions.length; i += 1) {
            if (dayOptions[i].checked) {
                selected.push(dayOptions[i].index)
            }
        }
        root.workingDayDraft = selected
        root.hoursPerDayDraft = String(root.calendarModel.hoursPerDay || "8")
    }

    function _calendarSummaryRows() {
        const dayOptions = root.calendarModel.workingDays || []
        const activeLabels = []
        for (let i = 0; i < dayOptions.length; i += 1) {
            if (dayOptions[i].checked) {
                activeLabels.push(String(dayOptions[i].label || ""))
            }
        }
        return [{
            "id": "calendar:default",
            "calendar": "Default Calendar",
            "workingDays": activeLabels.join(", "),
            "shiftPattern": activeLabels.length > 0 ? "Business week" : "No shift",
            "hoursPerDay": String(root.calendarModel.hoursPerDay || "8"),
            "exceptions": String((root.calendarModel.holidays || []).length) + " holiday(s)"
        }]
    }

    function _holidayRows() {
        const items = root.calendarModel.holidays || []
        const rows = []
        for (let i = 0; i < items.length; i += 1) {
            const item = items[i]
            const state = item.state || {}
            rows.push({
                "id": item.id,
                "date": item.title,
                "exception": item.subtitle,
                "calendar": String(state.calendar || "Default Calendar"),
                "details": item.supportingText || item.metaText || ""
            })
        }
        return rows
    }

    function _dependencyRows() {
        const items = root.dependenciesModel.items || []
        const rows = []
        for (let i = 0; i < items.length; i += 1) {
            const item = items[i]
            const state = item.state || {}
            rows.push({
                "id": item.id,
                "relatedActivity": item.title,
                "dependencyType": String(state.dependencyTypeLabel || item.subtitle || ""),
                "lag": String(state.lagLabel || ""),
                "direction": item.statusLabel,
                "status": String(state.statusLabel || item.metaText || "")
            })
        }
        return rows
    }

    function _constraintRows() {
        const items = root.constraintsModel.items || []
        const rows = []
        for (let i = 0; i < items.length; i += 1) {
            const item = items[i]
            const state = item.state || {}
            rows.push({
                "id": item.id,
                "constraint": item.title,
                "value": item.subtitle,
                "status": String(state.constraintStatus || item.statusLabel || ""),
                "notes": item.supportingText || item.metaText || ""
            })
        }
        return rows
    }

    function _baselineCompareRows() {
        const items = root.baselinesModel.rows || []
        const rows = []
        for (let i = 0; i < items.length; i += 1) {
            const item = items[i]
            rows.push({
                "id": item.id,
                "task": item.title,
                "change": item.statusLabel,
                "shift": item.supportingText,
                "dates": item.subtitle,
                "cost": item.metaText
            })
        }
        return rows
    }

    function _baselineRegisterRows() {
        const items = root.baselineRegisterModel.items || []
        const rows = []
        for (let i = 0; i < items.length; i += 1) {
            const item = items[i]
            const state = item.state || {}
            rows.push({
                "id": item.id,
                "baseline": item.title,
                "created": String(state.createdLabel || item.subtitle || ""),
                "approvedBy": String(state.approvedByLabel || ""),
                "state": String(state.varianceState || item.statusLabel || "")
            })
        }
        return rows
    }

    function _resourceRows() {
        const items = root.resourceLoadingModel.items || []
        const rows = []
        for (let i = 0; i < items.length; i += 1) {
            const item = items[i]
            const state = item.state || {}
            rows.push({
                "id": item.id,
                "resource": item.title,
                "allocation": String(state.allocationLabel || ""),
                "capacity": String(state.capacityLabel || ""),
                "utilization": String(state.utilizationLabel || item.subtitle || ""),
                "tasks": String(state.tasksCount || ""),
                "status": item.statusLabel
            })
        }
        return rows
    }

    onCalendarModelChanged: _syncCalendarDraft()
    Component.onCompleted: _syncCalendarDraft()

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.AppTheme.marginMd
        spacing: Theme.AppTheme.spacingSm

        SchedulingPanelFrame {
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: root._currentSectionIndex() === 0
            title: "Activity Details"
            subtitle: "Operational planning fields and current schedule state."

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: Theme.AppTheme.marginMd
                spacing: Theme.AppTheme.spacingSm

                AppWidgets.InlineMessage {
                    Layout.fillWidth: true
                    tone: "info"
                    message: root.activityDetail.emptyState || ""
                }

                Label {
                    Layout.fillWidth: true
                    visible: String(root.activityDetail.description || "").length > 0
                    text: root.activityDetail.description || ""
                    color: Theme.AppTheme.textSecondary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                    wrapMode: Text.WordWrap
                }

                Repeater {
                    model: root.activityDetail.fields || []

                    delegate: Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: _fieldColumn.implicitHeight + (Theme.AppTheme.spacingSm * 2)
                        radius: Theme.AppTheme.radiusSm
                        color: Theme.AppTheme.surfaceOverlay
                        border.color: Theme.AppTheme.subtleBorder
                        border.width: 1

                        ColumnLayout {
                            id: _fieldColumn
                            anchors.fill: parent
                            anchors.margins: Theme.AppTheme.spacingSm
                            spacing: 2

                            Label {
                                Layout.fillWidth: true
                                text: String(modelData.label || "")
                                color: Theme.AppTheme.textMuted
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.captionSize
                                font.bold: true
                            }

                            Label {
                                Layout.fillWidth: true
                                text: String(modelData.value || "")
                                color: Theme.AppTheme.textPrimary
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.smallSize
                                wrapMode: Text.WordWrap
                            }

                            Label {
                                Layout.fillWidth: true
                                visible: String(modelData.supportingText || "").length > 0
                                text: String(modelData.supportingText || "")
                                color: Theme.AppTheme.textMuted
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.captionSize
                                wrapMode: Text.WordWrap
                            }
                        }
                    }
                }
            }
        }

        SchedulingPanelFrame {
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: root._currentSectionIndex() === 1
            title: "Dependencies"
            subtitle: "Sequence logic, lag controls, and predecessor/successor management."

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: Theme.AppTheme.marginMd
                spacing: Theme.AppTheme.spacingSm

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.AppTheme.spacingSm

                    AppControls.PrimaryButton {
                        text: "Add Dependency"
                        iconName: "add"
                        enabled: !root.isBusy
                        onClicked: root.createDependencyRequested()
                    }

                    AppControls.SecondaryButton {
                        text: "Edit Lag"
                        iconName: "edit"
                        enabled: !root.isBusy && root.selectedDependencyId.length > 0
                        onClicked: {
                            const item = root._findItem(root.dependenciesModel.items || [], root.selectedDependencyId)
                            if (item) {
                                root.editDependencyRequested(item)
                            }
                        }
                    }

                    AppControls.SecondaryButton {
                        text: "Remove"
                        iconName: "delete"
                        danger: true
                        enabled: !root.isBusy && root.selectedDependencyId.length > 0
                        onClicked: {
                            const item = root._findItem(root.dependenciesModel.items || [], root.selectedDependencyId)
                            if (item) {
                                root.deleteDependencyRequested(item)
                            }
                        }
                    }

                    Item { Layout.fillWidth: true }
                }

                AppWidgets.DataTable {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    columns: [
                        { "key": "relatedActivity", "label": "Related Activity", "flex": 2, "sortable": true },
                        { "key": "dependencyType", "label": "Dependency Type", "flex": 1.3 },
                        { "key": "lag", "label": "Lag", "flex": 0, "minWidth": 70 },
                        { "key": "direction", "label": "Direction", "flex": 1, "type": "status" },
                        { "key": "status", "label": "Status", "flex": 0, "minWidth": 90, "type": "status" }
                    ]
                    rows: root._dependencyRows()
                    selectedRowId: root.selectedDependencyId
                    loading: false
                    emptyText: root.dependenciesModel.emptyState || "No dependencies are linked to this activity."

                    onRowSelected: function(rowId) {
                        root.selectedDependencyId = String(rowId || "")
                    }
                    onRowActivated: function(rowId) {
                        root.selectedDependencyId = String(rowId || "")
                        const item = root._findItem(root.dependenciesModel.items || [], rowId)
                        if (item) {
                            root.editDependencyRequested(item)
                        }
                    }
                }
            }
        }

        SchedulingPanelFrame {
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: root._currentSectionIndex() === 2
            title: "Constraints"
            subtitle: "Date guards, deadline controls, and execution locks."

            AppWidgets.DataTable {
                Layout.fillWidth: true
                Layout.fillHeight: true
                columns: [
                    { "key": "constraint", "label": "Constraint", "flex": 1.4 },
                    { "key": "value", "label": "Value", "flex": 1.0 },
                    { "key": "status", "label": "Status", "flex": 0.8, "type": "status" },
                    { "key": "notes", "label": "Notes", "flex": 2.0 }
                ]
                rows: root._constraintRows()
                emptyText: root.constraintsModel.emptyState || "No constraints recorded."
                loading: false
            }
        }

        SchedulingPanelFrame {
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: root._currentSectionIndex() === 3
            title: "Calendars"
            subtitle: "Working week, holidays, and working-day calculations."

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: Theme.AppTheme.marginMd
                spacing: Theme.AppTheme.spacingSm

                AppWidgets.InlineMessage {
                    Layout.fillWidth: true
                    tone: "info"
                    message: root.calendarModel.summaryText || ""
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.AppTheme.spacingXs

                    Repeater {
                        model: root.calendarModel.workingDays || []

                        delegate: CheckBox {
                            required property var modelData
                            text: String(modelData.label || "")
                            checked: (root.workingDayDraft || []).indexOf(modelData.index) >= 0
                            enabled: !root.isBusy
                            onToggled: {
                                const next = (root.workingDayDraft || []).slice()
                                const idx = next.indexOf(modelData.index)
                                if (checked && idx < 0) {
                                    next.push(modelData.index)
                                } else if (!checked && idx >= 0) {
                                    next.splice(idx, 1)
                                }
                                root.workingDayDraft = next
                            }
                        }
                    }

                    TextField {
                        Layout.preferredWidth: 96
                        text: root.hoursPerDayDraft
                        enabled: !root.isBusy
                        placeholderText: "Hours/day"
                        onTextChanged: root.hoursPerDayDraft = text
                    }

                    AppControls.SecondaryButton {
                        text: "Save Calendar"
                        iconName: "approve"
                        enabled: !root.isBusy
                        onClicked: root.saveCalendarRequested({
                            "workingDays": root.workingDayDraft,
                            "hoursPerDay": root.hoursPerDayDraft
                        })
                    }
                }

                AppWidgets.DataTable {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 120
                    columns: [
                        { "key": "calendar", "label": "Calendar", "flex": 1.0 },
                        { "key": "workingDays", "label": "Working Days", "flex": 1.6 },
                        { "key": "shiftPattern", "label": "Shift Pattern", "flex": 1.0 },
                        { "key": "hoursPerDay", "label": "Hours/Day", "flex": 0.8 },
                        { "key": "exceptions", "label": "Exceptions", "flex": 1.0 }
                    ]
                    rows: root._calendarSummaryRows()
                    emptyText: "No calendar summary is available."
                    loading: false
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.AppTheme.spacingSm

                    TextField {
                        id: holidayDateField
                        Layout.preferredWidth: 130
                        placeholderText: "YYYY-MM-DD"
                    }

                    TextField {
                        id: holidayNameField
                        Layout.fillWidth: true
                        placeholderText: "Holiday / exception"
                    }

                    AppControls.SecondaryButton {
                        text: "Add Holiday"
                        iconName: "add"
                        enabled: !root.isBusy
                        onClicked: root.addHolidayRequested({
                            "holidayDate": holidayDateField.text,
                            "name": holidayNameField.text
                        })
                    }
                }

                AppWidgets.DataTable {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 170
                    columns: [
                        { "key": "date", "label": "Date", "flex": 0.8 },
                        { "key": "exception", "label": "Exception", "flex": 1.0 },
                        { "key": "calendar", "label": "Calendar", "flex": 1.0 },
                        { "key": "details", "label": "Details", "flex": 1.8 }
                    ]
                    rows: root._holidayRows()
                    selectedRowId: root.selectedHolidayId
                    emptyText: root.calendarModel.emptyState || "No holiday exceptions configured."
                    loading: false

                    onRowSelected: function(rowId) {
                        root.selectedHolidayId = String(rowId || "")
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.AppTheme.spacingSm

                    TextField {
                        id: calcStartField
                        Layout.preferredWidth: 130
                        placeholderText: "Start YYYY-MM-DD"
                    }

                    TextField {
                        id: calcDaysField
                        Layout.preferredWidth: 110
                        placeholderText: "Working days"
                    }

                    AppControls.SecondaryButton {
                        text: "Calculate"
                        iconName: "refresh"
                        enabled: !root.isBusy
                        onClicked: root.calculateRequested({
                            "startDate": calcStartField.text,
                            "workingDays": calcDaysField.text
                        })
                    }

                    AppControls.SecondaryButton {
                        text: "Delete Holiday"
                        iconName: "delete"
                        danger: true
                        enabled: !root.isBusy && root.selectedHolidayId.length > 0
                        onClicked: root.deleteHolidayRequested(root.selectedHolidayId)
                    }
                }

                AppWidgets.InlineMessage {
                    Layout.fillWidth: true
                    tone: "success"
                    message: root.calculatorResult
                }
            }
        }

        SchedulingPanelFrame {
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: root._currentSectionIndex() === 4
            title: "Baselines"
            subtitle: "Snapshot comparison, variance review, and baseline register."

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: Theme.AppTheme.marginMd
                spacing: Theme.AppTheme.spacingSm

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.AppTheme.spacingSm

                    ComboBox {
                        Layout.preferredWidth: 220
                        model: root.baselinesModel.options || []
                        textRole: "label"
                        currentIndex: root._indexForValue(root.baselinesModel.options || [], root.baselinesModel.selectedBaselineAId || "")
                        enabled: !root.isBusy
                        onActivated: function(index) {
                            const option = (root.baselinesModel.options || [])[index]
                            if (option) {
                                root.baselineASelected(String(option.value || ""))
                            }
                        }
                    }

                    ComboBox {
                        Layout.preferredWidth: 220
                        model: root.baselinesModel.options || []
                        textRole: "label"
                        currentIndex: root._indexForValue(root.baselinesModel.options || [], root.baselinesModel.selectedBaselineBId || "")
                        enabled: !root.isBusy
                        onActivated: function(index) {
                            const option = (root.baselinesModel.options || [])[index]
                            if (option) {
                                root.baselineBSelected(String(option.value || ""))
                            }
                        }
                    }

                    CheckBox {
                        text: "Include unchanged"
                        checked: Boolean(root.baselinesModel.includeUnchanged)
                        enabled: !root.isBusy
                        onToggled: root.includeUnchangedUpdated(checked)
                    }

                    Item { Layout.fillWidth: true }

                    AppControls.SecondaryButton {
                        text: "Save Baseline"
                        iconName: "register"
                        enabled: !root.isBusy
                        onClicked: root.createBaselineRequested({ "name": "Baseline" })
                    }
                }

                AppWidgets.InlineMessage {
                    Layout.fillWidth: true
                    tone: "info"
                    message: root.baselinesModel.summaryText || root.baselinesModel.emptyState || ""
                }

                AppWidgets.DataTable {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 180
                    columns: [
                        { "key": "task", "label": "Activity", "flex": 1.5 },
                        { "key": "change", "label": "Change", "flex": 0.8, "type": "status" },
                        { "key": "shift", "label": "Shift", "flex": 1.5 },
                        { "key": "dates", "label": "Baseline Dates", "flex": 2.0 },
                        { "key": "cost", "label": "Cost Delta", "flex": 1.0 }
                    ]
                    rows: root._baselineCompareRows()
                    emptyText: root.baselinesModel.emptyState || "Choose two baselines to compare."
                    loading: false
                }

                AppWidgets.DataTable {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    columns: [
                        { "key": "baseline", "label": "Baseline", "flex": 1.4 },
                        { "key": "created", "label": "Created", "flex": 1.0 },
                        { "key": "approvedBy", "label": "Approved By", "flex": 1.0 },
                        { "key": "state", "label": "State", "flex": 0.8, "type": "status" }
                    ]
                    rows: root._baselineRegisterRows()
                    selectedRowId: root.selectedBaselineRegisterId
                    emptyText: root.baselineRegisterModel.emptyState || "No baseline register entries are available."
                    loading: false

                    onRowSelected: function(rowId) {
                        root.selectedBaselineRegisterId = String(rowId || "")
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.AppTheme.spacingSm

                    Item { Layout.fillWidth: true }

                    AppControls.SecondaryButton {
                        text: "Archive Baseline"
                        iconName: "delete"
                        danger: true
                        enabled: !root.isBusy && root.selectedBaselineRegisterId.length > 0
                        onClicked: root.deleteBaselineRequested(root.selectedBaselineRegisterId)
                    }
                }
            }
        }

        SchedulingPanelFrame {
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: root._currentSectionIndex() === 5
            title: "Resources"
            subtitle: "Project resource pressure and utilization indicators."

            AppWidgets.DataTable {
                Layout.fillWidth: true
                Layout.fillHeight: true
                columns: [
                    { "key": "resource", "label": "Resource", "flex": 1.4 },
                    { "key": "allocation", "label": "Allocation", "flex": 0.8 },
                    { "key": "capacity", "label": "Capacity", "flex": 0.8 },
                    { "key": "utilization", "label": "Utilization", "flex": 0.8 },
                    { "key": "tasks", "label": "Tasks", "flex": 0.5 },
                    { "key": "status", "label": "Status", "flex": 0.8, "type": "status" }
                ]
                rows: root._resourceRows()
                emptyText: root.resourceLoadingModel.emptyState || "No resource load data is available."
                loading: false
            }
        }

        SchedulingPanelFrame {
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: root._currentSectionIndex() === 6
            title: "Activity Feed"
            subtitle: "Recent planning actions, warnings, and control events."

            AppWidgets.ActivityFeed {
                Layout.fillWidth: true
                Layout.fillHeight: true
                items: root.activityFeedModel.items || []
                emptyText: root.activityFeedModel.emptyState || "No planning activity has been recorded."
            }
        }
    }
}

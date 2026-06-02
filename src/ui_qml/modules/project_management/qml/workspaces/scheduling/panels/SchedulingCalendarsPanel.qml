pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import "../components"

Item {
    id: root

    property var workspaceController: null
    property var calendarModel: ({
        "summaryText": "", "workingDays": [], "hoursPerDay": "8", "holidays": [], "emptyState": ""
    })
    property var workingDayDraft: []
    property string hoursPerDayDraft: "8"
    property string selectedHolidayId: ""

    signal workingDayDraftChanged(var draft)
    signal hoursPerDayDraftChanged(string hours)
    signal selectedHolidayIdChanged(string holidayId)

    readonly property var _calendarColumns: [
        { "key": "calendar",    "label": "Calendar",      "flex": 1.0 },
        { "key": "workingDays", "label": "Working Days",  "flex": 1.7 },
        { "key": "shiftPattern","label": "Shift Pattern", "flex": 1.0 },
        { "key": "hoursPerDay", "label": "Hours/Day",     "flex": 0.8 },
        { "key": "exceptions",  "label": "Exceptions",    "flex": 0.8 }
    ]
    readonly property var _holidayColumns: [
        { "key": "date",      "label": "Date",       "flex": 0.9, "sortable": true },
        { "key": "exception", "label": "Exception",  "flex": 1.2 },
        { "key": "calendar",  "label": "Calendar",   "flex": 1.0 },
        { "key": "details",   "label": "Details",    "flex": 1.8 }
    ]

    function _optionIndex(options, value) {
        const list = options || []
        for (let i = 0; i < list.length; i++) {
            if (String(list[i].value || "") === String(value || "")) return i
        }
        return list.length > 0 ? 0 : -1
    }

    SchedulingPanelFrame {
        anchors.fill: parent
        title: "Calendars"
        subtitle: "Working-week rules, holiday exceptions, and working-day calculations for the current schedule calendar."

        ScrollView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.margins: Theme.AppTheme.marginMd
            contentWidth: availableWidth
            clip: true

            ColumnLayout {
                width: parent.width
                spacing: Theme.AppTheme.spacingSm

                SchedulingActionBar {
                    Layout.fillWidth: true
                    isBusy: root.workspaceController ? root.workspaceController.isBusy : false
                    actions: [
                        { "id": "save",             "label": "Save Calendar",     "icon": "save",    "enabled": true },
                        { "id": "add_exception",    "label": "Add Exception",     "icon": "add",     "enabled": true },
                        { "id": "delete_exception", "label": "Delete Exception",  "icon": "delete",  "danger": true, "enabled": root.selectedHolidayId.length > 0 },
                        { "id": "calculate",        "label": "Calculate Days",    "icon": "refresh", "enabled": true }
                    ]

                    AppControls.ComboBox {
                        Layout.preferredWidth: 190
                        model: root.workspaceController ? (root.workspaceController.calendarOptions || []) : []
                        textRole: "label"
                        enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                            && (root.workspaceController ? (root.workspaceController.calendarOptions || []).length > 0 : false)
                        currentIndex: root._optionIndex(
                            root.workspaceController ? (root.workspaceController.calendarOptions || []) : [],
                            root.workspaceController ? root.workspaceController.selectedCalendarId : "default"
                        )
                        onActivated: function(index) {
                            const options = root.workspaceController ? (root.workspaceController.calendarOptions || []) : []
                            if (root.workspaceController !== null && options[index])
                                root.workspaceController.selectCalendar(String(options[index].value || "default"))
                        }
                    }

                    onActionTriggered: function(actionId) {
                        if (root.workspaceController === null) return
                        if (actionId === "save") {
                            root.workspaceController.saveCalendar({
                                "workingDays": root.workingDayDraft,
                                "hoursPerDay": root.hoursPerDayDraft
                            })
                        } else if (actionId === "add_exception") {
                            root.workspaceController.addHoliday({
                                "holidayDate": holidayDateField.text,
                                "name": holidayNameField.text
                            })
                        } else if (actionId === "delete_exception" && root.selectedHolidayId.length > 0) {
                            root.workspaceController.deleteHoliday(root.selectedHolidayId)
                        } else if (actionId === "calculate") {
                            root.workspaceController.calculateWorkingDays({
                                "startDate": calcStartField.text,
                                "workingDays": calcDaysField.text
                            })
                        }
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.AppTheme.spacingMd

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: calendarConfigColumn.implicitHeight + (Theme.AppTheme.marginMd * 2)
                        radius: Theme.AppTheme.radiusSm
                        color: Theme.AppTheme.surfaceOverlay
                        border.color: Theme.AppTheme.subtleBorder
                        border.width: 1

                        ColumnLayout {
                            id: calendarConfigColumn
                            anchors.fill: parent
                            anchors.margins: Theme.AppTheme.marginMd
                            spacing: Theme.AppTheme.spacingSm

                            AppControls.Label { Layout.fillWidth: true; text: "Working Week"; color: Theme.AppTheme.textSecondary; font.family: Theme.AppTheme.fontFamily; font.pixelSize: Theme.AppTheme.captionSize; font.bold: true }

                            Flow {
                                Layout.fillWidth: true
                                spacing: Theme.AppTheme.spacingSm

                                Repeater {
                                    model: root.calendarModel.workingDays || []

                                    delegate: AppControls.CheckBox {
                                        required property var modelData
                                        text: String(modelData.label || "")
                                        checked: (root.workingDayDraft || []).indexOf(modelData.index) >= 0
                                        enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                                        onToggled: {
                                            const next = (root.workingDayDraft || []).slice()
                                            const idx = next.indexOf(modelData.index)
                                            if (checked && idx < 0) next.push(modelData.index)
                                            else if (!checked && idx >= 0) next.splice(idx, 1)
                                            root.workingDayDraftChanged(next)
                                        }
                                    }
                                }
                            }

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: Theme.AppTheme.spacingSm
                                AppControls.Label { text: "Hours/Day"; color: Theme.AppTheme.textMuted; font.family: Theme.AppTheme.fontFamily; font.pixelSize: Theme.AppTheme.captionSize }
                                AppControls.TextField {
                                    Layout.preferredWidth: 96
                                    text: root.hoursPerDayDraft
                                    enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                                    onTextChanged: root.hoursPerDayDraftChanged(text)
                                }
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: calendarExceptionColumn.implicitHeight + (Theme.AppTheme.marginMd * 2)
                        radius: Theme.AppTheme.radiusSm
                        color: Theme.AppTheme.surfaceOverlay
                        border.color: Theme.AppTheme.subtleBorder
                        border.width: 1

                        ColumnLayout {
                            id: calendarExceptionColumn
                            anchors.fill: parent
                            anchors.margins: Theme.AppTheme.marginMd
                            spacing: Theme.AppTheme.spacingSm

                            AppControls.Label { Layout.fillWidth: true; text: "Exceptions & Calculator"; color: Theme.AppTheme.textSecondary; font.family: Theme.AppTheme.fontFamily; font.pixelSize: Theme.AppTheme.captionSize; font.bold: true }

                            AppControls.DateField {
                                id: holidayDateField
                                Layout.fillWidth: true
                                placeholderText: "Holiday date (YYYY-MM-DD)"
                                enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                            }

                            AppControls.TextField {
                                id: holidayNameField
                                Layout.fillWidth: true
                                placeholderText: "Exception label"
                                enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                            }

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: Theme.AppTheme.spacingSm
                                AppControls.DateField {
                                    id: calcStartField
                                    Layout.fillWidth: true
                                    placeholderText: "Calc start (YYYY-MM-DD)"
                                    enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                                }
                                AppControls.TextField {
                                    id: calcDaysField
                                    Layout.preferredWidth: 96
                                    placeholderText: "Days"
                                    enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                                }
                            }

                            AppWidgets.InlineMessage {
                                Layout.fillWidth: true
                                visible: String(root.workspaceController ? root.workspaceController.calculatorResult : "").length > 0
                                tone: "success"
                                message: root.workspaceController ? root.workspaceController.calculatorResult : ""
                            }
                        }
                    }
                }

                AppWidgets.InlineMessage {
                    Layout.fillWidth: true
                    visible: String(root.calendarModel.summaryText || "").length > 0
                    tone: "info"
                    message: root.calendarModel.summaryText || ""
                }

                AppWidgets.TableToolbar {
                    id: calendarsToolbar
                    Layout.fillWidth: true
                    searchText: root.workspaceController ? root.workspaceController.calendarsSearchText : ""
                    searchPlaceholder: "Search calendar exceptions..."
                    showCustomize: true
                    showExport: false
                    showRefresh: false
                    isBusy: root.workspaceController ? root.workspaceController.isBusy : false
                    onSearchChanged: function(text) { if (root.workspaceController) root.workspaceController.setCalendarsSearchText(text) }
                    onCustomizeClicked: holidaysTable.openColumnCustomizer(calendarsToolbar.customizeButtonItem)
                }

                AppWidgets.DataTable {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 200
                    columns: root._calendarColumns
                    sourceModel: root.workspaceController ? root.workspaceController.calendarSummaryTableModel : null
                    loading: false
                    emptyText: "No calendar summary is available."
                }

                AppWidgets.DataTable {
                    id: holidaysTable
                    Layout.fillWidth: true
                    Layout.preferredHeight: 480
                    columns: root._holidayColumns
                    sourceModel: root.workspaceController ? root.workspaceController.holidayTableModel : null
                    selectedRowId: root.selectedHolidayId
                    loading: root.workspaceController ? root.workspaceController.isLoading : false
                    emptyText: root.calendarModel.emptyState || "No holiday exceptions are configured."
                    onRowSelected: function(rowId) { root.selectedHolidayIdChanged(String(rowId || "")) }
                }

                Item { Layout.preferredHeight: Theme.AppTheme.marginMd }
            }
        }
    }
}

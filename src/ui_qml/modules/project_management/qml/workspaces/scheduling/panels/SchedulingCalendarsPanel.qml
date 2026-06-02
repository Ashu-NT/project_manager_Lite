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
    readonly property var _checkedDays: {
        const days = root.calendarModel.workingDays || []
        const selected = []
        for (let index = 0; index < days.length; index++) {
            if (days[index].checked === true)
                selected.push(days[index])
        }
        return selected
    }

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
        subtitle: "Shared working-calendar context consumed by scheduling, with read-only summary and working-day preview."

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
                        { "id": "calculate", "label": "Calculate Days", "icon": "refresh", "enabled": true },
                        { "id": "refresh",   "label": "Refresh",        "icon": "refresh", "enabled": true }
                    ]

                    AppControls.ComboBox {
                        Layout.preferredWidth: 220
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
                        if (root.workspaceController === null)
                            return
                        if (actionId === "calculate") {
                            root.workspaceController.calculateWorkingDays({
                                "startDate": calcStartField.text,
                                "workingDays": calcDaysField.text
                            })
                        } else if (actionId === "refresh") {
                            root.workspaceController.refresh()
                        }
                    }
                }

                AppWidgets.InlineMessage {
                    Layout.fillWidth: true
                    tone: "info"
                    message: "Shared working calendars are managed in Platform Admin. PM Scheduling consumes the selected calendar read-only here."
                }

                AppWidgets.InlineMessage {
                    Layout.fillWidth: true
                    visible: String(root.calendarModel.summaryText || "").length > 0
                    tone: "info"
                    message: root.calendarModel.summaryText || ""
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.AppTheme.spacingMd

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: workingWeekColumn.implicitHeight + (Theme.AppTheme.marginMd * 2)
                        radius: Theme.AppTheme.radiusSm
                        color: Theme.AppTheme.surfaceOverlay
                        border.color: Theme.AppTheme.subtleBorder
                        border.width: 1

                        ColumnLayout {
                            id: workingWeekColumn
                            anchors.fill: parent
                            anchors.margins: Theme.AppTheme.marginMd
                            spacing: Theme.AppTheme.spacingSm

                            AppControls.Label {
                                Layout.fillWidth: true
                                text: "Working Week"
                                color: Theme.AppTheme.textSecondary
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.captionSize
                                font.bold: true
                            }

                            Flow {
                                Layout.fillWidth: true
                                spacing: Theme.AppTheme.spacingSm

                                Repeater {
                                    model: root._checkedDays

                                    delegate: Rectangle {
                                        required property var modelData
                                        height: 26
                                        radius: Theme.AppTheme.radiusSm
                                        color: Theme.AppTheme.navSelectedBackground
                                        border.color: Theme.AppTheme.subtleBorder
                                        border.width: 1
                                        width: dayLabel.implicitWidth + Theme.AppTheme.spacingLg

                                        AppControls.Label {
                                            id: dayLabel
                                            anchors.centerIn: parent
                                            text: String(modelData.label || "")
                                            color: Theme.AppTheme.accent
                                            font.pixelSize: Theme.AppTheme.captionSize
                                            font.bold: true
                                        }
                                    }
                                }
                            }

                            AppControls.Label {
                                Layout.fillWidth: true
                                text: "Hours / Day: " + String(root.calendarModel.hoursPerDay || "8")
                                color: Theme.AppTheme.textPrimary
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.smallSize
                                font.bold: true
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: calculatorColumn.implicitHeight + (Theme.AppTheme.marginMd * 2)
                        radius: Theme.AppTheme.radiusSm
                        color: Theme.AppTheme.surfaceOverlay
                        border.color: Theme.AppTheme.subtleBorder
                        border.width: 1

                        ColumnLayout {
                            id: calculatorColumn
                            anchors.fill: parent
                            anchors.margins: Theme.AppTheme.marginMd
                            spacing: Theme.AppTheme.spacingSm

                            AppControls.Label {
                                Layout.fillWidth: true
                                text: "Working-Day Preview"
                                color: Theme.AppTheme.textSecondary
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.captionSize
                                font.bold: true
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
                    loading: root.workspaceController ? root.workspaceController.isLoading : false
                    emptyText: root.calendarModel.emptyState || "No holiday exceptions are configured."
                }

                Item { Layout.preferredHeight: Theme.AppTheme.marginMd }
            }
        }
    }
}

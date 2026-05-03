pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme
import ProjectManagement.Widgets 1.0 as ProjectManagementWidgets

Item {
    id: root

    property var calendarModel: ({
        "summaryText": "",
        "workingDays": [],
        "hoursPerDay": "8",
        "holidays": [],
        "emptyState": ""
    })
    property string calculatorResult: ""
    property bool isBusy: false
    property var workingDayStates: []

    signal saveCalendarRequested(var payload)
    signal addHolidayRequested(var payload)
    signal deleteHolidayRequested(string holidayId)
    signal calculateRequested(var payload)

    function resetWorkingDayStates() {
        root.workingDayStates = (root.calendarModel.workingDays || []).map(function(day) {
            return {
                "index": day.index,
                "label": day.label,
                "checked": Boolean(day.checked)
            }
        })
    }

    function selectedWorkingDays() {
        var values = []
        for (var index = 0; index < root.workingDayStates.length; index += 1) {
            var day = root.workingDayStates[index]
            if (day && day.checked) {
                values.push(day.index)
            }
        }
        return values
    }

    onCalendarModelChanged: root.resetWorkingDayStates()
    Component.onCompleted: root.resetWorkingDayStates()

    implicitHeight: calendarLayout.implicitHeight

    GridLayout {
        id: calendarLayout

        width: parent ? parent.width : implicitWidth
        columns: width > 1120 ? 3 : 1
        columnSpacing: Theme.AppTheme.spacingMd
        rowSpacing: Theme.AppTheme.spacingMd

        Rectangle {
            Layout.fillWidth: true
            Layout.alignment: Qt.AlignTop
            radius: Theme.AppTheme.radiusLg
            color: Theme.AppTheme.surface
            border.color: Theme.AppTheme.border
            implicitHeight: settingsColumn.implicitHeight + (Theme.AppTheme.marginLg * 2)

            ColumnLayout {
                id: settingsColumn

                anchors.fill: parent
                anchors.margins: Theme.AppTheme.marginLg
                spacing: Theme.AppTheme.spacingMd

                Label {
                    Layout.fillWidth: true
                    text: "Working Calendar"
                    color: Theme.AppTheme.textPrimary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.bodySize
                    font.bold: true
                }

                Label {
                    Layout.fillWidth: true
                    text: String(root.calendarModel.summaryText || "")
                    color: Theme.AppTheme.textSecondary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                    wrapMode: Text.WordWrap
                }

                Flow {
                    Layout.fillWidth: true
                    spacing: Theme.AppTheme.spacingSm

                    Repeater {
                        id: dayRepeater
                        model: root.workingDayStates

                        delegate: CheckBox {
                            id: dayCheck
                            required property var modelData
                            required property int index

                            text: String(dayCheck.modelData.label || "")
                            checked: Boolean(dayCheck.modelData.checked)
                            enabled: !root.isBusy

                            onToggled: {
                                var updated = root.workingDayStates.slice()
                                updated[index] = {
                                    "index": dayCheck.modelData.index,
                                    "label": dayCheck.modelData.label,
                                    "checked": checked
                                }
                                root.workingDayStates = updated
                            }
                        }
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.AppTheme.spacingSm

                    Label {
                        text: "Hours / day"
                        color: Theme.AppTheme.textPrimary
                        font.family: Theme.AppTheme.fontFamily
                    }

                    TextField {
                        id: hoursField
                        Layout.preferredWidth: 120
                        text: String(root.calendarModel.hoursPerDay || "8")
                        placeholderText: "8"
                        enabled: !root.isBusy
                    }

                    Item { Layout.fillWidth: true }

                    AppControls.PrimaryButton {
                        text: "Save Calendar"
                        enabled: !root.isBusy
                        onClicked: root.saveCalendarRequested({
                            "workingDays": root.selectedWorkingDays(),
                            "hoursPerDay": hoursField.text
                        })
                    }
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.alignment: Qt.AlignTop
            radius: Theme.AppTheme.radiusLg
            color: Theme.AppTheme.surface
            border.color: Theme.AppTheme.border
            implicitHeight: calculatorColumn.implicitHeight + (Theme.AppTheme.marginLg * 2)

            ColumnLayout {
                id: calculatorColumn

                anchors.fill: parent
                anchors.margins: Theme.AppTheme.marginLg
                spacing: Theme.AppTheme.spacingMd

                Label {
                    Layout.fillWidth: true
                    text: "Working-Day Calculator"
                    color: Theme.AppTheme.textPrimary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.bodySize
                    font.bold: true
                }

                Label {
                    Layout.fillWidth: true
                    text: "Preview finish dates using the current working calendar and non-working days."
                    color: Theme.AppTheme.textSecondary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                    wrapMode: Text.WordWrap
                }

                TextField {
                    id: calculatorStartDateField
                    Layout.fillWidth: true
                    placeholderText: "Start date (YYYY-MM-DD)"
                    enabled: !root.isBusy
                }

                TextField {
                    id: calculatorDaysField
                    Layout.fillWidth: true
                    placeholderText: "Working days"
                    enabled: !root.isBusy
                }

                AppControls.PrimaryButton {
                    text: "Calculate"
                    enabled: !root.isBusy
                    onClicked: root.calculateRequested({
                        "startDate": calculatorStartDateField.text,
                        "workingDays": calculatorDaysField.text
                    })
                }

                Label {
                    Layout.fillWidth: true
                    text: String(root.calculatorResult || "Run the calculator to preview the working-day finish date.")
                    color: Theme.AppTheme.textSecondary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                    wrapMode: Text.WordWrap
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.alignment: Qt.AlignTop
            radius: Theme.AppTheme.radiusLg
            color: Theme.AppTheme.surface
            border.color: Theme.AppTheme.border
            implicitHeight: holidaysColumn.implicitHeight + (Theme.AppTheme.marginLg * 2)

            ColumnLayout {
                id: holidaysColumn

                anchors.fill: parent
                anchors.margins: Theme.AppTheme.marginLg
                spacing: Theme.AppTheme.spacingMd

                Label {
                    Layout.fillWidth: true
                    text: "Non-Working Days"
                    color: Theme.AppTheme.textPrimary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.bodySize
                    font.bold: true
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.AppTheme.spacingSm

                    TextField {
                        id: holidayDateField
                        Layout.fillWidth: true
                        placeholderText: "Holiday date (YYYY-MM-DD)"
                        enabled: !root.isBusy
                    }

                    TextField {
                        id: holidayNameField
                        Layout.fillWidth: true
                        placeholderText: "Label"
                        enabled: !root.isBusy
                    }
                }

                AppControls.PrimaryButton {
                    text: "Add Non-Working Day"
                    enabled: !root.isBusy
                    onClicked: root.addHolidayRequested({
                        "holidayDate": holidayDateField.text,
                        "name": holidayNameField.text
                    })
                }

                ProjectManagementWidgets.RecordListCard {
                    Layout.fillWidth: true
                    title: "Holiday Register"
                    subtitle: "These days are skipped during scheduling and working-day calculations."
                    emptyState: String(root.calendarModel.emptyState || "")
                    items: root.calendarModel.holidays || []
                    tertiaryActionLabel: "Remove"
                    tertiaryDanger: true
                    actionsEnabled: !root.isBusy

                    onTertiaryActionRequested: function(itemData) {
                        var state = itemData && itemData.state ? itemData.state : (itemData || {})
                        root.deleteHolidayRequested(String(state.holidayId || ""))
                    }
                }
            }
        }
    }
}

pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme

// One Month-grid day cell. Purely presentational: every fact it shows
// (working/non-working, hours, holiday/exception labels, tone) comes from
// the backend-resolved CalendarDayViewModel (`dayData`) built once per
// range fetch -- this component never calculates working status, hours, or
// exceptions itself. `isToday` also comes from `dayData` (the calendar's
// own business-local today); `isCurrentMonth`/`isSelected` are pure view
// state owned by the parent grid.
Item {
    id: root

    property var dayData: ({
        "date": "", "dayNumber": 0, "dateLabel": "", "isToday": false,
        "isWorkingDay": false, "availableHours": 0, "primaryLabel": "",
        "secondaryLabel": "", "tone": "normal", "accessibilityLabel": ""
    })
    property bool isCurrentMonth: true
    property bool isSelected: false

    signal activated()

    readonly property var _toneColors: ({
        "normal":     { "bg": "transparent",            "fg": Theme.AppTheme.textPrimary },
        "nonWorking": { "bg": Theme.AppTheme.surfaceAlt, "fg": Theme.AppTheme.textMuted },
        "holiday":    { "bg": Theme.AppTheme.accentSoft, "fg": Theme.AppTheme.accent },
        "unavailable":{ "bg": Theme.AppTheme.dangerSoft, "fg": Theme.AppTheme.danger },
        "reduced":    { "bg": Theme.AppTheme.warningSoft,"fg": Theme.AppTheme.warning },
        "extra":      { "bg": Theme.AppTheme.successSoft,"fg": Theme.AppTheme.success },
        "info":       { "bg": Theme.AppTheme.infoSoft,   "fg": Theme.AppTheme.info }
    })
    readonly property var _tone: root._toneColors[String(root.dayData.tone || "normal")] || root._toneColors.normal

    implicitWidth: 120
    implicitHeight: 86
    opacity: root.isCurrentMonth ? 1.0 : 0.45

    activeFocusOnTab: true
    Accessible.role: Accessible.Button
    Accessible.name: String(root.dayData.accessibilityLabel || "")
    Accessible.onPressAction: root.activated()
    Keys.onPressed: (event) => {
        if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter || event.key === Qt.Key_Space) {
            root.activated()
            event.accepted = true
        }
    }

    Rectangle {
        anchors.fill: parent
        anchors.margins: 2
        radius: Theme.AppTheme.radiusSm
        color: root.isSelected ? Theme.AppTheme.selectedSurface : root._tone.bg
        border.width: root.activeFocus ? 2 : (root.dayData.isToday ? 2 : 0)
        border.color: root.activeFocus ? Theme.AppTheme.focusBorder : Theme.AppTheme.accent
    }

    MouseArea {
        anchors.fill: parent
        cursorShape: Qt.PointingHandCursor
        onClicked: {
            root.forceActiveFocus()
            root.activated()
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.AppTheme.spacingXs
        spacing: 2

        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.AppTheme.spacingXs

            AppControls.Label {
                text: String(root.dayData.dayNumber || "")
                color: root._tone.fg
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.bodySize
                font.bold: root.dayData.isToday
            }

            Item { Layout.fillWidth: true }
        }

        AppControls.Label {
            Layout.fillWidth: true
            visible: String(root.dayData.primaryLabel || "").length > 0
            text: String(root.dayData.primaryLabel || "")
            color: root._tone.fg
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.captionSize
            font.bold: true
            elide: Text.ElideRight
            maximumLineCount: 1
        }

        AppControls.Label {
            Layout.fillWidth: true
            visible: String(root.dayData.secondaryLabel || "").length > 0
            text: String(root.dayData.secondaryLabel || "")
            color: Theme.AppTheme.textMuted
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.captionSize
            elide: Text.ElideRight
            maximumLineCount: 1
        }

        Item { Layout.fillHeight: true }
    }
}

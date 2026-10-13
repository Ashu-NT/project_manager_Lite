pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Icons 1.0 as AppIcons
import App.Theme 1.0 as Theme

// One Month-grid day cell. Purely presentational: every fact it shows
// (working/non-working, hours, holiday/exception labels, tone) comes from
// the backend-resolved CalendarDayViewModel (`dayData`) built once per
// range fetch -- this component never calculates working status, hours, or
// exceptions itself. `isToday` also comes from `dayData` (the calendar's
// own business-local today); `isCurrentMonth`/`isSelected` are pure view
// state owned by the parent grid.
//
// Every cell shares one card system (same border, radius, padding)
// regardless of tone, so a plain working weekday and a weekend/holiday read
// as the same kind of surface -- only the tint and an optional small status
// icon vary. "Today" and "selected" are deliberately two independent,
// simultaneously-visible treatments: today is a small accent badge behind
// the day number, selected is the cell's own border/background -- so a day
// that is both still shows both facts at once.
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

    readonly property var _toneStyles: ({
        "normal":      { "wash": "transparent",              "fg": Theme.AppTheme.textPrimary, "icon": "" },
        "nonWorking":  { "wash": Theme.AppTheme.surfaceAlt,   "fg": Theme.AppTheme.textMuted,   "icon": "" },
        "holiday":     { "wash": Theme.AppTheme.accentSoft,   "fg": Theme.AppTheme.accent,      "icon": "risk" },
        "unavailable": { "wash": Theme.AppTheme.dangerSoft,   "fg": Theme.AppTheme.danger,      "icon": "risk" },
        "reduced":     { "wash": Theme.AppTheme.warningSoft,  "fg": Theme.AppTheme.warning,     "icon": "time" },
        "extra":       { "wash": Theme.AppTheme.successSoft,  "fg": Theme.AppTheme.success,     "icon": "add" },
        "info":        { "wash": Theme.AppTheme.infoSoft,     "fg": Theme.AppTheme.info,        "icon": "notifications" }
    })
    readonly property var _tone: root._toneStyles[String(root.dayData.tone || "normal")] || root._toneStyles.normal

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

    // Base card: every cell gets the same surface + border, regardless of
    // tone, so working weekdays never look like bare text on the page.
    Rectangle {
        id: _card
        anchors.fill: parent
        anchors.margins: 2
        radius: Theme.AppTheme.radiusSm
        color: root.isSelected
            ? Theme.AppTheme.selectedSurface
            : (_hoverArea.containsMouse ? Theme.AppTheme.hoverSurface : Theme.AppTheme.surface)
        border.width: root.activeFocus ? 2 : 1
        border.color: root.activeFocus
            ? Theme.AppTheme.focusBorder
            : (root.isSelected ? Theme.AppTheme.accent : Theme.AppTheme.subtleBorder)

        // Tone wash: a soft tint layered above the base card, never a full
        // opaque repaint -- keeps non-working/exception days readable
        // without turning them into heavy, saturated blocks.
        Rectangle {
            anchors.fill: parent
            radius: parent.radius
            visible: root._tone.wash !== "transparent" && !root.isSelected
            color: root._tone.wash
        }
    }

    MouseArea {
        id: _hoverArea
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: {
            root.forceActiveFocus()
            root.activated()
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.AppTheme.spacingSm
        spacing: 2

        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.AppTheme.spacingXs

            // Today gets its own small accent badge behind the day number --
            // independent of (and simultaneous with) the selected treatment
            // on the cell itself.
            Rectangle {
                visible: root.dayData.isToday
                Layout.preferredWidth: 22
                Layout.preferredHeight: 22
                radius: 11
                color: Theme.AppTheme.accent

                AppControls.Label {
                    anchors.centerIn: parent
                    text: String(root.dayData.dayNumber || "")
                    color: Theme.AppTheme.textOnAccent
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.bodySize
                    font.bold: true
                }
            }

            AppControls.Label {
                visible: !root.dayData.isToday
                text: String(root.dayData.dayNumber || "")
                color: root._tone.fg
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.bodySize
            }

            Item { Layout.fillWidth: true }

            AppIcons.AppIcon {
                visible: String(root._tone.icon || "").length > 0
                name: String(root._tone.icon || "default")
                size: Theme.AppTheme.iconXs
                iconColor: root._tone.fg
            }
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

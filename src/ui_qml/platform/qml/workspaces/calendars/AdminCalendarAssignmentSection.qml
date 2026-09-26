pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

Item {
    id: root

    property string entityType: ""
    property string entityId: ""
    property string entityLabel: ""
    property var assignedCalendar: ({})
    property var sourceChain: []
    property bool busy: false
    // Opt-in: a resolved "effective calendar" summary (own override, else
    // the Organization default), pre-computed server-side into a display-
    // ready {hasCalendar, calendarName, source ("override"/"inherited"),
    // workingWeekLabel, timeZone, holidaySetLabel} shape -- see
    // site_calendar_summary() in controllers/calendars/context.py. When
    // provided (non-empty calendarName), this replaces the generic
    // "Assigned Calendar" card below with the richer Effective Calendar
    // view. Department/Employee sections leave this at its default empty
    // object and keep today's raw-assignment-only view unchanged.
    property var effectiveCalendarSummary: ({})

    signal assignCalendarRequested()
    signal removeAssignmentRequested(string assignmentId)
    signal openCalendarManagementRequested()

    readonly property bool _hasCalendar: String(root.assignedCalendar && root.assignedCalendar.calendarId ? root.assignedCalendar.calendarId : "").length > 0
    readonly property string _calendarName: String(root.assignedCalendar && root.assignedCalendar.calendarName ? root.assignedCalendar.calendarName : "")
    readonly property string _calendarType: String(root.assignedCalendar && root.assignedCalendar.calendarType ? root.assignedCalendar.calendarType : "")
    readonly property string _effectiveFrom: String(root.assignedCalendar && root.assignedCalendar.effectiveFrom ? root.assignedCalendar.effectiveFrom : "")
    readonly property string _effectiveTo: String(root.assignedCalendar && root.assignedCalendar.effectiveTo ? root.assignedCalendar.effectiveTo : "")
    readonly property var _chainItems: Array.isArray(root.sourceChain) ? root.sourceChain : []
    readonly property bool _hasEffectiveSummary: String(root.effectiveCalendarSummary && root.effectiveCalendarSummary.calendarName ? root.effectiveCalendarSummary.calendarName : "").length > 0
    readonly property bool _effectiveIsOverride: root.effectiveCalendarSummary && root.effectiveCalendarSummary.source === "override"
    readonly property real _cardHeaderHeight: Theme.AppTheme.sectionTitleSize + Theme.AppTheme.spacingMd * 2 + Theme.AppTheme.spacingSm

    implicitHeight: contentColumn.implicitHeight

    function _cardHeight(contentHeight) {
        return contentHeight + root._cardHeaderHeight + Theme.AppTheme.marginMd * 2
    }

    ColumnLayout {
        id: contentColumn
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        spacing: Theme.AppTheme.spacingMd

        AppWidgets.SectionHeading {
            Layout.fillWidth: true
            label: "Calendar"
        }

        ColumnLayout {
            Layout.fillWidth: true
            Layout.leftMargin: Theme.AppTheme.spacingMd
            Layout.rightMargin: Theme.AppTheme.spacingMd
            spacing: Theme.AppTheme.spacingMd

            AppWidgets.InlineMessage {
                Layout.fillWidth: true
                tone: "info"
                message: "Calendar rules define working hours, holidays, and availability. Manage calendar definitions in Calendar Management."
            }

            AppWidgets.SectionCard {
                Layout.fillWidth: true
                visible: root._hasEffectiveSummary
                implicitHeight: root._cardHeight(effectiveCardContent.implicitHeight)
                title: "Effective Calendar"
                outlined: true

                ColumnLayout {
                    id: effectiveCardContent
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: Theme.AppTheme.marginMd
                    spacing: Theme.AppTheme.spacingSm

                    GridLayout {
                        Layout.fillWidth: true
                        columns: 2
                        columnSpacing: Theme.AppTheme.spacingLg
                        rowSpacing: Theme.AppTheme.spacingSm

                        Repeater {
                            model: [
                                { "label": "Effective Calendar", "value": String(root.effectiveCalendarSummary.calendarName || "") },
                                { "label": "Source", "value": root._effectiveIsOverride
                                    ? (root.entityType.length > 0 ? root.entityType.charAt(0).toUpperCase() + root.entityType.slice(1) + " override" : "Override")
                                    : "Inherited from Organization" },
                                { "label": "Working Week", "value": String(root.effectiveCalendarSummary.workingWeekLabel || "-") },
                                { "label": "Time Zone", "value": String(root.effectiveCalendarSummary.timeZone || "-") },
                                { "label": "Holiday Rules", "value": String(root.effectiveCalendarSummary.holidaySetLabel || "-") }
                            ]
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
                                    text: String(modelData.value || "")
                                    color: Theme.AppTheme.textPrimary
                                    font.pixelSize: Theme.AppTheme.smallSize
                                    wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                                }
                            }
                        }
                    }
                }
            }

            AppWidgets.SectionCard {
                Layout.fillWidth: true
                visible: !root._hasEffectiveSummary
                implicitHeight: root._cardHeight(calendarCardContent.implicitHeight)
                title: "Assigned Calendar"
                outlined: true

                ColumnLayout {
                    id: calendarCardContent
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: Theme.AppTheme.marginMd
                    spacing: Theme.AppTheme.spacingSm

                    AppWidgets.InlineMessage {
                        Layout.fillWidth: true
                        visible: !root._hasCalendar
                        tone: "warning"
                        message: "No calendar assigned. This " + root.entityType + " inherits from its parent in the calendar hierarchy."
                    }

                    GridLayout {
                        Layout.fillWidth: true
                        visible: root._hasCalendar
                        columns: 2
                        columnSpacing: Theme.AppTheme.spacingLg
                        rowSpacing: Theme.AppTheme.spacingSm

                        Repeater {
                            model: [
                                { "label": "Calendar Name", "value": root._calendarName },
                                { "label": "Calendar Type", "value": root._calendarType },
                                { "label": "Effective From", "value": root._effectiveFrom || "—" },
                                { "label": "Effective To", "value": root._effectiveTo || "Open" }
                            ]
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
                                    text: String(modelData.value || "")
                                    color: Theme.AppTheme.textPrimary
                                    font.pixelSize: Theme.AppTheme.smallSize
                                    wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                                }
                            }
                        }
                    }
                }
            }

            AppWidgets.SectionCard {
                Layout.fillWidth: true
                visible: root._chainItems.length > 0
                implicitHeight: root._cardHeight(chainContent.implicitHeight)
                title: "Inheritance Chain"
                outlined: true

                ColumnLayout {
                    id: chainContent
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: Theme.AppTheme.marginMd
                    spacing: Theme.AppTheme.spacingSm

                    Repeater {
                        model: root._chainItems
                        delegate: RowLayout {
                            required property string modelData
                            required property int index
                            Layout.fillWidth: true
                            spacing: Theme.AppTheme.spacingSm

                            AppControls.Label {
                                text: root.index === 0 ? "↳" : "↓"
                                color: Theme.AppTheme.textMuted
                                font.pixelSize: Theme.AppTheme.smallSize
                            }
                            AppControls.Label {
                                Layout.fillWidth: true
                                text: String(modelData || "")
                                color: Theme.AppTheme.textSecondary
                                font.pixelSize: Theme.AppTheme.smallSize
                                font.bold: root.index === root._chainItems.length - 1
                            }
                        }
                    }
                }
            }

            AppWidgets.SectionCard {
                Layout.fillWidth: true
                implicitHeight: root._cardHeight(mgmtContent.implicitHeight)
                title: "Calendar Management"
                outlined: true

                ColumnLayout {
                    id: mgmtContent
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: Theme.AppTheme.marginMd
                    spacing: Theme.AppTheme.spacingSm

                    AppControls.Label {
                        Layout.fillWidth: true
                        text: "Working rules, exceptions, recurring events, and shift patterns are managed centrally in Calendar Management."
                        color: Theme.AppTheme.textSecondary
                        font.pixelSize: Theme.AppTheme.smallSize
                        wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                    }

                    AppControls.Label {
                        Layout.fillWidth: true
                        text: "Use the actions above to assign or change this " + root.entityType + "'s calendar. Use Calendar Management to define calendar rules and holidays."
                        color: Theme.AppTheme.textMuted
                        font.pixelSize: Theme.AppTheme.captionSize
                        wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                    }
                }
            }
        }
    }
}

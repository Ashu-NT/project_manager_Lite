pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import QtQuick.Window
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Icons 1.0 as AppIcons
import App.Theme 1.0 as Theme

// Calendar tab's "Recurring" view: recurring meetings, training, and
// maintenance windows that reduce/extend available capacity on a schedule.
// Selecting a row opens the shared InspectorPanel on the right -- the same
// interaction model as Month's day selection and the Exceptions view.
Item {
    id: root
    implicitHeight: _layout.implicitHeight

    property var recurringEvents: []
    property string selectedRecurringEventId: ""
    property bool canWrite: true
    // Shared fixed height for the Month/Exceptions/Recurring content area
    // (see CalendarScheduleSection.qml) -- 0 means "size to this view's own
    // row count" so it still works when used standalone/in tests.
    property int fixedContentHeight: 0

    signal addRecurringEventRequested()
    signal editRecurringEventRequested(string eventId)
    signal deleteRecurringEventRequested()
    signal toggleActiveRequested(string eventId, bool active)
    signal recurringEventSelected(string eventId)

    property string _searchText: ""
    property string _typeFilter: "All"
    property string _statusFilter: "All"
    property bool _advancedExpanded: false

    readonly property bool _showInspector: root._selectedEvent !== null

    readonly property int _naturalTableHeight: Theme.AppTheme.headerHeight
        + Math.max(1, Math.min(root._tableRows.length, 8)) * Theme.AppTheme.normalRowHeight
        + Theme.AppTheme.spacingLg
    readonly property int _tableHeight: root.fixedContentHeight > 0 ? root.fixedContentHeight : root._naturalTableHeight

    readonly property var _columns: [
        { "key": "title", "label": "Event", "flex": 1.3 },
        { "key": "recurrenceLabel", "label": "Repeats", "flex": 1.5 },
        { "key": "typeLabel", "label": "Type", "flex": 0.9 },
        { "key": "impactChip", "label": "Impact", "flex": 1.0, "type": "status" },
        { "key": "validityLabel", "label": "Validity", "flex": 1.0 },
        { "key": "statusChip", "label": "Status", "flex": 0.7, "type": "status" }
    ]

    function _uniqueLabels(key) {
        const seen = {}
        const values = []
        for (let i = 0; i < root.recurringEvents.length; i += 1) {
            const label = String(root.recurringEvents[i][key] || "")
            if (label.length > 0 && !seen[label]) { seen[label] = true; values.push(label) }
        }
        return ["All"].concat(values.sort())
    }
    readonly property var _typeOptions: root._uniqueLabels("typeLabel")
    readonly property var _statusOptions: ["All", "Active", "Inactive"]

    readonly property var _filteredRows: {
        const query = root._searchText.trim().toLowerCase()
        return root.recurringEvents.filter(function(row) {
            if (root._typeFilter !== "All" && row.typeLabel !== root._typeFilter) return false
            if (root._statusFilter !== "All" && row.statusLabel !== root._statusFilter) return false
            if (query.length === 0) return true
            return String(row.title || "").toLowerCase().indexOf(query) >= 0
                || String(row.recurrenceLabel || "").toLowerCase().indexOf(query) >= 0
        })
    }
    readonly property var _tableRows: root._filteredRows.map(function(row) {
        const validity = String(row.effectiveFromLabel || "")
            + (row.effectiveToLabel ? (" – " + row.effectiveToLabel) : " – No end")
        return Object.assign({}, row, {
            "validityLabel": validity,
            "impactChip": { "label": row.impactLabel, "tone": row.impactTone },
            "statusChip": { "label": row.statusLabel, "tone": row.statusTone }
        })
    })

    readonly property var _selectedEvent: {
        for (let i = 0; i < root.recurringEvents.length; i += 1) {
            if (String(root.recurringEvents[i].id) === root.selectedRecurringEventId) return root.recurringEvents[i]
        }
        return null
    }

    onSelectedRecurringEventIdChanged: root._advancedExpanded = false

    readonly property var _inspectorGroups: {
        const evt = root._selectedEvent
        if (!evt) return []
        const endsLabel = evt.effectiveToLabel ? evt.effectiveToLabel : "No end"
        return [
            {
                "title": "Event",
                "rows": [
                    { "label": "Type", "value": evt.typeLabel },
                    { "label": "Impact", "value": evt.impactLabel }
                ]
            },
            {
                "title": "Recurrence",
                "rows": [
                    { "label": "Repeats", "value": evt.recurrenceLabel },
                    { "label": "Starts", "value": evt.effectiveFromLabel },
                    { "label": "Ends", "value": endsLabel }
                ]
            },
            {
                "title": "Schedule",
                "rows": [
                    { "label": "Time", "value": evt.startTimeLabel + "–" + evt.endTimeLabel },
                    { "label": "Capacity Impact", "value": evt.capacityImpactPercent > 0 ? (evt.capacityImpactPercent + "%") : "" }
                ]
            },
            {
                "title": "Status",
                "rows": [
                    { "label": "State", "value": evt.statusLabel }
                ]
            }
        ]
    }

    readonly property var _menuActions: {
        const evt = root._selectedEvent
        if (!evt || !root.canWrite) return []
        const items = []
        items.push(evt.isActive
            ? { "id": "deactivate", "label": "Deactivate", "icon": "reject", "enabled": true }
            : { "id": "activate", "label": "Activate", "icon": "approve", "enabled": true })
        items.push({ "id": "delete", "label": "Delete", "icon": "delete", "danger": true, "enabled": true })
        return items
    }

    ColumnLayout {
        id: _layout
        width: parent ? parent.width : root.width
        spacing: Theme.AppTheme.spacingMd

        AppWidgets.TableToolbar {
            Layout.fillWidth: true
            searchText: root._searchText
            searchPlaceholder: "Search recurring events..."
            showFilter: false
            showCreate: root.canWrite
            createLabel: "Add Recurring Event"
            onSearchChanged: function(text) { root._searchText = text }
            onCreateRequested: root.addRecurringEventRequested()

            AppControls.ComboBox {
                model: root._typeOptions
                currentIndex: Math.max(0, root._typeOptions.indexOf(root._typeFilter))
                onActivated: function(index) { root._typeFilter = root._typeOptions[index] }
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
                objectName: "calendarRecurringTable"
                Layout.fillWidth: true
                Layout.preferredHeight: root._tableHeight
                rows: root._tableRows
                columns: root._columns
                selectedRowId: root.selectedRecurringEventId
                emptyText: "No recurring events defined for this calendar."
                onRowSelected: function(rowId) { root.recurringEventSelected(String(rowId || "")) }
                onRowActivated: function(rowId) { root.recurringEventSelected(String(rowId || "")) }
            }

            AppWidgets.InspectorPanel {
                id: _inspector
                objectName: "calendarRecurringInspector"
                visible: root._showInspector && Window.width >= Theme.AppTheme.compactContentBreakpoint
                Layout.alignment: Qt.AlignTop
                Layout.preferredHeight: root._tableHeight

                preferredWidth: 260
                minimumWidth: 190
                availableWidth: root._showInspector ? Math.round(_layout.width * 0.3) : -1

                title: root._selectedEvent ? String(root._selectedEvent.title || "") : ""
                statusLabel: root._selectedEvent ? String(root._selectedEvent.statusLabel || "") : ""
                statusTone: root._selectedEvent ? String(root._selectedEvent.statusTone || "neutral") : "neutral"
                groups: root._inspectorGroups

                showEditAction: root.canWrite
                editActionLabel: "Edit Recurring Event"
                menuActions: root._menuActions
                menuTriggerLabel: "Actions"

                onCloseRequested: root.recurringEventSelected("")
                onEditRequested: root.editRecurringEventRequested(root.selectedRecurringEventId)
                onMenuActionTriggered: function(id) {
                    const evt = root._selectedEvent
                    if (!evt) return
                    if (id === "delete") { root.deleteRecurringEventRequested(); return }
                    if (id === "activate") { root.toggleActiveRequested(evt.id, true); return }
                    if (id === "deactivate") { root.toggleActiveRequested(evt.id, false); return }
                }

                // Advanced/raw RRULE is intentionally collapsed and
                // read-only -- normal users manage recurrence through the
                // Edit dialog's visual builder, never by hand-editing RRULE.
                ColumnLayout {
                    Layout.fillWidth: true
                    visible: root._selectedEvent !== null
                    spacing: Theme.AppTheme.spacingXs

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Theme.AppTheme.spacingXs

                        AppIcons.AppIcon {
                            name: root._advancedExpanded ? "chevron_down" : "chevron_right"
                            size: Theme.AppTheme.iconXs
                            iconColor: Theme.AppTheme.textMuted
                        }
                        AppControls.Label {
                            text: "Advanced recurrence"
                            color: Theme.AppTheme.textMuted
                            font.pixelSize: Theme.AppTheme.captionSize
                        }
                        Item { Layout.fillWidth: true }

                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: root._advancedExpanded = !root._advancedExpanded
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        visible: root._advancedExpanded
                        spacing: 2

                        AppControls.Label {
                            text: "Generated RRULE"
                            color: Theme.AppTheme.textMuted
                            font.pixelSize: Theme.AppTheme.captionSize
                        }
                        AppControls.Label {
                            Layout.fillWidth: true
                            text: root._selectedEvent ? String(root._selectedEvent.recurrenceRule || "") : ""
                            color: Theme.AppTheme.textSecondary
                            font.pixelSize: Theme.AppTheme.captionSize
                            wrapMode: Text.WrapAnywhere
                        }
                    }
                }
            }
        }
    }
}

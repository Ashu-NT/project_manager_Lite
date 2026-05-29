pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Mock 1.0 as AppMock
import App.Theme 1.0 as Theme

Item {
    id: root

    // ── Properties (matches TimesheetEntriesCard API) ─────────────────
    property var    assignmentSummary:   AppMock.MockFactory.fieldRecord("", "", "Select a task assignment.")
    property var    assignmentOptions:   []
    property var    periodOptions:       []
    property string selectedPeriodStart: ""
    property var    entriesModel:        AppMock.MockFactory.catalog("Time Entries", "", "Select a task assignment.")
    property var    entriesTableModel:   null
    property var    selectedEntryDetail: AppMock.MockFactory.fieldRecord()
    property string selectedEntryId:     ""
    property bool   isBusy:             false
    property string errorText:          ""

    // ── Signals ───────────────────────────────────────────────────────
    signal periodChanged(string periodStart)
    signal assignmentChanged(string assignmentId)
    signal entrySelected(string entryId)
    signal addRequested(var payload)
    signal updateRequested(var payload)
    signal deleteRequested(string entryId)
    signal submitRequested(var payload)
    signal lockRequested(var payload)
    signal unlockRequested(var payload)

    // ── Private helpers ───────────────────────────────────────────────
    readonly property var    _items: root.entriesModel.items || []
    readonly property var    _state: root.assignmentSummary.state || {}
    readonly property var    _entryState: root.selectedEntryDetail.state || {}
    readonly property bool   _hasAssignment: Boolean(root._state.assignmentId)
    readonly property bool   _hasEntry:      Boolean(root._entryState.entryId)
    readonly property bool   _canSubmit:     Boolean(root._state.resourceId)
        && Boolean(root._state.periodStart)
    readonly property bool   _canUnlock:     Boolean(root._state.periodId)

    readonly property int _tableH: {
        const n = root._items.length
        const rH = Theme.AppTheme.compactRowHeight
        const hH = Theme.AppTheme.normalRowHeight
        return n === 0 ? (hH + 80) : (hH + n * rH + 12)
    }

    readonly property var _columns: [
        { key: "title",       label: "Period / Date", flex: 2,   sortable: false },
        { key: "subtitle",    label: "Resource",      flex: 2,   sortable: false },
        { key: "metaText",    label: "Hours / Note",  flex: 2,   sortable: false },
        { key: "statusLabel", label: "Status",        flex: 0,   minWidth: 90, type: "status" }
    ]

    // Sync form fields when a time entry is selected
    onSelectedEntryDetailChanged: {
        if (root._entryState.entryId) {
            _dateField.text  = String(root._entryState.entryDate || "")
            _hoursField.text = String(root._entryState.hours || "")
            _noteArea.text   = String(root._entryState.note || "")
        } else {
            _dateField.text  = ""
            _hoursField.text = ""
            _noteArea.text   = ""
        }
    }

    implicitHeight: Math.min(_col.implicitHeight, 520)

    Flickable {
        anchors.fill:   parent
        contentWidth:   width
        contentHeight:  _col.implicitHeight
        clip:           true
        ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

    ColumnLayout {
        id: _col
        width:   parent.width
        spacing: 0

        // ── Section toolbar ───────────────────────────────────────────
        AppWidgets.ContextualActionToolbar {
            Layout.fillWidth: true
            title:    "Time Entries"
            subtitle: root._items.length > 0 ? String(root._items.length) : ""
            busy:     root.isBusy
            createLabel: ""
            actions: []
            onActionTriggered: function(actionId) {
                if (actionId === "submit") {
                    root.submitRequested({
                        "resourceId":  root._state.resourceId   || "",
                        "periodStart": root._state.periodStart  || "",
                        "note":        _periodNoteArea.text
                    })
                } else if (actionId === "lock") {
                    root.lockRequested({
                        "resourceId":  root._state.resourceId   || "",
                        "periodStart": root._state.periodStart  || "",
                        "note":        _periodNoteArea.text
                    })
                } else if (actionId === "unlock") {
                    root.unlockRequested({
                        "periodId": root._state.periodId || "",
                        "note":     _periodNoteArea.text
                    })
                }
            }
        }

        AppWidgets.InlineMessage {
            Layout.fillWidth: true
            visible: root.errorText.length > 0
            tone: "danger"
            message: root.errorText
        }

        // ── Assignment summary + period selector ──────────────────────
        Rectangle {
            Layout.fillWidth: true
            height: _summaryRow.implicitHeight + Theme.AppTheme.spacingMd * 2
            color:  Theme.AppTheme.surfaceAlt
            visible: String(root.assignmentSummary.title || "").length > 0
                || root.assignmentOptions.length > 0
                || root.periodOptions.length > 0

            Rectangle {
                anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom
                height: 1; color: Theme.AppTheme.divider
            }

            RowLayout {
                id: _summaryRow
                anchors.left:        parent.left
                anchors.right:       parent.right
                anchors.verticalCenter: parent.verticalCenter
                anchors.leftMargin:  Theme.AppTheme.marginMd
                anchors.rightMargin: Theme.AppTheme.marginMd
                spacing: Theme.AppTheme.spacingMd

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 2

                    AppControls.Label {
                        Layout.fillWidth: true
                        visible: String(root.assignmentSummary.title || "").length > 0
                        text:           root.assignmentSummary.title || ""
                        color:          Theme.AppTheme.textPrimary
                        font.family:    Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.smallSize
                        font.bold:      true
                        elide:          Text.ElideRight
                    }

                    AppControls.Label {
                        Layout.fillWidth: true
                        visible: String(root.assignmentSummary.subtitle || "").length > 0
                        text:           root.assignmentSummary.subtitle || ""
                        color:          Theme.AppTheme.textMuted
                        font.family:    Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.captionSize
                        elide:          Text.ElideRight
                    }
                }

                AppControls.ComboBox {
                    Layout.preferredWidth: 280
                    visible: root.assignmentOptions.length > 0
                    model: root.assignmentOptions
                    textRole: "label"
                    enabled: !root.isBusy
                    currentIndex: {
                        const opts = root.assignmentOptions
                        const assignmentId = String(root._state.assignmentId || "")
                        for (let i = 0; i < opts.length; i++) {
                            if (String(opts[i].value || "") === assignmentId)
                                return i
                        }
                        return 0
                    }
                    onActivated: function(idx) {
                        const opt = root.assignmentOptions[idx]
                        if (opt)
                            root.assignmentChanged(String(opt.value || ""))
                    }
                }

                AppControls.ComboBox {
                    Layout.preferredWidth: 160
                    visible: root.periodOptions.length > 0
                    model:        root.periodOptions
                    textRole:     "label"
                    enabled:      !root.isBusy
                    currentIndex: {
                        const opts = root.periodOptions
                        const val  = root.selectedPeriodStart
                        for (let i = 0; i < opts.length; i++) {
                            if (String(opts[i].value || "") === String(val || "")) return i
                        }
                        return 0
                    }
                    onActivated: function(idx) {
                        const opt = root.periodOptions[idx]
                        if (opt) root.periodChanged(String(opt.value || ""))
                    }
                }
            }
        }

        // ── Entry form (date + hours + note) ─────────────────────────
        Item {
            Layout.fillWidth: true
            implicitHeight: _formCol.implicitHeight + Theme.AppTheme.spacingMd * 2
            visible: root._hasAssignment

            ColumnLayout {
                id: _formCol
                anchors.left:    parent.left
                anchors.right:   parent.right
                anchors.top:     parent.top
                anchors.margins: Theme.AppTheme.spacingMd
                spacing:         Theme.AppTheme.spacingSm

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.AppTheme.spacingMd

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 3

                        AppControls.Label {
                            text:           "Date"
                            color:          Theme.AppTheme.textMuted
                            font.family:    Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.captionSize
                            font.bold:      true
                        }

                        AppControls.DateField {
                            id: _dateField
                            Layout.fillWidth: true
                            enabled:         !root.isBusy
                            placeholderText: "YYYY-MM-DD"
                            font.family:     Theme.AppTheme.fontFamily
                            font.pixelSize:  Theme.AppTheme.smallSize
                        }
                    }

                    ColumnLayout {
                        Layout.preferredWidth: 120
                        spacing: 3

                        AppControls.Label {
                            text:           "Hours"
                            color:          Theme.AppTheme.textMuted
                            font.family:    Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.captionSize
                            font.bold:      true
                        }

                        AppControls.TextField {
                            id: _hoursField
                            Layout.fillWidth: true
                            enabled:         !root.isBusy
                            placeholderText: "8.00"
                            font.family:     Theme.AppTheme.fontFamily
                            font.pixelSize:  Theme.AppTheme.smallSize
                        }
                    }
                }

                AppControls.TextArea {
                    id: _noteArea
                    Layout.fillWidth:    true
                    Layout.preferredHeight: 72
                    enabled:             !root.isBusy
                    placeholderText:     "Work completed during this entry…"
                    wrapMode:            TextEdit.WordWrap
                    font.family:         Theme.AppTheme.fontFamily
                    font.pixelSize:      Theme.AppTheme.smallSize
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.AppTheme.spacingXs

                    AppControls.PrimaryButton {
                        text:    "Add Entry"
                        iconName: "add"
                        enabled: !root.isBusy && root._hasAssignment
                        onClicked: root.addRequested({
                            "assignmentId": root._state.assignmentId || "",
                            "entryDate":    _dateField.text,
                            "hours":        _hoursField.text,
                            "note":         _noteArea.text
                        })
                    }

                    AppControls.SecondaryButton {
                        text:    "Update"
                        iconName: "edit"
                        enabled: !root.isBusy && root._hasEntry
                        onClicked: root.updateRequested({
                            "entryId":   root._entryState.entryId || "",
                            "entryDate": _dateField.text,
                            "hours":     _hoursField.text,
                            "note":      _noteArea.text
                        })
                    }

                    AppControls.SecondaryButton {
                        text:    "Delete"
                        iconName: "delete"
                        danger:  true
                        enabled: !root.isBusy && root._hasEntry
                        onClicked: root.deleteRequested(String(root._entryState.entryId || ""))
                    }
                }
            }
        }

        // ── Entries DataTable ─────────────────────────────────────────
        Item {
            Layout.fillWidth: true
            height: root._tableH

            AppWidgets.DataTable {
                anchors.fill:  parent
                columns:       root._columns
                sourceModel:   root.entriesTableModel
                selectedRowId: root.selectedEntryId
                loading:       root.isBusy
                emptyText:     root.entriesModel.emptyState || "No time entries for this period."

                onRowSelected: function(rowId) {
                    root.entrySelected(rowId)
                }
                onRowActivated: function(rowId) {
                    root.entrySelected(rowId)
                }
            }
        }

        // ── Period note + submit/lock/unlock ──────────────────────────
        Item {
            Layout.fillWidth: true
            implicitHeight: _periodCol.implicitHeight + Theme.AppTheme.spacingMd * 2
            visible: root._canSubmit || root._canUnlock

            ColumnLayout {
                id: _periodCol
                anchors.left:    parent.left
                anchors.right:   parent.right
                anchors.top:     parent.top
                anchors.margins: Theme.AppTheme.spacingMd
                spacing:         Theme.AppTheme.spacingSm

                Rectangle {
                    Layout.fillWidth: true
                    height: 1
                    color: Theme.AppTheme.divider
                }

                AppControls.TextArea {
                    id: _periodNoteArea
                    Layout.fillWidth:       true
                    Layout.preferredHeight: 64
                    enabled:                !root.isBusy
                    placeholderText:        "Optional note for period submission or lock…"
                    wrapMode:               TextEdit.WordWrap
                    font.family:            Theme.AppTheme.fontFamily
                    font.pixelSize:         Theme.AppTheme.smallSize
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.AppTheme.spacingXs

                    AppControls.PrimaryButton {
                        text:    "Submit Period"
                        iconName: "approve"
                        enabled: !root.isBusy && root._canSubmit
                        onClicked: root.submitRequested({
                            "resourceId":  root._state.resourceId  || "",
                            "periodStart": root._state.periodStart || "",
                            "note":        _periodNoteArea.text
                        })
                    }

                    AppControls.SecondaryButton {
                        text:    "Lock"
                        iconName: "approve"
                        enabled: !root.isBusy && root._canSubmit
                        onClicked: root.lockRequested({
                            "resourceId":  root._state.resourceId  || "",
                            "periodStart": root._state.periodStart || "",
                            "note":        _periodNoteArea.text
                        })
                    }

                    AppControls.SecondaryButton {
                        text:    "Unlock"
                        iconName: "close"
                        enabled: !root.isBusy && root._canUnlock
                        onClicked: root.unlockRequested({
                            "periodId": root._state.periodId || "",
                            "note":     _periodNoteArea.text
                        })
                    }
                }
            }
        }
    }  // ColumnLayout
    }  // Flickable
}

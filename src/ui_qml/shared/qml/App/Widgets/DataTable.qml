pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Theme 1.0 as Theme
import App.Widgets 1.0 as AppWidgets
import App.Icons 1.0 as AppIcons

// Enterprise data table backed by a virtualized ListView.
//
// Public API (backward-compatible):
//   columns  [{key, label, flex, minWidth, sortable, type, visible}]
//   rows     [{id, ...fieldValues}]
//   type     "text" | "status" | "progress"
//            progress rawValue: number 0-1  OR  {value: 0-1, label: "72%"}
//   flex  0  → fixed minWidth column; flex > 0 → proportional fill
//
// New optional props: loading, emptyText
Item {
    id: root

    // ── Public API ────────────────────────────────────────────────────
    property var    columns:        []
    property var    rows:           []
    property string selectedRowId:  ""
    property string sortKey:        ""
    property int    sortDirection:  Qt.AscendingOrder
    property bool   showFilter:     false
    property bool   loading:        false
    property string emptyText:      "No records"

    property bool   multiSelect:    false
    property var    selectedRowIds: []

    signal rowSelected(string rowId)
    signal rowActivated(string rowId)
    signal sortRequested(string key)
    signal rowSelectionToggled(string rowId, bool selected)
    signal selectAllToggled(bool allSelected)
    signal filterClicked()
    signal viewDetailRequested(string rowId)

    // ── Private helpers ───────────────────────────────────────────────
    function _isRowChecked(rowId) {
        const ids = root.selectedRowIds || []
        for (let i = 0; i < ids.length; i++) {
            if (String(ids[i]) === String(rowId)) return true
        }
        return false
    }

    readonly property bool _allChecked:  root.rows.length > 0
        && (root.selectedRowIds || []).length >= root.rows.length
    readonly property bool _someChecked: (root.selectedRowIds || []).length > 0 && !root._allChecked

    readonly property int  _cbColW: 32          // checkbox column width (sticky, not scrolled)

    readonly property var _visCols: {
        const r = []
        for (let i = 0; i < root.columns.length; i++) {
            if (root.columns[i].visible !== false) r.push(root.columns[i])
        }
        return r
    }

    readonly property real _flexTotal: {
        let t = 0
        for (let i = 0; i < root._visCols.length; i++) {
            const f = root._visCols[i].flex
            t += (f !== undefined ? f : 1)
        }
        return t > 0 ? t : 1
    }

    // Sum of all column minWidths — threshold for triggering horizontal scroll
    readonly property real _minDataW: {
        let w = 0
        for (let i = 0; i < root._visCols.length; i++) {
            const mw = root._visCols[i].minWidth
            w += (mw !== undefined ? mw : 80)
        }
        return w
    }

    // Width available for data columns (excludes checkbox column)
    readonly property real _dataAreaW: root.width - (root.multiSelect ? root._cbColW : 0)

    // Effective data width — at least as wide as the viewport so flex columns fill it
    readonly property real _dataW: Math.max(root._dataAreaW, root._minDataW)

    // Total scrollable content width including the sticky checkbox column
    readonly property real _totalW: (root.multiSelect ? root._cbColW : 0) + root._dataW

    // Horizontal scroll is needed when columns exceed the viewport
    readonly property bool _needsHScroll: root._minDataW > root._dataAreaW + 1

    // Horizontal scroll offset (pixels) — driven by ScrollBar and WheelHandler
    property real _contentX: 0

    // Reset offset if scroll is no longer needed after a column visibility change
    onColumnsChanged: { if (!root._needsHScroll) root._contentX = 0 }

    // Compute pixel width for a single column descriptor
    function _colWidth(col) {
        const minW = col.minWidth !== undefined ? col.minWidth : 80
        const flex  = col.flex    !== undefined ? col.flex    : 1
        if (flex === 0) return minW
        return Math.max(minW, (root._dataW * flex) / root._flexTotal)
    }

    // Apply a column-visibility draft from TableColumnCustomizer
    function _applyColumnVisibility(draft) {
        const vm = {}
        for (let j = 0; j < draft.length; j++) vm[draft[j].key] = draft[j].visible
        const next = []
        for (let i = 0; i < root.columns.length; i++) {
            const c = JSON.parse(JSON.stringify(root.columns[i]))
            if (c.key in vm) c.visible = vm[c.key]
            next.push(c)
        }
        root.columns = next
    }

    // ── Horizontal wheel / trackpad handler ───────────────────────────
    // Intercepts horizontal trackpad scroll and Shift+wheel.
    // Drives _hScrollBar.position which then sets _contentX via onPositionChanged.
    WheelHandler {
        id: _wheelH
        target:          null
        acceptedDevices: PointerDevice.Mouse | PointerDevice.TouchPad
        onWheel: function(event) {
            if (!root._needsHScroll) return
            const dx = event.angleDelta.x
            const dy = event.angleDelta.y
            const isHoriz = Math.abs(dx) > Math.abs(dy)
                || (event.modifiers & Qt.ShiftModifier)
            if (!isHoriz) return

            const delta  = (dx !== 0) ? dx : dy
            const maxX   = Math.max(0, root._totalW - root.width)
            const newX   = Math.max(0, Math.min(root._contentX - delta * 0.5, maxX))
            if (root._totalW > root.width)
                _hScrollBar.position = newX / root._totalW
            event.accepted = true
        }
    }

    // ── Action bar (Customize columns + optional Filter) ──────────────
    Rectangle {
        id: _actionBar
        anchors.top:   parent.top
        anchors.left:  parent.left
        anchors.right: parent.right
        height: Theme.AppTheme.toolbarHeight - 6
        color:  Theme.AppTheme.surfaceRaised

        Rectangle {
            anchors { left: parent.left; right: parent.right; bottom: parent.bottom }
            height: 1
            color:  Theme.AppTheme.divider
        }

        Row {
            anchors.right:          parent.right
            anchors.rightMargin:    8
            anchors.verticalCenter: parent.verticalCenter
            spacing: 2

            Item {
                visible: root.showFilter
                width:  60
                height: Theme.AppTheme.inputHeight - 8

                Rectangle {
                    anchors.fill: parent
                    radius: Theme.AppTheme.radiusSm
                    color:  _filterMA.containsMouse
                        ? Theme.AppTheme.hoverSurface : Theme.AppTheme.surfaceOverlay
                }
                Row {
                    anchors.centerIn: parent
                    spacing: 4
                    AppIcons.AppIcon {
                        name: "filter"; size: 11
                        iconColor: Theme.AppTheme.textMuted
                        anchors.verticalCenter: parent.verticalCenter
                    }
                    Text {
                        text:           "Filter"
                        color:          Theme.AppTheme.textMuted
                        font.pixelSize: Theme.AppTheme.captionSize
                        font.family:    Theme.AppTheme.fontFamily
                        anchors.verticalCenter: parent.verticalCenter
                    }
                }
                MouseArea {
                    id: _filterMA
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape:  Qt.PointingHandCursor
                    onClicked:    root.filterClicked()
                }
            }

            Rectangle {
                visible: root.showFilter
                width: 1; height: 14
                color: Theme.AppTheme.divider
                anchors.verticalCenter: parent.verticalCenter
            }

            Item {
                visible: root.columns.length > 0
                width:  84
                height: Theme.AppTheme.inputHeight - 8

                Rectangle {
                    anchors.fill: parent
                    radius: Theme.AppTheme.radiusSm
                    color:  _custMA.containsMouse
                        ? Theme.AppTheme.hoverSurface : Theme.AppTheme.surfaceOverlay
                }
                Text {
                    anchors.centerIn: parent
                    text:           "Customize"
                    color:          Theme.AppTheme.textMuted
                    font.pixelSize: Theme.AppTheme.captionSize
                    font.family:    Theme.AppTheme.fontFamily
                }

                AppWidgets.TableColumnCustomizer {
                    id: _colCustomizer
                    parent: _actionBar
                    x: _actionBar.width - width - 4
                    y: _actionBar.height + 2
                    columns: root.columns
                    onColumnVisibilityChanged: function(draft) {
                        root._applyColumnVisibility(draft)
                    }
                }

                MouseArea {
                    id: _custMA
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape:  Qt.PointingHandCursor
                    onClicked:    _colCustomizer.open()
                }
            }
        }
    }

    // ── Sticky column header ──────────────────────────────────────────
    Rectangle {
        id: _header
        anchors.top:   _actionBar.bottom
        anchors.left:  parent.left
        anchors.right: parent.right
        height: Theme.AppTheme.normalRowHeight
        color:  Theme.AppTheme.surfaceAlt
        z: 2

        Row {
            anchors.fill: parent

            // Select-all checkbox — sticky, not scrolled
            Item {
                width:   root._cbColW
                height:  parent.height
                visible: root.multiSelect

                CheckBox {
                    id: _headerCb
                    anchors.centerIn: parent
                    checkState: root._allChecked  ? Qt.Checked
                              : root._someChecked ? Qt.PartiallyChecked
                                                  : Qt.Unchecked
                    tristate: true
                    padding:  0
                    spacing:  0

                    indicator: Rectangle {
                        implicitWidth: 14; implicitHeight: 14; radius: 2
                        color: _headerCb.checkState !== Qt.Unchecked
                            ? Theme.AppTheme.accent : "transparent"
                        border.color: _headerCb.checkState !== Qt.Unchecked
                            ? Theme.AppTheme.accent : Theme.AppTheme.subtleBorder
                        border.width: 1
                        Text {
                            anchors.centerIn: parent
                            text:  _headerCb.checkState === Qt.PartiallyChecked ? "—" : "✓"
                            color: "white"
                            font.pixelSize: 9; font.bold: true
                            visible: _headerCb.checkState !== Qt.Unchecked
                        }
                    }
                    contentItem: Item { implicitWidth: 0; implicitHeight: 14 }
                    onClicked: root.selectAllToggled(!root._allChecked)
                }
            }

            // Scrollable header cells — clip + offset by _contentX
            Item {
                width:  parent.width - (root.multiSelect ? root._cbColW : 0)
                height: parent.height
                clip:   true

                Row {
                    x:      -root._contentX
                    height: parent.height

                    Repeater {
                        model: root._visCols

                        delegate: Item {
                            id: _hCell
                            required property var modelData
                            required property int index

                            readonly property bool _sorted: root.sortKey === _hCell.modelData.key

                            width:  root._colWidth(_hCell.modelData)
                            height: Theme.AppTheme.normalRowHeight

                            RowLayout {
                                anchors.fill:        parent
                                anchors.leftMargin:  Theme.AppTheme.spacingSm
                                anchors.rightMargin: Theme.AppTheme.spacingXs
                                spacing: 3

                                Label {
                                    Layout.fillWidth: true
                                    text:           _hCell.modelData.label || ""
                                    color:          _hCell._sorted
                                        ? Theme.AppTheme.accent : Theme.AppTheme.textMuted
                                    font.family:    Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.captionSize
                                    font.bold:      true
                                    elide:          Text.ElideRight
                                }
                                Text {
                                    visible:        _hCell._sorted
                                    text:           root.sortDirection === Qt.AscendingOrder ? "▲" : "▼"
                                    color:          Theme.AppTheme.accent
                                    font.pixelSize: 7
                                }
                            }

                            // Column separator
                            Rectangle {
                                anchors.right:  parent.right
                                anchors.top:    parent.top
                                anchors.bottom: parent.bottom
                                width:   1
                                color:   Theme.AppTheme.divider
                                visible: _hCell.index < root._visCols.length - 1
                            }

                            MouseArea {
                                anchors.fill: parent
                                enabled:     _hCell.modelData.sortable !== false
                                cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
                                onClicked:   root.sortRequested(_hCell.modelData.key)
                            }
                        }
                    }
                }
            }
        }

        // Header bottom border
        Rectangle {
            anchors { left: parent.left; right: parent.right; bottom: parent.bottom }
            height: 1; color: Theme.AppTheme.divider
        }
    }

    // ── Horizontal scrollbar ──────────────────────────────────────────
    ScrollBar {
        id: _hScrollBar
        anchors.left:   parent.left
        anchors.right:  parent.right
        anchors.bottom: parent.bottom
        orientation: Qt.Horizontal
        height:  root._needsHScroll ? 10 : 0
        visible: root._needsHScroll
        size:    root._needsHScroll
            ? Math.min(1.0, root.width / root._totalW) : 1.0
        policy:  root._needsHScroll ? ScrollBar.AlwaysOn : ScrollBar.AlwaysOff

        onPositionChanged: {
            if (!root._needsHScroll) return
            const maxScroll = Math.max(0, root._totalW - root.width)
            root._contentX  = Math.max(0, Math.min(position * root._totalW, maxScroll))
        }
    }

    // ── Virtualized row list ──────────────────────────────────────────
    ListView {
        id: _rowList
        anchors.top:    _header.bottom
        anchors.left:   parent.left
        anchors.right:  parent.right
        anchors.bottom: _hScrollBar.top
        clip:                  true
        model:                 root.rows
        reuseItems:            true
        keyNavigationEnabled:  true
        focus:                 true
        boundsBehavior:        Flickable.StopAtBounds
        highlightMoveDuration: 0

        ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

        Keys.onUpPressed:     { if (currentIndex > 0) decrementCurrentIndex() }
        Keys.onDownPressed:   { if (currentIndex < count - 1) incrementCurrentIndex() }
        Keys.onReturnPressed: {
            if (currentIndex >= 0 && root.rows[currentIndex])
                root.rowActivated(String(root.rows[currentIndex].id || ""))
        }

        delegate: Item {
            id: _row
            required property var modelData
            required property int index

            readonly property string _rid: String(_row.modelData.id || String(_row.index))
            readonly property bool   _sel: root.selectedRowId === _row._rid
            readonly property bool   _chk: root.multiSelect && root._isRowChecked(_row._rid)
            readonly property bool   _hi:  _row._sel || _row._chk

            width:  _rowList.width
            height: Theme.AppTheme.compactRowHeight

            // ── Row background + selection accent ─────────────────────
            Rectangle {
                anchors.fill: parent
                color: _row._hi
                    ? Theme.AppTheme.selectedSurface
                    : _rowMA.containsMouse
                        ? Theme.AppTheme.hoverSurface
                        : _row.index % 2 !== 0
                            ? Theme.AppTheme.surfaceOverlay : "transparent"

                Rectangle {
                    width: 2
                    anchors { top: parent.top; bottom: parent.bottom; left: parent.left }
                    color:   Theme.AppTheme.accent
                    visible: _row._hi
                }
            }

            // ── Row content ───────────────────────────────────────────
            Row {
                anchors.fill: parent

                // Sticky checkbox (does not scroll)
                Item {
                    width:   root._cbColW
                    height:  Theme.AppTheme.compactRowHeight
                    visible: root.multiSelect

                    CheckBox {
                        id: _rowCb
                        anchors.centerIn: parent
                        checked: root._isRowChecked(_row._rid)
                        padding: 0; spacing: 0

                        indicator: Rectangle {
                            implicitWidth: 14; implicitHeight: 14; radius: 2
                            color: _rowCb.checked ? Theme.AppTheme.accent : "transparent"
                            border.color:  _rowCb.checked
                                ? Theme.AppTheme.accent : Theme.AppTheme.subtleBorder
                            border.width: 1
                            Text {
                                anchors.centerIn: parent
                                text: "✓"; color: "white"
                                font.pixelSize: 9; font.bold: true
                                visible: _rowCb.checked
                            }
                        }
                        contentItem: Item { implicitWidth: 0; implicitHeight: 14 }
                        onToggled: root.rowSelectionToggled(_row._rid, checked)
                    }
                }

                // Scrollable data cells — clip + offset by _contentX
                Item {
                    width:  parent.width - (root.multiSelect ? root._cbColW : 0)
                    height: Theme.AppTheme.compactRowHeight
                    clip:   true

                    Row {
                        x:      -root._contentX
                        height: parent.height

                        Repeater {
                            model: root._visCols

                            delegate: Item {
                                id: _cell
                                required property var modelData
                                required property int index

                                readonly property var    _raw:  _row.modelData[_cell.modelData.key] !== undefined
                                    ? _row.modelData[_cell.modelData.key] : ""
                                readonly property string _txt:  _cell._raw !== null ? String(_cell._raw) : ""

                                readonly property bool _isSt: _cell.modelData.type === "status"
                                    || _cell.modelData.key === "statusLabel"
                                    || _cell.modelData.key === "status"
                                    || (typeof _cell.modelData.key === "string"
                                        && _cell.modelData.key.indexOf("StatusLabel") >= 0)

                                readonly property bool _isPr: _cell.modelData.type === "progress"

                                readonly property real _pVal: {
                                    if (!_cell._isPr) return 0.0
                                    const rv = _cell._raw
                                    if (rv === null || rv === undefined || rv === "") return 0.0
                                    if (typeof rv === "object") return parseFloat(rv.value || 0)
                                    return parseFloat(rv) || 0.0
                                }
                                readonly property string _pLbl: {
                                    if (!_cell._isPr) return ""
                                    const rv = _cell._raw
                                    return (rv && typeof rv === "object") ? String(rv.label || "") : ""
                                }

                                width:  root._colWidth(_cell.modelData)
                                height: Theme.AppTheme.compactRowHeight

                                // Status chip
                                AppWidgets.StatusChip {
                                    anchors.verticalCenter: parent.verticalCenter
                                    anchors.left:       parent.left
                                    anchors.leftMargin: Theme.AppTheme.spacingSm
                                    visible: _cell._isSt && _cell._txt.length > 0
                                    status:  _cell._txt
                                }

                                // Progress bar + label
                                Item {
                                    anchors.verticalCenter:  parent.verticalCenter
                                    anchors.left:            parent.left
                                    anchors.right:           parent.right
                                    anchors.leftMargin:      Theme.AppTheme.spacingSm
                                    anchors.rightMargin:     Theme.AppTheme.spacingSm
                                    height:  20
                                    visible: _cell._isPr

                                    AppWidgets.ProgressBar {
                                        anchors.left:           parent.left
                                        anchors.right:          _pPct.visible ? _pPct.left : parent.right
                                        anchors.rightMargin:    _pPct.visible ? Theme.AppTheme.spacingXs : 0
                                        anchors.verticalCenter: parent.verticalCenter
                                        value: _cell._pVal
                                    }

                                    Label {
                                        id: _pPct
                                        anchors.right:          parent.right
                                        anchors.verticalCenter: parent.verticalCenter
                                        visible:        _cell._pLbl.length > 0
                                        text:           _cell._pLbl
                                        color:          Theme.AppTheme.textMuted
                                        font.family:    Theme.AppTheme.fontFamily
                                        font.pixelSize: Theme.AppTheme.captionSize
                                    }
                                }

                                // Plain text (default)
                                Label {
                                    anchors.fill:        parent
                                    anchors.leftMargin:  Theme.AppTheme.spacingSm
                                    anchors.rightMargin: Theme.AppTheme.spacingXs
                                    visible:            !_cell._isSt && !_cell._isPr
                                    text:                _cell._txt
                                    verticalAlignment:   Text.AlignVCenter
                                    color: _row._hi
                                        ? Theme.AppTheme.textPrimary
                                        : Theme.AppTheme.textSecondary
                                    font.family:    Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.smallSize
                                    elide:          Text.ElideRight
                                }
                            }
                        }
                    }
                }
            }

            // Row bottom divider
            Rectangle {
                anchors { left: parent.left; right: parent.right; bottom: parent.bottom }
                height: 1; color: Theme.AppTheme.divider
            }

            // Row click area — starts after checkbox column so checkboxes own their events
            MouseArea {
                id: _rowMA
                anchors.top:        parent.top
                anchors.bottom:     parent.bottom
                anchors.left:       parent.left
                anchors.leftMargin: root.multiSelect ? root._cbColW : 0
                anchors.right:      parent.right
                hoverEnabled:  true
                cursorShape:   Qt.PointingHandCursor

                onClicked: {
                    root.selectedRowId = _row._rid
                    root.rowSelected(_row._rid)
                    _rowList.forceActiveFocus()
                    _rowList.currentIndex = _row.index
                }
                onDoubleClicked: root.rowActivated(_row._rid)
            }
        }
    }

    // ── Empty state ───────────────────────────────────────────────────
    AppWidgets.EmptyState {
        anchors.centerIn: _rowList
        width:   Math.min(_rowList.width, 320)
        visible: root.rows.length === 0 && !root.loading
        title:   root.emptyText
    }

    // ── Loading overlay ───────────────────────────────────────────────
    Item {
        anchors.top:    _header.bottom
        anchors.left:   parent.left
        anchors.right:  parent.right
        anchors.bottom: _hScrollBar.top
        visible: root.loading
        z: 5

        Rectangle {
            anchors.fill: parent
            color:   Theme.AppTheme.workspaceBackground
            opacity: 0.75
        }

        BusyIndicator {
            anchors.centerIn: parent
            running: root.loading
        }
    }
}

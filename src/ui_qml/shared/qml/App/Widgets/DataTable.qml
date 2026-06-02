pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Icons 1.0 as AppIcons
import App.Theme 1.0 as Theme
import App.Models 1.0 as AppModels
import App.Controls 1.0 as AppControls

// Enterprise data table — Qt 6 TableView, true 2-D cell-based delegates.
//
// Public API (backward-compatible):
//   columns  [{key, label, flex, minWidth, sortable, type, visible}]
//   rows     [{id, ...fieldValues}]
//   type     "text" | "status" | "progress"
//            progress rawValue: number 0-1  OR  {value:0-1, label:"72%"}
//   flex  0  → fixed minWidth; flex > 0 → proportional fill
//
// Internals:
//   _frozenView  – narrow single-column TableView for the checkbox column
//   _mainView    – main N×M TableView backed by DynamicTableModel (_tableModel)
//   Each _mainView delegate = one cell at (row, column)
Item {
    id: root

    // ── Public API ────────────────────────────────────────────────────
    property var    columns:        []
    property var    rows:           []
    property string selectedRowId:  ""
    property string sortKey:        ""
    property int    sortDirection:  Qt.AscendingOrder
    property bool   clientSideSorting: true
    property bool   showFilter:     false
    property bool   loading:        false
    property string emptyText:      "No records"
    property bool   multiSelect:    false
    property var    selectedRowIds: []
    property var    _selectedLookup: ({})
    property Item   columnCustomizerAnchorItem: null
    property alias  filterButtonItem: _filterButton
    property string tableId: ""
    // Optional Python-owned DynamicTableModel.  When set the rows: path is
    // bypassed entirely — the Python model is used directly as the TableView
    // model and row-count comes from model.rowCountValue.  The rows: property
    // continues to work unchanged when sourceModel is null.
    property var sourceModel: null

    signal rowSelected(string rowId)
    signal rowActivated(string rowId)
    signal sortRequested(string key)
    signal rowSelectionToggled(string rowId, bool selected)
    signal selectAllToggled(bool allSelected)
    signal filterClicked()
    signal viewDetailRequested(string rowId)
    signal columnsStateChanged(var columns)

    // ── Private helpers ───────────────────────────────────────────────
    property int  _hoveredRow:        -1
    property int  _currentRow:        -1
    property bool _layoutPending:     false   // debounce guard for forceLayout

    function _rebuildSelectedLookup() {
        const map = {}
        const ids = root.selectedRowIds || []
        for (let i = 0; i < ids.length; i++) {
            map[String(ids[i])] = true
        }
        root._selectedLookup = map
    }

    function _isRowChecked(rowId) {
        return root._selectedLookup[String(rowId)] === true
    }

    function openColumnCustomizer(anchorItem) {
        if (anchorItem) {
            root.columnCustomizerAnchorItem = anchorItem
        }
        _colCustomizer.anchorItem = root.columnCustomizerAnchorItem || _columnCustomizerAnchor
        _colCustomizer.open()
    }

    function _scheduleMainViewLayout() {
        if (root._layoutPending) return
        root._layoutPending = true
        Qt.callLater(function() {
            root._layoutPending = false
            if (_mainView.width > 0 && _mainView.height > 0) {
                _mainView.forceLayout()
            }
        })
    }

    function _toggleSort(key) {
        const normalizedKey = String(key || "")
        if (!normalizedKey.length) {
            return
        }
        // Update visual indicator — applies whether sourceModel is set or not.
        if (root.sortKey === normalizedKey) {
            root.sortDirection = root.sortDirection === Qt.AscendingOrder
                ? Qt.DescendingOrder
                : Qt.AscendingOrder
        } else {
            root.sortKey = normalizedKey
            root.sortDirection = Qt.AscendingOrder
        }
        // Delegate actual sort: Python model when sourceModel is set,
        // otherwise _displayRows recomputes via clientSideSorting.
        if (root.sourceModel) {
            root.sourceModel.toggleSort(normalizedKey)
        }
    }

    function _sortValue(rawValue) {
        if (rawValue === undefined || rawValue === null || rawValue === "") {
            return null
        }
        if (typeof rawValue === "object") {
            if (rawValue.value !== undefined && rawValue.value !== null && rawValue.value !== "") {
                return rawValue.value
            }
            if (rawValue.label !== undefined && rawValue.label !== null && rawValue.label !== "") {
                return rawValue.label
            }
            if (rawValue.text !== undefined && rawValue.text !== null && rawValue.text !== "") {
                return rawValue.text
            }
            return JSON.stringify(rawValue)
        }
        return rawValue
    }

    function _compareSortValues(leftValue, rightValue) {
        if (leftValue === rightValue) {
            return 0
        }
        if (leftValue === null) {
            return 1
        }
        if (rightValue === null) {
            return -1
        }
        if (typeof leftValue === "boolean" && typeof rightValue === "boolean") {
            return leftValue === rightValue ? 0 : (leftValue ? 1 : -1)
        }

        const leftText = String(leftValue).trim()
        const rightText = String(rightValue).trim()
        const leftNumber = Number(leftValue)
        const rightNumber = Number(rightValue)
        if (leftText.length > 0
                && rightText.length > 0
                && !isNaN(leftNumber)
                && !isNaN(rightNumber)) {
            return leftNumber - rightNumber
        }

        const leftDate = Date.parse(leftText)
        const rightDate = Date.parse(rightText)
        if (!isNaN(leftDate) && !isNaN(rightDate)) {
            return leftDate - rightDate
        }

        return leftText.localeCompare(rightText, undefined, {
            numeric: true,
            sensitivity: "base"
        })
    }

    onSelectedRowIdsChanged: root._rebuildSelectedLookup()
    Component.onCompleted: root._rebuildSelectedLookup()

    readonly property var _displayRows: {
        const sourceRows = root.rows || []
        const rowsCopy = sourceRows.slice()
        if (!root.clientSideSorting || String(root.sortKey || "").length === 0) {
            return rowsCopy
        }
        const key = String(root.sortKey || "")
        const direction = root.sortDirection === Qt.DescendingOrder ? -1 : 1
        rowsCopy.sort(function(leftRow, rightRow) {
            const leftValue = root._sortValue(leftRow ? leftRow[key] : null)
            const rightValue = root._sortValue(rightRow ? rightRow[key] : null)
            return direction * root._compareSortValues(leftValue, rightValue)
        })
        return rowsCopy
    }

    // Total row count — reads from sourceModel when provided, else from _displayRows.
    readonly property int _rowCount: root.sourceModel
        ? root.sourceModel.rowCountValue
        : root._displayRows.length

    readonly property bool _allChecked:  root._rowCount > 0
        && (root.selectedRowIds || []).length >= root._rowCount
    readonly property bool _someChecked: (root.selectedRowIds || []).length > 0 && !root._allChecked

    readonly property int _cbColW: 32

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

    // Width available for data columns (viewport minus frozen checkbox column)
    readonly property real _dataAreaW: root.width - (root.multiSelect ? root._cbColW : 0)

    readonly property real _minDataW: {
        let w = 0
        for (let i = 0; i < root._visCols.length; i++) {
            w += root._columnBaseWidth(root._visCols[i])
        }
        return w
    }

    // Preserve natural widths first, then distribute spare room to flexible columns.
    readonly property real _extraFlexSpace: Math.max(0, root._dataAreaW - root._minDataW)

    function _columnBaseWidth(col) {
        if (!col) return Theme.AppTheme.tableColumnDefaultWidth
        if (col.preferredWidth !== undefined) return col.preferredWidth
        if (col.minWidth !== undefined && col.flex === 0) return col.minWidth

        const type = String(col.type || "text")
        let naturalWidth = Theme.AppTheme.tableColumnDefaultWidth
        if (type === "status") {
            naturalWidth = Theme.AppTheme.tableStatusColumnWidth
        } else if (type === "progress") {
            naturalWidth = Theme.AppTheme.tableProgressColumnWidth
        } else if (String(col.key || "").toLowerCase().indexOf("description") >= 0
                || String(col.key || "").toLowerCase().indexOf("summary") >= 0
                || String(col.key || "").toLowerCase().indexOf("title") >= 0
                || String(col.label || "").toLowerCase().indexOf("name") >= 0) {
            naturalWidth = Theme.AppTheme.tableColumnWideWidth
        }
        if (col.minWidth !== undefined) {
            naturalWidth = Math.max(naturalWidth, col.minWidth)
        }
        return naturalWidth
    }

    function _colWidth(col) {
        if (!col) return Theme.AppTheme.tableColumnDefaultWidth
        const minW = root._columnBaseWidth(col)
        const flex  = col.flex    !== undefined ? col.flex    : 1
        if (flex === 0) return minW
        if (root._minDataW >= root._dataAreaW) {
            return minW
        }
        return Math.max(minW, minW + (root._extraFlexSpace * flex) / root._flexTotal)
    }

    function _applyColumnVisibility(draft) {
        // draft = [{key, label, visible}] — configurable columns only, in user-chosen order.
        // Non-configurable columns (configurable === false) retain their original position at the end.
        const draftByKey = {}
        const draftOrder = []
        for (let j = 0; j < draft.length; j++) {
            draftByKey[draft[j].key] = draft[j]
            draftOrder.push(draft[j].key)
        }
        const originalByKey = {}
        for (let i = 0; i < root.columns.length; i++) {
            originalByKey[root.columns[i].key] = root.columns[i]
        }
        const next = []
        // 1. Configurable columns in draft (user-controlled) order
        for (let j = 0; j < draftOrder.length; j++) {
            const orig = originalByKey[draftOrder[j]]
            if (!orig) continue
            const c = JSON.parse(JSON.stringify(orig))
            c.visible = draftByKey[draftOrder[j]].visible
            next.push(c)
        }
        // 2. Non-configurable columns appended at end in their original order
        for (let i = 0; i < root.columns.length; i++) {
            const c = root.columns[i]
            if (c.configurable === false) {
                next.push(JSON.parse(JSON.stringify(c)))
            }
        }
        root.columns = next
        root.columnsStateChanged(next)
    }

    // ── Python-backed 2-D model ───────────────────────────────────────
    // rows/columns are bound directly; the model filters visible columns
    // internally and emits modelReset whenever either list changes.
    AppModels.DynamicTableModel {
        id: _tableModel
        rows:    root._displayRows
        columns: root.columns
    }

    // When a controller-owned sourceModel is provided, push the QML column
    // definitions into it so the model's role lookups (ColumnTypeRole etc.)
    // resolve correctly against the same column list used by the header.
    Binding {
        when:     root.sourceModel !== null
        target:   root.sourceModel
        property: "columns"
        value:    root.columns
    }

    // Notify the header's columnWidthProvider when visible-column set changes.
    on_VisColsChanged: root._scheduleMainViewLayout()

    Item {
        id: _columnCustomizerAnchor
        anchors.top: root.top
        anchors.right: root.right
        width: 1
        height: _header.height
    }

    TableColumnCustomizer {
        id: _colCustomizer
        anchorItem: root.columnCustomizerAnchorItem || _columnCustomizerAnchor
        columns: root.columns
        onColumnVisibilityChanged: function(draft) {
            root._applyColumnVisibility(draft)
        }
    }

    // ── Sticky column header ──────────────────────────────────────────
    Rectangle {
        id: _header
        anchors.top:   root.top
        anchors.left:  root.left
        anchors.right: root.right
        height: Theme.AppTheme.normalRowHeight
        color:  Theme.AppTheme.surfaceAlt
        z: 2

        Row {
            id: _headerRow
            anchors.fill: _header

            // Checkbox select-all header (fixed, not scrolled)
            Item {
                id: _selectAllHeaderCell
                width:   root._cbColW
                height:  _headerRow.height
                visible: root.multiSelect

                AppControls.CheckBox {
                    id: _headerCb
                    anchors.centerIn: _selectAllHeaderCell
                    checkState: root._allChecked  ? Qt.Checked
                              : root._someChecked ? Qt.PartiallyChecked
                                                  : Qt.Unchecked
                    tristate: true
                    padding:  0; spacing: 0

                    indicator: Rectangle {
                        implicitWidth: 14; implicitHeight: 14; radius: 2
                        color: _headerCb.checkState !== Qt.Unchecked
                            ? Theme.AppTheme.accent : "transparent"
                        border.color: _headerCb.checkState !== Qt.Unchecked
                            ? Theme.AppTheme.accent : Theme.AppTheme.subtleBorder
                        border.width: 1
                        Text {
                            anchors.centerIn: parent
                            text: _headerCb.checkState === Qt.PartiallyChecked ? "—" : "✓"
                            color: "white"
                            font.pixelSize: 9; font.bold: true
                            visible: _headerCb.checkState !== Qt.Unchecked
                        }
                    }
                    contentItem: Item { implicitWidth: 0; implicitHeight: 14 }
                    onClicked: root.selectAllToggled(!root._allChecked)
                }
            }

            // Scrollable header cells — offset synced with _mainView.contentX
            Item {
                id: _headerScrollClip
                width:  _headerRow.width - (root.multiSelect ? root._cbColW : 0)
                height: _headerRow.height
                clip:   true

                Row {
                    id: _headerScrollRow
                    x:      -_mainView.contentX
                    height: _headerScrollClip.height

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

                                AppControls.Label {
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
                                anchors.right:  _hCell.right
                                anchors.top:    _hCell.top
                                anchors.bottom: _hCell.bottom
                                width: 1; color: Theme.AppTheme.divider
                                visible: _hCell.index < root._visCols.length - 1
                            }

                            MouseArea {
                                anchors.fill: parent
                                enabled:      _hCell.modelData.sortable !== false
                                cursorShape:  enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
                                onClicked: {
                                    root._toggleSort(_hCell.modelData.key)
                                    root.sortRequested(_hCell.modelData.key)
                                }
                            }
                        }
                    }
                }
            }
        }

        Rectangle {
            anchors { left: _header.left; right: _header.right; bottom: _header.bottom }
            height: 1; color: Theme.AppTheme.divider
        }

        Rectangle {
            id: _filterButton
            visible: root.showFilter
            anchors.right: _header.right
            anchors.rightMargin: Theme.AppTheme.spacingSm
            anchors.verticalCenter: _header.verticalCenter
            implicitWidth: _filterRow.implicitWidth + 14
            implicitHeight: Theme.AppTheme.inputHeight - 8
            radius: Theme.AppTheme.radiusSm
            color: _filterHover.containsMouse
                ? Theme.AppTheme.hoverSurface
                : Theme.AppTheme.surfaceRaised
            z: 3

            Row {
                id: _filterRow
                anchors.centerIn: parent
                spacing: Theme.AppTheme.spacingXs

                AppIcons.AppIcon {
                    name: "filter"
                    size: Theme.AppTheme.tableIconSize
                    iconColor: Theme.AppTheme.textMuted
                    anchors.verticalCenter: parent.verticalCenter
                }

                AppControls.Label {
                    text: "Filters"
                    color: Theme.AppTheme.textSecondary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.captionSize
                    font.bold: true
                    anchors.verticalCenter: parent.verticalCenter
                }
            }

            MouseArea {
                id: _filterHover
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: root.filterClicked()
            }
        }
    }

    // ── Frozen checkbox column TableView ──────────────────────────────
    // Single-column, N-row TableView for checkboxes.
    // syncView keeps it aligned vertically with _mainView.
    TableView {
        id: _frozenView
        anchors.top:    _header.bottom
        anchors.left:   root.left
        anchors.bottom: _hScrollBar.top
        width:   root.multiSelect ? root._cbColW : 0
        visible: root.multiSelect
        clip:    true

        model:          root._rowCount
        reuseItems:     true
        boundsBehavior: Flickable.StopAtBounds
        interactive:    false  // vertical scroll driven by _mainView via syncView

        syncView:      _mainView
        syncDirection: Qt.Vertical

        rowHeightProvider:   function()    { return Theme.AppTheme.compactRowHeight }
        columnWidthProvider: function()    { return root._cbColW }

        // Redirect wheel events over the frozen area to the main view
        WheelHandler {
            acceptedDevices: PointerDevice.Mouse | PointerDevice.TouchPad
            onWheel: function(event) {
                const dy = event.angleDelta.y
                _mainView.contentY = Math.max(
                    0,
                    Math.min(_mainView.contentY - dy * 0.5,
                             _mainView.contentHeight - _mainView.height)
                )
                event.accepted = true
            }
        }

        delegate: Item {
            id: _cbCell
            required property int row

            readonly property var    _rowData: root.sourceModel ? ({}) : (root._displayRows[row] || {})
            readonly property string _rid: {
                if (root.sourceModel) return root.sourceModel.rowId(row)
                const rawId = _rowData.id
                return String(rawId !== undefined && rawId !== null ? rawId : row)
            }
            readonly property bool _sel: root.selectedRowId === _rid
            readonly property bool _chk: root._isRowChecked(_rid)
            readonly property bool _hi:  _sel || _chk

            implicitWidth:  root._cbColW
            implicitHeight: Theme.AppTheme.compactRowHeight

            // Row background (matches _mainView row colors)
            Rectangle {
                id: _cbCellBackground
                anchors.fill: parent
                color: _cbCell._hi
                    ? Theme.AppTheme.selectedSurface
                    : root._hoveredRow === _cbCell.row
                        ? Theme.AppTheme.hoverSurface
                        : _cbCell.row % 2 !== 0
                            ? Theme.AppTheme.surfaceOverlay : "transparent"

                // Left selection accent bar
                Rectangle {
                    width: 2
                    anchors { top: _cbCellBackground.top; bottom: _cbCellBackground.bottom; left: _cbCellBackground.left }
                    color:   Theme.AppTheme.accent
                    visible: _cbCell._hi
                }
            }

            Item {
                anchors.centerIn: parent
                width: 20; height: 20

                Rectangle {
                    anchors.centerIn: parent
                    width: 14; height: 14; radius: 2
                    color: _cbCell._chk ? Theme.AppTheme.accent : "transparent"
                    border.color: _cbCell._chk
                        ? Theme.AppTheme.accent : Theme.AppTheme.subtleBorder
                    border.width: 1
                    Text {
                        anchors.centerIn: parent
                        text: "✓"; color: "white"
                        font.pixelSize: 9; font.bold: true
                        visible: _cbCell._chk
                    }
                }

                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.rowSelectionToggled(_cbCell._rid, !root._isRowChecked(_cbCell._rid))
                }
            }

            Rectangle {
                anchors { left: _cbCell.left; right: _cbCell.right; bottom: _cbCell.bottom }
                height: 1; color: Theme.AppTheme.divider
            }

            // Hover tracking (HoverHandler does not interfere with AppControls.CheckBox events)
            HoverHandler {
                onHoveredChanged: {
                    if (hovered) root._hoveredRow = _cbCell.row
                    else if (root._hoveredRow === _cbCell.row) root._hoveredRow = -1
                }
            }
        }
    }

    // ── Main 2-D data TableView ───────────────────────────────────────
    // Each delegate = one cell at (row, column).
    TableView {
        id: _mainView
        anchors.top:    _header.bottom
        anchors.left:   _frozenView.right
        anchors.right:  root.right
        anchors.bottom: _hScrollBar.top
        clip:           true
        focus:          true

        model:          root.sourceModel || _tableModel
        reuseItems:     true
        boundsBehavior: Flickable.StopAtBounds

        rowHeightProvider:   function()    { return Theme.AppTheme.compactRowHeight }
        columnWidthProvider: function(col) {
            const c = root._visCols[col]
            return c ? root._colWidth(c) : 0
        }

        onWidthChanged:  root._scheduleMainViewLayout()

        ScrollBar.vertical:   ScrollBar { policy: ScrollBar.AsNeeded }
        ScrollBar.horizontal: _hScrollBar

        // ── Keyboard navigation ───────────────────────────────────────
        Keys.onUpPressed: {
            if (root._currentRow > 0) {
                root._currentRow--
                _mainView.positionViewAtRow(root._currentRow, TableView.Contain)
            }
        }
        Keys.onDownPressed: {
            if (root._currentRow < root._rowCount - 1) {
                root._currentRow++
                _mainView.positionViewAtRow(root._currentRow, TableView.Contain)
            }
        }
        Keys.onReturnPressed: {
            if (root._currentRow >= 0 && root._currentRow < root._rowCount) {
                if (root.sourceModel) {
                    root.rowActivated(root.sourceModel.rowId(root._currentRow))
                } else {
                    const rd = root._displayRows[root._currentRow]
                    if (rd) root.rowActivated(String(rd.id !== undefined ? rd.id : ""))
                }
            }
        }

        // ── Cell delegate ─────────────────────────────────────────────
        delegate: Item {
            id: _cell
            // TableView injects row/column; DynamicTableModel injects the rest.
            required property int    row
            required property int    column
            required property string display     // Qt.DisplayRole — ready-to-show text
            required property var    rawValue    // unformatted cell value
            required property string rowId       // row's id field (or row index as string)
            required property string columnType  // "text" | "status" | "progress"

            readonly property bool _sel: root.selectedRowId === _cell.rowId
            readonly property bool _chk: root.multiSelect && root._isRowChecked(_cell.rowId)
            readonly property bool _hi:  _sel || _chk

            readonly property bool _isSt: _cell.columnType === "status"
            readonly property bool _isPr: _cell.columnType === "progress"

            readonly property real _pVal: {
                if (!_isPr) return 0.0
                const rv = _cell.rawValue
                if (rv === null || rv === undefined || rv === "") return 0.0
                if (typeof rv === "object") return parseFloat(rv.value || 0)
                return parseFloat(rv) || 0.0
            }
            readonly property string _pLbl: {
                if (!_isPr) return ""
                const rv = _cell.rawValue
                return (rv && typeof rv === "object") ? String(rv.label || "") : ""
            }

            implicitHeight: Theme.AppTheme.compactRowHeight

            // ── Cell background ───────────────────────────────────────
            Rectangle {
                id: _cellBackground
                anchors.fill: parent
                color: _cell._hi
                    ? Theme.AppTheme.selectedSurface
                    : root._hoveredRow === _cell.row
                        ? Theme.AppTheme.hoverSurface
                        : _cell.row % 2 !== 0
                            ? Theme.AppTheme.surfaceOverlay : "transparent"

                // Left selection accent bar on the first column only
                Rectangle {
                    visible: _cell.column === 0 && _cell._hi
                    width: 2
                    anchors { top: _cellBackground.top; bottom: _cellBackground.bottom; left: _cellBackground.left }
                    color: Theme.AppTheme.accent
                }
            }

            // ── Status chip ───────────────────────────────────────────
            StatusChip {
                anchors.verticalCenter: _cell.verticalCenter
                anchors.left:           _cell.left
                anchors.leftMargin:     Theme.AppTheme.spacingSm
                visible: _cell._isSt && _cell.display.length > 0
                status:  _cell.display
            }

            // ── Progress bar + label ──────────────────────────────────
            Item {
                id: _progressCell
                anchors.verticalCenter: _cell.verticalCenter
                anchors.left:           _cell.left
                anchors.right:          _cell.right
                anchors.leftMargin:     Theme.AppTheme.spacingSm
                anchors.rightMargin:    Theme.AppTheme.spacingSm
                height:  20
                visible: _cell._isPr

                ProgressBar {
                    anchors.left:           _progressCell.left
                    anchors.right:          _pPct.visible ? _pPct.left : _progressCell.right
                    anchors.rightMargin:    _pPct.visible ? Theme.AppTheme.spacingXs : 0
                    anchors.verticalCenter: _progressCell.verticalCenter
                    value: _cell._pVal
                }

                AppControls.Label {
                    id: _pPct
                    anchors.right:          _progressCell.right
                    anchors.verticalCenter: _progressCell.verticalCenter
                    visible:        _cell._pLbl.length > 0
                    text:           _cell._pLbl
                    color:          Theme.AppTheme.textMuted
                    font.family:    Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.captionSize
                }
            }

            // ── Plain text ────────────────────────────────────────────
            AppControls.Label {
                anchors.fill:        parent
                anchors.leftMargin:  Theme.AppTheme.spacingSm
                anchors.rightMargin: Theme.AppTheme.spacingXs
                visible:             !_cell._isSt && !_cell._isPr
                text:                _cell.display
                verticalAlignment:   Text.AlignVCenter
                color: _cell._hi
                    ? Theme.AppTheme.textPrimary
                    : Theme.AppTheme.textSecondary
                font.family:    Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.smallSize
                elide:          Text.ElideRight
            }

            // ── Cell bottom divider ───────────────────────────────────
            Rectangle {
                anchors { left: _cell.left; right: _cell.right; bottom: _cell.bottom }
                height: 1; color: Theme.AppTheme.divider
            }

            // ── Mouse area: click + double-click ─────────────────────
            MouseArea {
                anchors.fill:  parent
                cursorShape:   Qt.PointingHandCursor
                onClicked: {
                    root._currentRow = _cell.row
                    _mainView.forceActiveFocus()
                    root.rowSelected(_cell.rowId)
                }
                onDoubleClicked: root.rowActivated(_cell.rowId)
            }

            // ── Hover tracking ────────────────────────────────────────
            HoverHandler {
                onHoveredChanged: {
                    if (hovered) root._hoveredRow = _cell.row
                    else if (root._hoveredRow === _cell.row) root._hoveredRow = -1
                }
            }
        }
    }

    // ── Horizontal scrollbar (shared between header + _mainView) ─────
    ScrollBar {
        id: _hScrollBar
        anchors.left:   _frozenView.right
        anchors.right:  root.right
        anchors.bottom: root.bottom
        orientation: Qt.Horizontal
        policy:      ScrollBar.AsNeeded
        height:      12
    }

    // ── Empty state ───────────────────────────────────────────────────
    EmptyState {
        anchors.centerIn: _mainView
        width:   Math.min(_mainView.width, 320)
        visible: root._rowCount === 0 && !root.loading
        title:   root.emptyText
    }

    // ── Loading overlay ───────────────────────────────────────────────
    Item {
        anchors.top:    _header.bottom
        anchors.left:   root.left
        anchors.right:  root.right
        anchors.bottom: _hScrollBar.top
        visible: root.loading
        z: 5

        Rectangle {
            anchors.fill: parent
            color:        Theme.AppTheme.workspaceBackground
            opacity:      0.75
        }

        BusyIndicator {
            anchors.centerIn: parent
            running: root.loading
        }
    }
}

pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Theme 1.0 as Theme
import App.Widgets 1.0 as AppWidgets

// Reusable enterprise data table.
// columns: [{key, label, flex, minWidth, sortable, type, visible}]
// rows:    [{id, ...fieldValues}]
// type values: "text" | "status" | "progress"
//   progress expects rawValue: { value: 0.0-1.0, label: "72%" }
// flex 0 = fixed minWidth; flex > 0 = proportional fill
Item {
    id: root

    property var columns: []
    property var rows: []
    property string selectedRowId: ""
    property string sortKey: ""
    property int sortDirection: Qt.AscendingOrder
    property bool reorderEnabled: true

    property bool multiSelect: false
    property var selectedRowIds: []

    signal rowSelected(string rowId)
    signal rowActivated(string rowId)
    signal sortRequested(string key)
    signal rowSelectionToggled(string rowId, bool selected)
    signal selectAllToggled(bool allSelected)
    signal columnsReordered(var newColumns)

    function _isRowChecked(rowId) {
        const ids = root.selectedRowIds || []
        for (let i = 0; i < ids.length; i++) {
            if (String(ids[i]) === String(rowId)) return true
        }
        return false
    }

    readonly property bool _allChecked: root.rows.length > 0
        && (root.selectedRowIds || []).length >= root.rows.length
    readonly property bool _someChecked: (root.selectedRowIds || []).length > 0 && !root._allChecked

    // Width available for data columns (subtract checkbox column if multiSelect)
    readonly property real _dataWidth: root.multiSelect ? root.width - 36 : root.width

    // Only columns where visible !== false
    readonly property var _visibleColumns: {
        const result = []
        for (let i = 0; i < root.columns.length; i++) {
            if (root.columns[i].visible !== false) result.push(root.columns[i])
        }
        return result
    }

    readonly property real _flexTotal: {
        let total = 0
        for (let i = 0; i < root._visibleColumns.length; i++) {
            const col = root._visibleColumns[i]
            total += (col.flex !== undefined ? col.flex : 1)
        }
        return total > 0 ? total : 1
    }

    function _colWidth(col) {
        const minW = col.minWidth !== undefined ? col.minWidth : 80
        const flex = col.flex !== undefined ? col.flex : 1
        if (flex === 0) return minW
        return Math.max(minW, (root._dataWidth * flex) / root._flexTotal)
    }

    function _applyReorder(fromVisIdx, dropCenterX) {
        if (!root.reorderEnabled) return
        let toVisIdx = fromVisIdx
        let x = root.multiSelect ? 36 : 0
        const vis = root._visibleColumns
        for (let i = 0; i < vis.length; i++) {
            if (dropCenterX <= x + root._colWidth(vis[i]) / 2) { toVisIdx = i; break }
            x += root._colWidth(vis[i])
            toVisIdx = vis.length - 1
        }
        if (fromVisIdx === toVisIdx) return
        function _vToF(vi) {
            let c = -1
            for (let i = 0; i < root.columns.length; i++) {
                if (root.columns[i].visible !== false && ++c === vi) return i
            }
            return root.columns.length - 1
        }
        const newCols = root.columns.slice()
        const moved = newCols.splice(_vToF(fromVisIdx), 1)[0]
        newCols.splice(_vToF(toVisIdx), 0, moved)
        root.columns = newCols
        root.columnsReordered(newCols)
    }

    function _applyColumnVisibility(updatedDraft) {
        const vm = {}
        for (let j = 0; j < updatedDraft.length; j++) vm[updatedDraft[j].key] = updatedDraft[j].visible
        const newCols = []
        for (let i = 0; i < root.columns.length; i++) {
            const c = JSON.parse(JSON.stringify(root.columns[i]))
            if (c.key in vm) c.visible = vm[c.key]
            newCols.push(c)
        }
        root.columns = newCols
    }

    // ── Sticky header ──────────────────────────────────────────────────
    Rectangle {
        id: tableHeader
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        height: 32
        color: Theme.AppTheme.surfaceAlt
        z: 1

        Row {
            anchors.fill: parent

            // Checkbox select-all header
            Item {
                width: 36
                height: 32
                visible: root.multiSelect

                CheckBox {
                    anchors.centerIn: parent
                    checkState: root._allChecked
                        ? Qt.Checked
                        : root._someChecked ? Qt.PartiallyChecked : Qt.Unchecked
                    tristate: true
                    onClicked: root.selectAllToggled(!root._allChecked)
                }
            }

            Repeater {
                model: root._visibleColumns

                delegate: Item {
                    id: headerCell
                    required property var modelData
                    required property int index

                    readonly property bool isSorted: root.sortKey === headerCell.modelData.key
                    property bool _isDragging: false
                    property real _dragOffset: 0

                    width: root._colWidth(headerCell.modelData)
                    height: 32
                    z: headerCell._isDragging ? 5 : 0

                    transform: Translate {
                        x: headerCell._dragOffset
                        Behavior on x {
                            enabled: !headerCell._isDragging
                            NumberAnimation { duration: 120; easing.type: Easing.OutCubic }
                        }
                    }

                    Rectangle {
                        anchors.fill: parent
                        color: Theme.AppTheme.accent
                        opacity: headerCell._isDragging ? 0.12 : 0
                        radius: 2
                    }

                    DragHandler {
                        id: headerDrag
                        enabled: root.reorderEnabled
                        yAxis.enabled: false
                        onActiveChanged: {
                            headerCell._isDragging = active
                            if (!active) {
                                const cx = headerCell.x + headerCell._dragOffset + headerCell.width / 2
                                root._applyReorder(headerCell.index, cx)
                                headerCell._dragOffset = 0
                            }
                        }
                        onTranslationChanged: {
                            if (active) headerCell._dragOffset = translation.x
                        }
                    }

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: Theme.AppTheme.spacingSm
                        anchors.rightMargin: Theme.AppTheme.spacingXs
                        spacing: 3

                        Label {
                            Layout.fillWidth: true
                            text: headerCell.modelData.label || ""
                            color: headerCell.isSorted
                                ? Theme.AppTheme.accent
                                : Theme.AppTheme.textMuted
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.captionSize
                            font.bold: true
                            elide: Text.ElideRight
                        }

                        Text {
                            visible: headerCell.isSorted
                            text: root.sortDirection === Qt.AscendingOrder ? "▲" : "▼"
                            color: Theme.AppTheme.accent
                            font.pixelSize: 7
                        }
                    }

                    MouseArea {
                        anchors.fill: parent
                        enabled: headerCell.modelData.sortable !== false && !headerCell._isDragging
                        cursorShape: headerCell._isDragging
                            ? Qt.ClosedHandCursor
                            : (enabled ? Qt.PointingHandCursor : Qt.ArrowCursor)
                        onClicked: root.sortRequested(headerCell.modelData.key)
                    }
                }
            }
        }

        // Gear icon — opens column visibility customizer
        Item {
            id: customizerArea
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            width: 28
            z: 2
            visible: root.columns.length > 0

            Rectangle {
                anchors.fill: parent
                anchors.topMargin: 5
                anchors.bottomMargin: 5
                anchors.leftMargin: 2
                anchors.rightMargin: 4
                radius: Theme.AppTheme.radiusSm
                color: gearHover.containsMouse ? Theme.AppTheme.hoverSurface : "transparent"
            }

            Text {
                anchors.centerIn: parent
                text: "⚙"
                color: Theme.AppTheme.textMuted
                font.pixelSize: 11
                font.family: Theme.AppTheme.fontFamily
            }

            AppWidgets.TableColumnCustomizer {
                id: columnCustomizer
                parent: customizerArea
                x: -(width - customizerArea.width)
                y: customizerArea.height + 2
                columns: root.columns
                onColumnVisibilityChanged: function(updatedColumns) {
                    root._applyColumnVisibility(updatedColumns)
                }
            }

            MouseArea {
                id: gearHover
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: columnCustomizer.open()
            }
        }
    }

    Rectangle {
        id: headerDivider
        anchors.top: tableHeader.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        height: 1
        color: Theme.AppTheme.border
    }

    // ── Virtualized row list ───────────────────────────────────────────
    ListView {
        id: rowList
        anchors.top: headerDivider.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        clip: true
        model: root.rows
        keyNavigationEnabled: true
        focus: true

        Keys.onUpPressed: {
            if (rowList.currentIndex > 0) rowList.decrementCurrentIndex()
        }
        Keys.onDownPressed: {
            if (rowList.currentIndex < rowList.count - 1) rowList.incrementCurrentIndex()
        }
        Keys.onReturnPressed: {
            if (rowList.currentIndex >= 0) {
                const row = root.rows[rowList.currentIndex]
                if (row) root.rowActivated(String(row.id || ""))
            }
        }

        // Empty state
        AppWidgets.EmptyState {
            anchors.centerIn: parent
            visible: rowList.count === 0
            width: Math.min(rowList.width, 320)
            title: "No records"
        }

        delegate: Item {
            id: rowDelegate
            required property var modelData
            required property int index

            readonly property string rowId: String(rowDelegate.modelData.id || String(rowDelegate.index))
            readonly property bool isSelected: root.selectedRowId === rowDelegate.rowId
            readonly property bool isChecked: root.multiSelect && root._isRowChecked(rowDelegate.rowId)
            readonly property bool isHighlighted: rowDelegate.isSelected || rowDelegate.isChecked

            width: rowList.width
            height: Theme.AppTheme.compactRowHeight

            // Row background
            Rectangle {
                anchors.fill: parent
                color: rowDelegate.isHighlighted
                    ? Theme.AppTheme.selectedSurface
                    : rowHover.containsMouse
                        ? Theme.AppTheme.hoverSurface
                        : rowDelegate.index % 2 !== 0
                            ? Theme.AppTheme.surfaceSunken
                            : "transparent"

                // Accent left rail on selected / checked row
                Rectangle {
                    anchors.left: parent.left
                    anchors.top: parent.top
                    anchors.bottom: parent.bottom
                    width: 2
                    color: Theme.AppTheme.accent
                    visible: rowDelegate.isHighlighted
                }
            }

            // Cells
            Row {
                anchors.fill: parent

                // Per-row checkbox (multiSelect mode)
                Item {
                    width: 36
                    height: Theme.AppTheme.compactRowHeight
                    visible: root.multiSelect

                    CheckBox {
                        anchors.centerIn: parent
                        checked: root._isRowChecked(rowDelegate.rowId)
                        onToggled: root.rowSelectionToggled(rowDelegate.rowId, checked)
                    }
                }

                Repeater {
                    model: root._visibleColumns

                    delegate: Item {
                        id: cellDelegate
                        required property var modelData  // column descriptor
                        required property int index

                        readonly property var rawValue: rowDelegate.modelData[cellDelegate.modelData.key] !== undefined
                            ? rowDelegate.modelData[cellDelegate.modelData.key]
                            : ""
                        readonly property string cellText: cellDelegate.rawValue !== null
                            ? String(cellDelegate.rawValue)
                            : ""
                        readonly property bool isStatusCell: cellDelegate.modelData.type === "status"
                            || cellDelegate.modelData.key === "statusLabel"
                            || cellDelegate.modelData.key === "status"
                            || (cellDelegate.modelData.key !== undefined
                                && cellDelegate.modelData.key.indexOf("StatusLabel") >= 0)
                        readonly property bool isProgressCell: cellDelegate.modelData.type === "progress"

                        readonly property real _progressValue: {
                            if (!cellDelegate.isProgressCell) return 0.0
                            const rv = cellDelegate.rawValue
                            if (rv === null || rv === undefined || rv === "") return 0.0
                            if (typeof rv === "object") return parseFloat(rv.value || 0)
                            return parseFloat(rv) || 0.0
                        }
                        readonly property string _progressLabel: {
                            if (!cellDelegate.isProgressCell) return ""
                            const rv = cellDelegate.rawValue
                            if (rv !== null && rv !== undefined && typeof rv === "object")
                                return String(rv.label || "")
                            return ""
                        }

                        width: root._colWidth(cellDelegate.modelData)
                        height: Theme.AppTheme.compactRowHeight

                        // Status chip cell
                        AppWidgets.StatusChip {
                            anchors.verticalCenter: parent.verticalCenter
                            anchors.left: parent.left
                            anchors.leftMargin: Theme.AppTheme.spacingSm
                            visible: cellDelegate.isStatusCell && cellDelegate.cellText.length > 0
                            status: cellDelegate.cellText
                        }

                        // Progress cell
                        Item {
                            anchors.verticalCenter: parent.verticalCenter
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.leftMargin: Theme.AppTheme.spacingSm
                            anchors.rightMargin: Theme.AppTheme.spacingSm
                            height: 20
                            visible: cellDelegate.isProgressCell

                            AppWidgets.ProgressBar {
                                id: progressFill
                                anchors.left: parent.left
                                anchors.right: progressPct.visible ? progressPct.left : parent.right
                                anchors.rightMargin: progressPct.visible ? Theme.AppTheme.spacingXs : 0
                                anchors.verticalCenter: parent.verticalCenter
                                value: cellDelegate._progressValue
                            }

                            Label {
                                id: progressPct
                                anchors.right: parent.right
                                anchors.verticalCenter: parent.verticalCenter
                                visible: cellDelegate._progressLabel !== ""
                                text: cellDelegate._progressLabel
                                color: Theme.AppTheme.textMuted
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.captionSize
                            }
                        }

                        // Text cell
                        Label {
                            anchors.fill: parent
                            anchors.leftMargin: Theme.AppTheme.spacingSm
                            anchors.rightMargin: Theme.AppTheme.spacingXs
                            visible: !cellDelegate.isStatusCell && !cellDelegate.isProgressCell
                            text: cellDelegate.cellText
                            verticalAlignment: Text.AlignVCenter
                            color: rowDelegate.isHighlighted
                                ? Theme.AppTheme.textPrimary
                                : Theme.AppTheme.textSecondary
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.smallSize
                            elide: Text.ElideRight
                        }
                    }
                }
            }

            // Row divider
            Rectangle {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                height: 1
                color: Theme.AppTheme.divider
            }

            MouseArea {
                id: rowHover
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: {
                    root.selectedRowId = rowDelegate.rowId
                    root.rowSelected(rowDelegate.rowId)
                    rowList.forceActiveFocus()
                    rowList.currentIndex = rowDelegate.index
                }
                onDoubleClicked: root.rowActivated(rowDelegate.rowId)
            }
        }
    }
}

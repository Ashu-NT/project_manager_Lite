pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Theme 1.0 as Theme
import App.Widgets 1.0 as AppWidgets

// Reusable enterprise data table.
// columns: [{key, label, flex, minWidth, sortable, type, visible}]
// rows:    [{id, ...fieldValues}]
// type values: "text" (default) | "status" | "number" | "date"
// flex 0 = fixed minWidth column; flex > 0 = proportional fill
Item {
    id: root

    property var columns: []
    property var rows: []
    property string selectedRowId: ""
    property string sortKey: ""
    property int sortDirection: Qt.AscendingOrder

    property bool multiSelect: false
    property var selectedRowIds: []

    signal rowSelected(string rowId)
    signal rowActivated(string rowId)
    signal sortRequested(string key)
    signal rowSelectionToggled(string rowId, bool selected)
    signal selectAllToggled(bool allSelected)

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

                    width: root._colWidth(headerCell.modelData)
                    height: 32

                    // Column separator
                    Rectangle {
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.bottom: parent.bottom
                        width: 1
                        color: Theme.AppTheme.divider
                        visible: headerCell.index < root._visibleColumns.length - 1
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
                        enabled: headerCell.modelData.sortable !== false
                        cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
                        onClicked: root.sortRequested(headerCell.modelData.key)
                    }
                }
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

                        width: root._colWidth(cellDelegate.modelData)
                        height: Theme.AppTheme.compactRowHeight

                        // Column separator
                        Rectangle {
                            anchors.right: parent.right
                            anchors.top: parent.top
                            anchors.bottom: parent.bottom
                            width: 1
                            color: Theme.AppTheme.divider
                            visible: cellDelegate.index < root._visibleColumns.length - 1
                        }

                        // Status chip cell
                        AppWidgets.StatusChip {
                            anchors.verticalCenter: parent.verticalCenter
                            anchors.left: parent.left
                            anchors.leftMargin: Theme.AppTheme.spacingSm
                            visible: cellDelegate.isStatusCell && cellDelegate.cellText.length > 0
                            status: cellDelegate.cellText
                        }

                        // Text cell
                        Label {
                            anchors.fill: parent
                            anchors.leftMargin: Theme.AppTheme.spacingSm
                            anchors.rightMargin: Theme.AppTheme.spacingXs
                            visible: !cellDelegate.isStatusCell
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

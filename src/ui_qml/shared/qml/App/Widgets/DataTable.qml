pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Theme 1.0 as Theme
import App.Widgets 1.0 as AppWidgets
import App.Icons 1.0 as AppIcons

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
    property bool showFilter: false

    property bool multiSelect: false
    property var selectedRowIds: []

    signal rowSelected(string rowId)
    signal rowActivated(string rowId)
    signal sortRequested(string key)
    signal rowSelectionToggled(string rowId, bool selected)
    signal selectAllToggled(bool allSelected)
    signal filterClicked()
    signal viewDetailRequested(string rowId)

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

    // Fixed-width column reserved for the "Details" action button
    readonly property int _actionColWidth: 68

    // Width available for data columns (subtract checkbox + action columns)
    readonly property real _dataWidth: (root.multiSelect ? root.width - 36 : root.width) - root._actionColWidth

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

    // ── Action bar (Filter / Customize) above column headers ─────────
    Rectangle {
        id: actionBar
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        height: Theme.AppTheme.toolbarHeight - 6
        color: Theme.AppTheme.surfaceRaised

        Rectangle {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            height: 1
            color: Theme.AppTheme.divider
        }

        Row {
            anchors.right: parent.right
            anchors.rightMargin: 8
            anchors.verticalCenter: parent.verticalCenter
            spacing: 2

            // Filter button
            Item {
                id: filterBtn
                visible: root.showFilter
                width: 60
                height: Theme.AppTheme.inputHeight - 8

                Rectangle {
                    anchors.fill: parent
                    radius: Theme.AppTheme.radiusSm
                    color: filterHover.containsMouse
                        ? Theme.AppTheme.hoverSurface
                        : Theme.AppTheme.surfaceOverlay
                }

                Row {
                    anchors.centerIn: parent
                    spacing: 4

                    AppIcons.AppIcon {
                        name: "filter"
                        size: 11
                        iconColor: Theme.AppTheme.textMuted
                        anchors.verticalCenter: parent.verticalCenter
                    }

                    Text {
                        text: "Filter"
                        color: Theme.AppTheme.textMuted
                        font.pixelSize: Theme.AppTheme.captionSize
                        font.family: Theme.AppTheme.fontFamily
                        anchors.verticalCenter: parent.verticalCenter
                    }
                }

                MouseArea {
                    id: filterHover
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.filterClicked()
                }
            }

            Rectangle {
                visible: root.showFilter
                width: 1
                height: 14
                color: Theme.AppTheme.divider
                anchors.verticalCenter: parent.verticalCenter
            }

            // Customize button
            Item {
                id: customizeBtn
                visible: root.columns.length > 0
                width: 84
                height: Theme.AppTheme.inputHeight - 8

                Rectangle {
                    anchors.fill: parent
                    radius: Theme.AppTheme.radiusSm
                    color: custHover.containsMouse
                        ? Theme.AppTheme.hoverSurface
                        : Theme.AppTheme.surfaceOverlay
                }

                Text {
                    anchors.centerIn: parent
                    text: "Customize"
                    color: Theme.AppTheme.textMuted
                    font.pixelSize: Theme.AppTheme.captionSize
                    font.family: Theme.AppTheme.fontFamily
                }

                AppWidgets.TableColumnCustomizer {
                    id: columnCustomizer
                    parent: actionBar
                    x: actionBar.width - width - 4
                    y: actionBar.height + 2
                    columns: root.columns
                    onColumnVisibilityChanged: function(updatedColumns) {
                        root._applyColumnVisibility(updatedColumns)
                    }
                }

                MouseArea {
                    id: custHover
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: columnCustomizer.open()
                }
            }
        }
    }

    // ── Sticky column header ──────────────────────────────────────────
    Rectangle {
        id: tableHeader
        anchors.top: actionBar.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        height: Theme.AppTheme.normalRowHeight
        color: Theme.AppTheme.surfaceAlt
        z: 1

        Row {
            anchors.fill: parent

            // Select-all checkbox header
            Item {
                width: 36
                height: Theme.AppTheme.normalRowHeight
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

            // Column header cells
            Repeater {
                model: root._visibleColumns

                delegate: Item {
                    id: headerCell
                    required property var modelData
                    required property int index

                    readonly property bool isSorted: root.sortKey === headerCell.modelData.key

                    width: root._colWidth(headerCell.modelData)
                    height: Theme.AppTheme.normalRowHeight

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

            // Empty header placeholder for the action column
            Item {
                width: root._actionColWidth
                height: Theme.AppTheme.normalRowHeight
            }
        }
    }

    Rectangle {
        id: headerDivider
        anchors.top: tableHeader.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        height: 1
        color: Theme.AppTheme.divider
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

        ScrollBar.vertical: ScrollBar {
            policy: ScrollBar.AsNeeded
        }

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
                            ? Theme.AppTheme.surfaceOverlay
                            : "transparent"

                Rectangle {
                    anchors.left: parent.left
                    anchors.top: parent.top
                    anchors.bottom: parent.bottom
                    width: 2
                    color: Theme.AppTheme.accent
                    visible: rowDelegate.isHighlighted
                }
            }

            // Data cells row
            Row {
                id: cellRow
                anchors.top: parent.top
                anchors.bottom: parent.bottom
                anchors.left: parent.left

                // Per-row checkbox
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
                        required property var modelData
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

                        AppWidgets.StatusChip {
                            anchors.verticalCenter: parent.verticalCenter
                            anchors.left: parent.left
                            anchors.leftMargin: Theme.AppTheme.spacingSm
                            visible: cellDelegate.isStatusCell && cellDelegate.cellText.length > 0
                            status: cellDelegate.cellText
                        }

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

            // Row hover/click — covers data area only (not the action column)
            MouseArea {
                id: rowHover
                anchors.top: parent.top
                anchors.bottom: parent.bottom
                anchors.left: parent.left
                width: parent.width - root._actionColWidth
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

            // "Details" action button — right-side fixed column
            Item {
                id: actionCell
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.bottom: parent.bottom
                width: root._actionColWidth

                Text {
                    anchors.centerIn: parent
                    text: "Details"
                    font.pixelSize: Theme.AppTheme.smallSize
                    font.family: Theme.AppTheme.fontFamily
                    font.bold: true
                    color: rowHover.containsMouse || rowDelegate.isHighlighted
                        ? Theme.AppTheme.accent
                        : Theme.AppTheme.textMuted
                    opacity: rowHover.containsMouse || rowDelegate.isHighlighted ? 1.0 : 0.40

                    Behavior on opacity {
                        NumberAnimation { duration: 120 }
                    }
                }

                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        root.selectedRowId = rowDelegate.rowId
                        root.rowSelected(rowDelegate.rowId)
                        root.viewDetailRequested(rowDelegate.rowId)
                    }
                }
            }
        }
    }
}

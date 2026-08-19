pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Mock 1.0 as AppMock
import App.Theme 1.0 as Theme

// Phase N: Task Detail -> Dependencies. Answers "what must happen before
// this task, and what tasks depend on this one?" -- the operational
// relationship-management surface for ONE selected task. Whole-project
// network visualization belongs to R4.4 Planning, not here.
Item {
    id: root

    property var    dependenciesModel: AppMock.MockFactory.catalog()
    property bool   isBusy: false
    property bool   canCreate: false
    property string errorText: ""
    property var    dependencyTypeOptions: []
    property var    taskDetail: null
    // Fed back down from the page after previewRequested() -- the typed,
    // non-persisting "what would removing this edge change" preview
    // (Phase K). QML performs zero schedule calculation; this is exactly
    // the same fact set the Remove Dependency confirmation uses.
    property var    dependencyImpactPreview: ({})

    signal createRequested()
    signal editRequested(var dependencyData)
    signal deleteRequested(var dependencyData)
    signal openTaskRequested(string taskId)
    signal selectionChanged(var dependencyData)
    signal previewRequested(string dependencyId)

    readonly property var _items: root.dependenciesModel.items || []
    property int _activeTab: 0
    property string _selectedId: ""

    function _itemForId(dependencyId) {
        const id = String(dependencyId || "")
        if (!id.length) return null
        const list = root._items
        for (let i = 0; i < list.length; i++) {
            if (String(list[i].id || "") === id) return list[i]
        }
        return null
    }
    readonly property var _selectedItem: root._itemForId(root._selectedId)
    readonly property var _selectedState: root._selectedItem ? (root._selectedItem.state || {}) : ({})

    function clearSelection() {
        if (root._selectedId === "") return
        root._selectedId = ""
        root.selectionChanged(null)
    }

    // Phase N14: a task switch (new dependenciesModel identity) must drop
    // selection/inspector/tab state before the new task's rows render --
    // no stale relationship may flash from the previously-selected task.
    onDependenciesModelChanged: {
        root._activeTab = 0
        if (root._selectedId !== "") {
            root._selectedId = ""
            root.selectionChanged(null)
        }
    }

    function openEditSelected() {
        if (root._selectedItem) {
            root.editRequested(root._selectedItem)
        }
    }

    readonly property var _predecessorItems: root._items.filter(function(item) {
        return String((item.state || {}).direction || "") === "PREDECESSOR"
    })
    readonly property var _successorItems: root._items.filter(function(item) {
        return String((item.state || {}).direction || "") === "SUCCESSOR"
    })

    function _lagLeadLabel(lagDays) {
        const n = parseInt(lagDays || "0", 10) || 0
        if (n === 0) return "0d"
        if (n > 0) return "+" + n + "d"
        return Math.abs(n) + "d lead"
    }

    function _toRow(item) {
        const state = item.state || {}
        return {
            "id": item.id,
            "task": String(state.linkedTaskName || item.title || ""),
            "relationship": String(state.dependencyType || "") + " · " + String(state.dependencyTypeLabel || ""),
            "lagLead": root._lagLeadLabel(state.lagDays)
        }
    }
    readonly property var _predecessorRows: root._predecessorItems.map(root._toRow)
    readonly property var _successorRows: root._successorItems.map(root._toRow)

    readonly property var _columns: [
        { key: "task",         label: "Task",         flex: 3, sortable: false },
        { key: "relationship", label: "Relationship", flex: 2, sortable: false },
        { key: "lagLead",      label: "Lag / Lead",   flex: 1, sortable: false, minWidth: 90 }
    ]

    readonly property var _activeRows: root._activeTab === 0 ? root._predecessorRows : root._successorRows
    readonly property int _tableH: {
        const n = root._activeRows.length
        const rH = Theme.AppTheme.compactRowHeight
        const hH = Theme.AppTheme.normalRowHeight
        const natural = hH + Math.max(n, 1) * rH + 12
        return Math.max(140, Math.min(natural, 320))
    }

    readonly property string _currentTaskPeriodLabel: {
        const fields = (root.taskDetail && root.taskDetail.fields) || []
        let start = "", finish = ""
        for (let i = 0; i < fields.length; i++) {
            if (fields[i].label === "Start") start = fields[i].value
            else if (fields[i].label === "Finish") finish = fields[i].value
        }
        if (!start && !finish) return "Not scheduled"
        return start + " – " + finish
    }

    readonly property var _inspectorSections: {
        if (!root._selectedItem) return []
        const s = root._selectedState
        const sections = [
            { "label": "Direction",     "value": String(s.directionLabel || "") },
            { "label": "Relationship",  "value": String(s.dependencyTypeLabel || "") + (s.dependencyType ? " (" + s.dependencyType + ")" : "") },
            { "label": "Lag / Lead",    "value": root._lagLeadLabel(s.lagDays) + " working days" },
            { "label": "Related task dates", "value": String(s.linkedTaskStartLabel || "--") + " – " + String(s.linkedTaskFinishLabel || "--") },
            { "label": "Current task dates", "value": root._currentTaskPeriodLabel }
        ]
        const impact = root.dependencyImpactPreview || {}
        if (impact.available === true && impact.isValid !== false) {
            const risk = String(impact.riskLevel || "none")
            if (risk !== "none" && risk !== "unknown") {
                sections.push({ "label": "Schedule impact if removed", "value": String(impact.summary || "") })
            }
        }
        return sections
    }

    implicitHeight: _col.implicitHeight

    ColumnLayout {
        id: _col
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        spacing: 0

        AppWidgets.InlineMessage {
            Layout.fillWidth: true
            visible: root.errorText.length > 0
            tone: root.errorText.indexOf("Approval required") >= 0 ? "info" : "danger"
            message: root.errorText
        }

        AppWidgets.ContextualActionToolbar {
            Layout.fillWidth: true
            title: "Dependencies"
            subtitle: "Manage the scheduling relationships before and after this task."
            busy: root.isBusy
            createLabel: root.canCreate ? "Add Dependency" : ""
            actions: []
            onCreateRequested: root.createRequested()
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.topMargin: Theme.AppTheme.spacingXs
            Layout.bottomMargin: Theme.AppTheme.spacingSm
            spacing: Theme.AppTheme.spacingLg
            visible: root._items.length > 0

            RowLayout {
                spacing: Theme.AppTheme.spacingXs
                AppControls.Label {
                    text: "Predecessors"
                    color: Theme.AppTheme.textMuted
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                }
                AppControls.Label {
                    text: String(root._predecessorItems.length)
                    color: Theme.AppTheme.textPrimary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                    font.bold: true
                }
            }
            RowLayout {
                spacing: Theme.AppTheme.spacingXs
                AppControls.Label {
                    text: "Successors"
                    color: Theme.AppTheme.textMuted
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                }
                AppControls.Label {
                    text: String(root._successorItems.length)
                    color: Theme.AppTheme.textPrimary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                    font.bold: true
                }
            }
            Item { Layout.fillWidth: true }
        }

        AppWidgets.EmptyState {
            Layout.fillWidth: true
            Layout.topMargin: Theme.AppTheme.spacingLg
            Layout.bottomMargin: Theme.AppTheme.spacingLg
            visible: !root.isBusy && root._items.length === 0
            title: root.dependenciesModel.emptyState || "This task has no scheduling dependencies."
        }

        ColumnLayout {
            Layout.fillWidth: true
            spacing: 0
            visible: root._items.length > 0

            AppWidgets.DetailTabBar {
                Layout.fillWidth: true
                currentIndex: root._activeTab
                tabs: [
                    { "label": "Predecessors (" + root._predecessorItems.length + ")" },
                    { "label": "Successors (" + root._successorItems.length + ")" }
                ]
                onTabSelected: function(index) { root._activeTab = index }
            }

            RowLayout {
                Layout.fillWidth: true

                Item {
                    Layout.fillWidth: true
                    Layout.preferredHeight: root._tableH

                    AppWidgets.EmptyState {
                        anchors.centerIn: parent
                        visible: root._activeRows.length === 0
                        title: root._activeTab === 0
                            ? "No tasks constrain this task from before."
                            : "This task does not constrain any other tasks yet."
                    }

                    AppWidgets.DataTable {
                        anchors.fill: parent
                        visible: root._activeRows.length > 0
                        columns: root._columns
                        rows: root._activeRows
                        selectedRowId: root._selectedId
                        loading: root.isBusy

                        onRowSelected: function(rowId) {
                            root._selectedId = rowId
                            root.selectionChanged(root._itemForId(rowId))
                            if (rowId) root.previewRequested(rowId)
                        }
                        onRowActivated: function(rowId) {
                            root._selectedId = rowId
                            root.selectionChanged(root._itemForId(rowId))
                            if (rowId) root.previewRequested(rowId)
                        }
                    }
                }

                AppWidgets.InspectorPanel {
                    id: _inspector
                    Layout.preferredWidth: Theme.AppTheme.inspectorWidth
                    Layout.fillHeight: true
                    visible: root._selectedItem !== null
                    title: String(root._selectedState.linkedTaskName || "")
                    statusLabel: String(root._selectedState.directionLabel || "")
                    sections: root._inspectorSections
                    showEditAction: false
                    showSecondaryAction: false
                    busy: root.isBusy

                    onCloseRequested: root.clearSelection()

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Theme.AppTheme.spacingXs

                        AppControls.SecondaryButton {
                            Layout.fillWidth: true
                            text: "Edit Relationship"
                            iconName: "edit"
                            enabled: !root.isBusy
                            onClicked: root.editRequested(root._selectedItem)
                        }
                        AppControls.SecondaryButton {
                            Layout.fillWidth: true
                            text: "Open Task"
                            iconName: "open"
                            enabled: !root.isBusy && String(root._selectedState.linkedTaskId || "").length > 0
                            onClicked: root.openTaskRequested(String(root._selectedState.linkedTaskId || ""))
                        }
                        AppControls.SecondaryButton {
                            Layout.fillWidth: true
                            text: "Remove"
                            iconName: "delete"
                            danger: true
                            enabled: !root.isBusy
                            onClicked: root.deleteRequested(root._selectedItem)
                        }
                    }
                }
            }
        }
    }
}

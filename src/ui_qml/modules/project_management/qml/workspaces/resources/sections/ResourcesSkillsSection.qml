pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

Item {
    id: root

    property var workspaceController: null
    property bool hasResource: false
    property bool canManageSkills: false
    property bool isBusy: false
    property real availableHeight: 0
    property string _selectedSkillId: ""

    signal addSkillRequested()
    signal removeSkillRequested(string skillId)
    signal selectionChanged(string skillId)

    function _value(model, index) {
        const item = model[index]
        return item ? String(item.value || "all") : "all"
    }

    function _indexForValue(model, value) {
        const expected = String(value || "all").toLowerCase()
        for (let index = 0; index < model.length; index += 1) {
            if (String(model[index].value || "").toLowerCase() === expected) return index
        }
        return 0
    }

    function clearSelection() {
        if (!root._selectedSkillId.length) return
        root._selectedSkillId = ""
        root.selectionChanged("")
    }

    implicitHeight: Math.max(content.implicitHeight, root.availableHeight)

    ColumnLayout {
        id: content
        width: parent.width
        height: root.implicitHeight
        spacing: Theme.AppTheme.spacingSm

        AppWidgets.ContextualActionToolbar {
            Layout.fillWidth: true
            title: "Skills"
            subtitle: root.workspaceController
                ? String(root.workspaceController.resourceSkillsTotal || 0) : "0"
            busy: root.isBusy
            createLabel: root.hasResource && root.canManageSkills ? "Add Skill" : ""
            actions: []
            onCreateRequested: root.addSkillRequested()
        }

        AppWidgets.TableToolbar {
            Layout.fillWidth: true
            searchText: root.workspaceController
                ? root.workspaceController.resourceSkillsSearch : ""
            searchPlaceholder: "Search skill, code, or notes..."
            showFilter: false
            showRefresh: true
            isBusy: root.isBusy
            onSearchChanged: function(text) {
                if (root.workspaceController) root.workspaceController.setResourceSkillsSearch(text)
            }
            onRefreshRequested: {
                if (root.workspaceController) root.workspaceController.refreshResourceSkills()
            }

            AppControls.ComboBox {
                id: proficiencyFilter
                implicitWidth: 155
                model: [
                    { "value": "all", "label": "All proficiency" },
                    { "value": "beginner", "label": "Beginner" },
                    { "value": "intermediate", "label": "Intermediate" },
                    { "value": "advanced", "label": "Advanced" },
                    { "value": "expert", "label": "Expert" }
                ]
                textRole: "label"
                currentIndex: root._indexForValue(
                    model,
                    root.workspaceController
                        ? root.workspaceController.resourceSkillsProficiency : "all"
                )
                onActivated: function(index) {
                    if (root.workspaceController) {
                        root.workspaceController.setResourceSkillsProficiency(
                            root._value(model, index)
                        )
                    }
                }
            }
        }

        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.minimumHeight: 300

            AppWidgets.DataTable {
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: pagination.top
                columns: [
                    { "key": "skillName", "label": "Skill", "flex": 2, "minWidth": 180, "sortable": true },
                    { "key": "skillCode", "label": "Code", "flex": 1, "minWidth": 105, "sortable": true },
                    { "key": "proficiency", "label": "Proficiency", "flex": 0, "minWidth": 120, "type": "status", "sortable": true },
                    { "key": "notes", "label": "Notes", "flex": 2, "minWidth": 180, "sortable": true }
                ]
                sourceModel: root.workspaceController
                    ? root.workspaceController.resourceSkillsTableModel : null
                sortingMode: "server"
                sortKey: root.workspaceController
                    ? root.workspaceController.resourceSkillsSortKey : "skillName"
                sortDirection: root.workspaceController
                    ? root.workspaceController.resourceSkillsSortDirection : Qt.AscendingOrder
                selectedRowId: root._selectedSkillId
                loading: root.isBusy
                emptyText: root.hasResource
                    ? "No skills match the selected filters."
                    : "Select a resource to view its skills."
                onRowSelected: function(rowId) {
                    root._selectedSkillId = rowId
                    root.selectionChanged(rowId)
                }
                onRowActivated: function(rowId) {
                    root._selectedSkillId = rowId
                    root.selectionChanged(rowId)
                }
                onSortRequested: function(key, direction) {
                    if (root.workspaceController)
                        root.workspaceController.setResourceSkillsSort(key, direction)
                }
            }

            AppWidgets.TablePaginationBar {
                id: pagination
                objectName: "resourceSkillsPagination"
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                currentPage: root.workspaceController
                    ? root.workspaceController.resourceSkillsPage : 1
                pageSize: root.workspaceController
                    ? root.workspaceController.resourceSkillsPageSize : 25
                totalItems: root.workspaceController
                    ? root.workspaceController.resourceSkillsTotal : 0
                busy: root.isBusy
                onPageRequested: function(page) {
                    if (root.workspaceController) root.workspaceController.setResourceSkillsPage(page)
                }
                onPageSizeRequested: function(size) {
                    if (root.workspaceController) root.workspaceController.setResourceSkillsPageSize(size)
                }
            }
        }
    }
}

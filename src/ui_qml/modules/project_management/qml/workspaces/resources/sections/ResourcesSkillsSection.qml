pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import App.Controls 1.0 as AppControls

Item {
    id: root

    property var workspaceController: null
    property bool hasResource: false
    property bool canManageSkills: true
    property bool isBusy: false

    signal addSkillRequested()
    signal removeSkillRequested(string skillId)

    readonly property var _skills: root.workspaceController
        ? (root.workspaceController.resourceSkills || []) : []
    property string _selectedSkillId: ""
    readonly property var _selectedSkill: {
        const sid = root._selectedSkillId
        if (!sid) return null
        const list = root._skills
        for (let i = 0; i < list.length; i++) {
            if (String(list[i].id || "") === sid) return list[i]
        }
        return null
    }
    readonly property int _tableH: {
        const n = root._skills.length
        const rH = Theme.AppTheme.compactRowHeight
        const hH = Theme.AppTheme.normalRowHeight
        return n === 0 ? (hH + 80) : Math.min(hH + n * rH + 12, 300)
    }
    readonly property var _columns: [
        { key: "title",       label: "Skill",       flex: 2,  sortable: false },
        { key: "subtitle",    label: "Code",        flex: 1,  sortable: false },
        { key: "statusLabel", label: "Proficiency", flex: 0,  minWidth: 110, type: "status" },
        { key: "metaText",    label: "Notes",       flex: 2,  sortable: false }
    ]

    implicitHeight: _skillsCol.implicitHeight

    ColumnLayout {
        id: _skillsCol
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        spacing: 0

        AppWidgets.ContextualActionToolbar {
            Layout.fillWidth: true
            visible: !root._selectedSkillId
            title: "Skills"
            subtitle: root._skills.length > 0 ? String(root._skills.length) : ""
            busy: root.isBusy
            createLabel: (root.hasResource && root.canManageSkills) ? "Add Skill" : ""
            actions: []
            onCreateRequested: root.addSkillRequested()
        }

        AppWidgets.ContextualActionToolbar {
            Layout.fillWidth: true
            visible: Boolean(root._selectedSkillId)
            showBack: true
            title: root._selectedSkill ? String(root._selectedSkill.title || "Skill") : "Skill"
            subtitle: root._selectedSkill ? String(root._selectedSkill.statusLabel || "") : ""
            busy: root.isBusy
            actions: [
                { id: "remove", label: "Remove", icon: "delete", enabled: true, danger: true }
            ]
            onBackRequested: root._selectedSkillId = ""
            onActionTriggered: function(actionId) {
                if (actionId === "remove" && root._selectedSkill)
                    root.removeSkillRequested(String(root._selectedSkill.id || ""))
            }
        }

        Item {
            Layout.fillWidth: true
            implicitHeight: root._tableH

            AppWidgets.DataTable {
                anchors.fill: parent
                columns: root._columns
                sourceModel: root.workspaceController ? root.workspaceController.resourceSkillsTableModel : null
                selectedRowId: root._selectedSkillId
                loading: root.isBusy
                emptyText: root.hasResource
                    ? "No skills recorded for this resource."
                    : "Select a resource to view its skills."
                onRowSelected: function(rowId) { root._selectedSkillId = rowId }
                onRowActivated: function(rowId) { root._selectedSkillId = rowId }
            }
        }
    }
}

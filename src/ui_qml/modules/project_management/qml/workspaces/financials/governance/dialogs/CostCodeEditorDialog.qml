pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

AppWidgets.EntityDialog {
    id: root
    objectName: "costCodeEditorDialog"
    property var workspaceController: null
    property string selectedProjectId: ""
    property string mode: "create"
    property var costCode: null
    signal submitted(var payload)
    readonly property bool _editing: root.mode === "edit"
    readonly property var _state: root.costCode ? (root.costCode.state || {}) : ({})
    width: 680
    title: root._editing ? "Edit Cost Code" : "Create Cost Code"
    subtitle: "Organization-owned financial classification; project eligibility is governed separately."
    primaryText: root._editing ? "Save Changes" : "Create Cost Code"
    primaryIcon: root._editing ? "save" : "add"
    primaryEnabled: root.selectedProjectId.length > 0

    function populate() {
        codeField.text = root._editing ? String(root._state.code || root.costCode.title || "") : ""
        nameField.text = root._editing ? String(root._state.name || root.costCode.subtitle || "") : ""
        descriptionField.text = root._editing ? String(root._state.description || "") : ""
        parentSelector.selectedId = root._editing ? String(root._state.parentId || "") : ""
        parentSelector.selectedLabel = root._editing ? String(root._state.parentCode || "None") : "None"
        externalSystemField.text = root._editing ? String(root._state.externalSystem || "") : ""
        externalReferenceField.text = root._editing ? String(root._state.externalReference || "") : ""
        effectiveFromField.text = root._editing ? String(root._state.effectiveFrom || "") : ""
        effectiveToField.text = root._editing ? String(root._state.effectiveTo || "") : ""
        root.errorMessage = ""
        codeField.forceActiveFocus()
    }
    function submitDialog() {
        const code = codeField.text.trim().toUpperCase()
        const name = nameField.text.trim()
        if (!/^[A-Z0-9][A-Z0-9._-]{0,63}$/.test(code)) {
            root.errorMessage = "Cost code must use 1-64 letters, numbers, dots, underscores, or hyphens."
            codeField.forceActiveFocus(); return
        }
        if (!name) { root.errorMessage = "Cost-code name is required."; nameField.forceActiveFocus(); return }
        const system = externalSystemField.text.trim()
        const reference = externalReferenceField.text.trim()
        if (Boolean(system) !== Boolean(reference)) {
            root.errorMessage = "External system and reference must be supplied together."
            if (system) externalReferenceField.forceActiveFocus(); else externalSystemField.forceActiveFocus()
            return
        }
        root.errorMessage = ""
        root.submitted({
            "projectId": root.selectedProjectId, "costCodeId": root.costCode ? String(root.costCode.id || "") : "",
            "version": Number(root._state.version || 0), "code": code, "name": name,
            "description": descriptionField.text.trim(), "parentId": parentSelector.selectedId,
            "externalSystem": system, "externalReference": reference,
            "effectiveFrom": effectiveFromField.text.trim(), "effectiveTo": effectiveToField.text.trim()
        })
    }
    onOpened: root.populate()
    onRejected: root.close()

    GridLayout {
        Layout.fillWidth: true; columns: width >= 540 ? 2 : 1
        columnSpacing: Theme.AppTheme.spacingMd; rowSpacing: Theme.AppTheme.spacingSm
        AppWidgets.FormField { Layout.fillWidth: true; label: "Code"; required: true
            AppControls.TextField { id: codeField; Layout.fillWidth: true; placeholderText: "LABOR.INTERNAL" } }
        AppWidgets.FormField { Layout.fillWidth: true; label: "Name"; required: true
            AppControls.TextField { id: nameField; Layout.fillWidth: true; placeholderText: "Internal labor" } }
        AppWidgets.FormField { Layout.fillWidth: true; label: "Parent code"
            AppControls.SearchablePagedSelector {
                id: parentSelector; Layout.fillWidth: true; allowEmpty: true; emptyLabel: "None"
                searchPlaceholder: "Search active cost codes..."; contextKey: root.selectedProjectId + "|parent"
                onLookupRequested: function(query, page, pageSize, generation, contextKey) {
                    const result = root.workspaceController ? root.workspaceController.searchSetupCostCodes(root.selectedProjectId, query, page, pageSize, "", true) : ({"ok": false, "message": "Setup lookup unavailable."})
                    parentSelector.acceptResult(result, generation, contextKey)
                }
            } }
        AppWidgets.FormField { Layout.fillWidth: true; label: "Effective from"
            AppControls.DateField { id: effectiveFromField; Layout.fillWidth: true } }
        AppWidgets.FormField { Layout.fillWidth: true; label: "Effective to"
            AppControls.DateField { id: effectiveToField; Layout.fillWidth: true } }
        AppWidgets.FormField { Layout.fillWidth: true; label: "External system"
            AppControls.TextField { id: externalSystemField; Layout.fillWidth: true } }
        AppWidgets.FormField { Layout.fillWidth: true; label: "External reference"
            AppControls.TextField { id: externalReferenceField; Layout.fillWidth: true } }
        AppWidgets.FormField { Layout.fillWidth: true; Layout.columnSpan: parent.columns; label: "Description"
            AppControls.TextArea { id: descriptionField; Layout.fillWidth: true; Layout.preferredHeight: 88; wrapMode: TextEdit.WordWrap } }
    }
}

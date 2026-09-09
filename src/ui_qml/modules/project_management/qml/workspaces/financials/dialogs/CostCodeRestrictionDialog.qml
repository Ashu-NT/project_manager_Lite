import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets

AppWidgets.EntityDialog {
    id: root
    property var workspaceController: null
    property string projectId: ""
    signal submitted(var payload)
    width: 560; title: "Add Cost Code to Project Allow-list"
    subtitle: "Choose an active organization cost code not already assigned to this project."
    primaryText: "Add to Allow-list"; primaryIcon: "add"
    function submitDialog() { if (!selector.selectedId) { root.errorMessage="Select a cost code."; selector.forceActiveFocus(); return }; root.errorMessage=""; root.submitted({"projectId":root.projectId,"costCodeId":selector.selectedId}) }
    onOpened: { selector.clearSelection(); root.errorMessage=""; selector.forceActiveFocus() }
    onRejected: root.close()
    AppWidgets.FormField { Layout.fillWidth:true; label:"Cost code"; required:true
        AppControls.SearchablePagedSelector { id:selector; Layout.fillWidth:true; searchPlaceholder:"Search unassigned active cost codes..."; contextKey:root.projectId+"|unassigned"
            onLookupRequested:function(query,page,pageSize,generation,contextKey) { const result=root.workspaceController?root.workspaceController.searchSetupCostCodes(root.projectId,query,page,pageSize,"unassigned",true):({"ok":false,"message":"Setup lookup unavailable."}); selector.acceptResult(result,generation,contextKey) } } }
}

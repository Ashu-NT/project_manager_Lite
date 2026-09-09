pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

AppWidgets.EntityDialog {
    id: root
    property var workspaceController: null
    property string projectId: ""
    property var profile: null
    signal submitted(var payload)
    readonly property var _state: root.profile ? (root.profile.state || {}) : ({})
    readonly property var _currencies: root.workspaceController ? (root.workspaceController.currencyOptions || []) : []
    readonly property var _billingMethods: [{"value":"non_billable","label":"Non-billable"},{"value":"time_and_materials","label":"Time and materials"},{"value":"fixed_price","label":"Fixed price"},{"value":"cost_plus","label":"Cost plus"}]
    readonly property var _controlModes: [{"value":"none","label":"No enforcement"},{"value":"warn","label":"Warn"},{"value":"block","label":"Block"}]
    readonly property var _policies: [{"value":"all_active","label":"All active codes"},{"value":"restricted","label":"Project allow-list"}]
    width: 700
    title: "Edit Financial Setup"
    subtitle: "Update project currency, billing, period, and financial-control policy."
    primaryText: "Save Changes"; primaryIcon: "save"
    function _index(model, value) { for (let i=0;i<model.length;i++) if (String(model[i].value)===String(value||"")) return i; return 0 }
    function populate() {
        currencyCombo.currentIndex=root._index(root._currencies,root._state.currency)
        billingCombo.currentIndex=root._index(root._billingMethods,root._state.billingMethod)
        controlCombo.currentIndex=root._index(root._controlModes,root._state.budgetControlMode)
        policyCombo.currentIndex=root._index(root._policies,root._state.costCodePolicy)
        fundedCheck.checked=Boolean(root._state.isFunded); billableCheck.checked=Boolean(root._state.isBillable)
        startField.text=String(root._state.financialStartDate||""); endField.text=String(root._state.financialEndDate||"")
        defaultSelector.selectedId=String(root._state.defaultCostCodeId||""); defaultSelector.selectedLabel=String(root._state.defaultCostCodeLabel||"None")
        root.errorMessage=""; currencyCombo.forceActiveFocus()
    }
    function submitDialog() {
        const currency=root._currencies[currencyCombo.currentIndex], billing=root._billingMethods[billingCombo.currentIndex]
        const control=root._controlModes[controlCombo.currentIndex], policy=root._policies[policyCombo.currentIndex]
        if (!currency) { root.errorMessage="Currency is required."; currencyCombo.forceActiveFocus(); return }
        if (billableCheck.checked && billing.value==="non_billable") { root.errorMessage="Select a billing method for a billable project."; billingCombo.forceActiveFocus(); return }
        if (!billableCheck.checked && billing.value!=="non_billable") { root.errorMessage="A non-billable project must use the Non-billable method."; billingCombo.forceActiveFocus(); return }
        root.errorMessage=""
        root.submitted({"projectId":root.projectId,"version":Number(root._state.version||0),"currency":String(currency.value),"billingMethod":String(billing.value),"budgetControlMode":String(control.value),"costCodePolicy":String(policy.value),"financialStartDate":startField.text.trim(),"financialEndDate":endField.text.trim(),"isFunded":fundedCheck.checked,"isBillable":billableCheck.checked,"defaultCostCodeId":defaultSelector.selectedId})
    }
    onOpened: root.populate()
    onRejected: root.close()
    GridLayout {
        Layout.fillWidth: true; columns: width>=560 ? 2 : 1; columnSpacing: Theme.AppTheme.spacingMd; rowSpacing: Theme.AppTheme.spacingSm
        AppWidgets.FormField { Layout.fillWidth:true; label:"Currency"; required:true; AppControls.ComboBox { id:currencyCombo; Layout.fillWidth:true; model:root._currencies; textRole:"label" } }
        AppWidgets.FormField { Layout.fillWidth:true; label:"Billing method"; required:true; AppControls.ComboBox { id:billingCombo; Layout.fillWidth:true; model:root._billingMethods; textRole:"label" } }
        AppWidgets.FormField { Layout.fillWidth:true; label:"Budget control"; required:true; AppControls.ComboBox { id:controlCombo; Layout.fillWidth:true; model:root._controlModes; textRole:"label" } }
        AppWidgets.FormField { Layout.fillWidth:true; label:"Cost-code policy"; required:true; AppControls.ComboBox { id:policyCombo; Layout.fillWidth:true; model:root._policies; textRole:"label" } }
        AppWidgets.FormField { Layout.fillWidth:true; label:"Financial start"; AppControls.DateField { id:startField; Layout.fillWidth:true } }
        AppWidgets.FormField { Layout.fillWidth:true; label:"Financial end"; AppControls.DateField { id:endField; Layout.fillWidth:true } }
        AppWidgets.FormField { Layout.fillWidth:true; Layout.columnSpan:parent.columns; label:"Default cost code"
            AppControls.SearchablePagedSelector { id:defaultSelector; Layout.fillWidth:true; allowEmpty:true; emptyLabel:"None"; searchPlaceholder:"Search eligible active cost codes..."; contextKey:root.projectId+"|"+String(root._policies[policyCombo.currentIndex].value||"")
                onLookupRequested:function(query,page,pageSize,generation,contextKey) { const assignment=root._policies[policyCombo.currentIndex].value==="restricted"?"assigned":""; const result=root.workspaceController?root.workspaceController.searchSetupCostCodes(root.projectId,query,page,pageSize,assignment,true):({"ok":false,"message":"Setup lookup unavailable."}); defaultSelector.acceptResult(result,generation,contextKey) } } }
        AppControls.CheckBox { id:fundedCheck; Layout.fillWidth:true; text:"Funded project" }
        AppControls.CheckBox { id:billableCheck; Layout.fillWidth:true; text:"Billable project" }
    }
}

pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

Item {
    id: root
    property var profile: ({"id":"","fields":[],"state":{}})
    property var costCodes: ({"items":[]})
    property var restrictions: ({"items":[]})
    property var costCodesTableModel: null
    property var restrictionsTableModel: null
    property bool canManageRestrictions: false
    property bool busy: false
    property string costCodeSortKey: "code"
    property int costCodeSortDirection: Qt.AscendingOrder
    property string restrictionSortKey: "code"
    property int restrictionSortDirection: Qt.AscendingOrder
    property string costCodeSearch: ""
    property string costCodeStatus: ""
    property string costCodeAssignment: ""
    property string restrictionSearch: ""
    property string selectedCostCodeId: ""
    property string selectedRestrictionId: ""
    readonly property var profileState: root.profile ? (root.profile.state || {}) : ({})
    readonly property bool restrictedPolicy: String(root.profileState.costCodePolicy || "") === "restricted"
    readonly property var selectedCostCode: root._find(root.costCodes.items || [], root.selectedCostCodeId)
    readonly property var selectedRestriction: root._find(root.restrictions.items || [], root.selectedRestrictionId)
    readonly property var _fields: root.profile.fields || []
    readonly property var _statuses: [{"value":"","label":"All statuses"},{"value":"active","label":"Active"},{"value":"inactive","label":"Inactive"}]
    readonly property var _assignments: [{"value":"","label":"Any availability"},{"value":"assigned","label":"On allow-list"},{"value":"unassigned","label":"Not on allow-list"}]

    signal profileEditRequested(var profile)
    signal profileTransitionRequested(string action, var profile)
    signal costCodeEditRequested(var costCode)
    signal costCodeStatusRequested(string action, var costCode)
    signal restrictionAddRequested()
    signal restrictionRemoveRequested(var restriction)
    signal costCodePageRequested(int page)
    signal restrictionPageRequested(int page)
    signal costCodeSortRequested(string key, int direction)
    signal restrictionSortRequested(string key, int direction)
    signal costCodeFiltersRequested(string search, string status, string assignment)
    signal restrictionFilterRequested(string search)

    function _find(rows, id) { for (let i=0;i<rows.length;i++) if (String(rows[i].id||"")===String(id||"")) return rows[i]; return null }
    function _index(model, value) { for (let i=0;i<model.length;i++) if (String(model[i].value)===String(value||"")) return i; return 0 }
    function _emitCostCodeFilters(search) { const s=root._statuses[statusFilter.currentIndex]||root._statuses[0]; const a=root._assignments[assignmentFilter.currentIndex]||root._assignments[0]; root.costCodeFiltersRequested(search,String(s.value),String(a.value)) }

    implicitHeight: column.implicitHeight
    ColumnLayout {
        id: column; width: parent.width; spacing: Theme.AppTheme.spacingMd
        AppWidgets.SectionHeading { Layout.fillWidth:true; label:"Financial Profile" }
        AppWidgets.EmptyState { Layout.fillWidth:true; visible:String(root.profile.id||"").length===0; title:"No project selected"; message:root.profile.emptyState||"Select a project to review Financial Setup." }
        Flow {
            Layout.fillWidth:true; visible:String(root.profile.id||"").length>0; spacing:Theme.AppTheme.spacingSm
            leftPadding:Theme.AppTheme.spacingMd; rightPadding:Theme.AppTheme.spacingMd
            AppControls.SecondaryButton { visible:Boolean(root.profileState.canEdit); enabled:!root.busy; text:"Edit Setup"; iconName:"edit"; onClicked:root.profileEditRequested(root.profile) }
            AppControls.SecondaryButton { visible:Boolean(root.profileState.canTransition)&&String(root.profileState.status)==="draft"; enabled:!root.busy; text:"Activate"; iconName:"approve"; onClicked:root.profileTransitionRequested("profile_active",root.profile) }
            AppControls.SecondaryButton { visible:Boolean(root.profileState.canTransition)&&String(root.profileState.status)==="active"; enabled:!root.busy; text:"Put On Hold"; iconName:"pause"; onClicked:root.profileTransitionRequested("profile_on_hold",root.profile) }
            AppControls.SecondaryButton { visible:Boolean(root.profileState.canTransition)&&String(root.profileState.status)==="on_hold"; enabled:!root.busy; text:"Reactivate"; iconName:"approve"; onClicked:root.profileTransitionRequested("profile_active",root.profile) }
            AppControls.SecondaryButton { visible:Boolean(root.profileState.canTransition)&&(String(root.profileState.status)==="active"||String(root.profileState.status)==="on_hold"); enabled:!root.busy; text:"Close Profile"; iconName:"close"; danger:true; onClicked:root.profileTransitionRequested("profile_closed",root.profile) }
        }
        AppWidgets.SectionCard {
            Layout.fillWidth:true; visible:String(root.profile.id||"").length>0; title:root.profile.statusLabel||"Profile"
            GridLayout {
                width:parent?parent.width:0; columns:width>=900?3:(width>=560?2:1); columnSpacing:Theme.AppTheme.spacingLg; rowSpacing:Theme.AppTheme.spacingMd
                Repeater { model:root._fields; delegate:ColumnLayout { required property var modelData; Layout.fillWidth:true; Layout.margins:Theme.AppTheme.spacingMd; spacing:Theme.AppTheme.spacingXs
                    AppControls.Label { Layout.fillWidth:true; text:String(parent.modelData.label||""); color:Theme.AppTheme.textMuted; font.pixelSize:Theme.AppTheme.captionSize }
                    AppControls.Label { Layout.fillWidth:true; text:String(parent.modelData.value||"-"); font.bold:true; wrapMode:Text.WordWrap }
                } }
            }
        }

        AppWidgets.SectionHeading { Layout.fillWidth:true; label:"Cost Codes" }
        Flow { Layout.fillWidth:true; spacing:Theme.AppTheme.spacingSm; leftPadding:Theme.AppTheme.spacingMd; rightPadding:Theme.AppTheme.spacingMd
            AppControls.SecondaryButton { visible:Boolean(root.selectedCostCode&&root.selectedCostCode.state&&root.selectedCostCode.state.canEdit); enabled:!root.busy; text:"Edit"; iconName:"edit"; onClicked:root.costCodeEditRequested(root.selectedCostCode) }
            AppControls.SecondaryButton { visible:Boolean(root.selectedCostCode&&root.selectedCostCode.state&&root.selectedCostCode.state.canChangeStatus); enabled:!root.busy; text:root.selectedCostCode&&root.selectedCostCode.state&&root.selectedCostCode.state.isActive?"Deactivate":"Activate"; iconName:root.selectedCostCode&&root.selectedCostCode.state&&root.selectedCostCode.state.isActive?"pause":"approve"; onClicked:root.costCodeStatusRequested(root.selectedCostCode.state.isActive?"deactivate_cost_code":"activate_cost_code",root.selectedCostCode) }
            AppControls.SecondaryButton { visible:Boolean(root.selectedCostCode&&root.selectedCostCode.state&&root.selectedCostCode.state.canAddRestriction); enabled:!root.busy; text:"Add to Allow-list"; iconName:"add"; onClicked:root.restrictionAddRequested() }
        }
        AppWidgets.TableToolbar { Layout.fillWidth:true; searchText:root.costCodeSearch; searchPlaceholder:"Search code, name, or description..."; showFilter:false; showRefresh:false; isBusy:root.busy
            onSearchChanged:function(text){root._emitCostCodeFilters(text)}
            AppControls.ComboBox { id:statusFilter; implicitWidth:145; model:root._statuses; textRole:"label"; currentIndex:root._index(root._statuses,root.costCodeStatus); onActivated:root._emitCostCodeFilters(root.costCodeSearch) }
            AppControls.ComboBox { id:assignmentFilter; implicitWidth:165; model:root._assignments; textRole:"label"; currentIndex:root._index(root._assignments,root.costCodeAssignment); onActivated:root._emitCostCodeFilters(root.costCodeSearch) }
        }
        AppWidgets.EmptyState { Layout.fillWidth:true; visible:(root.costCodes.items||[]).length===0; title:"No Cost Codes"; message:root.costCodes.emptyState||"No cost codes match the current filters." }
        Item { Layout.fillWidth:true; Layout.preferredHeight:280; visible:(root.costCodes.items||[]).length>0
            AppWidgets.DataTable { anchors.fill:parent; objectName:"financialSetupCostCodesTable"; sourceModel:root.costCodesTableModel; sortingMode:"server"; sortKey:root.costCodeSortKey; sortDirection:root.costCodeSortDirection; selectedRowId:root.selectedCostCodeId; loading:root.busy
                columns:[{"key":"title","label":"Code","flex":1.0,"sortable":true},{"key":"subtitle","label":"Name","flex":1.6,"sortable":true},{"key":"statusLabel","label":"Status","minWidth":100,"flex":0,"sortable":true},{"key":"supportingText","label":"Parent","flex":1.0,"sortable":true},{"key":"metaText","label":"Effective period","flex":1.3,"sortable":true}]
                onRowSelected:function(id){root.selectedCostCodeId=String(id||"")}; onSortRequested:function(key,direction){root.costCodeSortRequested(key,direction)}
            } }
        AppWidgets.TablePaginationBar { Layout.fillWidth:true; visible:Number(root.costCodes.total||0)>Number(root.costCodes.pageSize||50); currentPage:Number(root.costCodes.page||1); pageSize:Number(root.costCodes.pageSize||50); totalItems:Number(root.costCodes.total||0); busy:root.busy; onPageRequested:function(page){root.costCodePageRequested(page)} }

        AppWidgets.SectionHeading { Layout.fillWidth:true; label:"Project Cost-Code Allow-list" }
        AppWidgets.InlineMessage { Layout.fillWidth:true; visible:!root.restrictedPolicy; tone:"info"; message:"The All Active Codes policy is selected. Switch to Project Allow-list to govern explicit project eligibility." }
        Flow { Layout.fillWidth:true; visible:root.restrictedPolicy; spacing:Theme.AppTheme.spacingSm; leftPadding:Theme.AppTheme.spacingMd; rightPadding:Theme.AppTheme.spacingMd
            AppControls.SecondaryButton { visible:root.canManageRestrictions; enabled:!root.busy; text:"Add Cost Code"; iconName:"add"; onClicked:root.restrictionAddRequested() }
            AppControls.SecondaryButton { visible:Boolean(root.selectedRestriction&&root.selectedRestriction.state&&root.selectedRestriction.state.canRemove); enabled:!root.busy; text:"Remove"; iconName:"delete"; danger:true; onClicked:root.restrictionRemoveRequested(root.selectedRestriction) }
        }
        AppWidgets.TableToolbar { Layout.fillWidth:true; visible:root.restrictedPolicy; searchText:root.restrictionSearch; searchPlaceholder:"Search allowed cost code..."; showFilter:false; showRefresh:false; isBusy:root.busy; onSearchChanged:function(text){root.restrictionFilterRequested(text)} }
        AppWidgets.EmptyState { Layout.fillWidth:true; visible:root.restrictedPolicy&&(root.restrictions.items||[]).length===0; title:"No Allow-list Entries"; message:root.restrictions.emptyState||"No cost codes are explicitly available to this project." }
        Item { Layout.fillWidth:true; Layout.preferredHeight:240; visible:root.restrictedPolicy&&(root.restrictions.items||[]).length>0
            AppWidgets.DataTable { anchors.fill:parent; objectName:"financialSetupRestrictionsTable"; sourceModel:root.restrictionsTableModel; sortingMode:"server"; sortKey:root.restrictionSortKey; sortDirection:root.restrictionSortDirection; selectedRowId:root.selectedRestrictionId; loading:root.busy
                columns:[{"key":"title","label":"Code","flex":1.0,"sortable":true},{"key":"subtitle","label":"Name","flex":1.6,"sortable":true},{"key":"statusLabel","label":"Status","minWidth":100,"flex":0,"sortable":true},{"key":"supportingText","label":"Usage","flex":1.2,"sortable":false},{"key":"metaText","label":"Added","flex":1.2,"sortable":true}]
                onRowSelected:function(id){root.selectedRestrictionId=String(id||"")}; onSortRequested:function(key,direction){root.restrictionSortRequested(key,direction)}
            } }
        AppWidgets.TablePaginationBar { Layout.fillWidth:true; visible:root.restrictedPolicy&&Number(root.restrictions.total||0)>Number(root.restrictions.pageSize||50); currentPage:Number(root.restrictions.page||1); pageSize:Number(root.restrictions.pageSize||50); totalItems:Number(root.restrictions.total||0); busy:root.busy; onPageRequested:function(page){root.restrictionPageRequested(page)} }
    }
}

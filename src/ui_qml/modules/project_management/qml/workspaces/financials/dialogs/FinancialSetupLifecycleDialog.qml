import QtQuick
import App.Widgets 1.0 as AppWidgets

AppWidgets.EntityDialog {
    id: root
    property string action: ""
    property string projectId: ""
    property var profile: null
    property var costCode: null
    property var restriction: null
    signal decided(var payload)
    readonly property var _profileState: root.profile ? (root.profile.state || {}) : ({})
    readonly property var _costCodeState: root.costCode ? (root.costCode.state || {}) : ({})
    readonly property bool _profileAction: root.action.indexOf("profile_") === 0
    readonly property bool _removeRestriction: root.action === "remove_restriction"
    readonly property bool _activate: root.action === "activate_cost_code"
    width: 520
    title: root._profileAction ? "Change Financial Profile Status" : root._removeRestriction ? "Remove Cost Code from Allow-list" : (root._activate ? "Activate Cost Code" : "Deactivate Cost Code")
    subtitle: root._profileAction ? "The server validates the requested lifecycle transition." : root._removeRestriction ? "This changes future project eligibility and does not rewrite financial history." : "Status changes affect future selection only and preserve historical references."
    primaryText: root._removeRestriction ? "Remove" : root._activate ? "Activate" : root._profileAction ? "Change Status" : "Deactivate"
    primaryIcon: root._removeRestriction || (!root._activate && !root._profileAction) ? "delete" : "approve"
    function submitDialog() {
        let payload={"projectId":root.projectId}
        if (root._profileAction) { payload.version=Number(root._profileState.version||0); payload.targetStatus=root.action.substring(8) }
        else if (root._removeRestriction) payload.costCodeId=String(root.restriction&&root.restriction.state?root.restriction.state.costCodeId||"":"")
        else { payload.costCodeId=String(root.costCode?root.costCode.id||"":""); payload.version=Number(root._costCodeState.version||0); payload.activate=root._activate }
        root.decided(payload)
    }
    onOpened: root.errorMessage=""
    onRejected: root.close()
}

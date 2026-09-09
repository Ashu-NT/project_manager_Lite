import QtQuick
import App.Widgets 1.0 as AppWidgets

AppWidgets.EntityDialog {
    id: root
    objectName: "rateLifecycleDialog"
    property string target: "card"
    property var rateCard: null
    property var rateLine: null
    signal decided(var payload)
    readonly property var _cardState: root.rateCard ? (root.rateCard.state || {}) : ({})
    readonly property var _lineState: root.rateLine ? (root.rateLine.state || {}) : ({})
    width: 520
    title: root.target === "line" ? "Deactivate Rate Line" : "Deactivate Rate Card"
    subtitle: root.target === "line"
        ? "This stops future resolution while preserving posted financial history."
        : "This closes the Rate Card for future use. Existing snapshots remain unchanged."
    primaryText: "Deactivate"
    primaryIcon: "delete"
    primaryEnabled: !root.busy
    function submitDialog() {
        root.decided({
            "rateCardId": String(root.rateCard ? root.rateCard.id || "" : ""),
            "cardVersion": Number(root._cardState.version || 0),
            "rateLineId": String(root.rateLine ? root.rateLine.id || "" : ""),
            "version": Number(root.target === "line" ? root._lineState.version || 0 : root._cardState.version || 0)
        })
    }
    onOpened: root.errorMessage = ""
    onRejected: root.close()
}

pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

AppWidgets.EntityDialog {
    id: root
    objectName: "rateLineEditorDialog"
    property var workspaceController: null
    property string mode: "create"
    property string projectId: ""
    property var rateCard: null
    property var rateLine: null
    signal submitted(var payload)
    readonly property bool _editing: root.mode === "edit"
    readonly property var _cardState: root.rateCard ? (root.rateCard.state || {}) : ({})
    readonly property var _lineState: root.rateLine ? (root.rateLine.state || {}) : ({})
    readonly property bool _historical: Boolean(root._lineState.isConsumed)
    readonly property var _selectorKinds: [
        { "value": "resource", "label": "Resource" },
        { "value": "role", "label": "Role" },
        { "value": "skill", "label": "Skill" },
        { "value": "department", "label": "Department" }
    ]
    readonly property var _rateTypes: [
        { "value": "cost", "label": "Cost" },
        { "value": "billing", "label": "Billing" }
    ]
    readonly property var _units: [
        { "value": "HOUR", "label": "Hour" },
        { "value": "DAY", "label": "Day" },
        { "value": "ITEM", "label": "Item" }
    ]
    width: 760
    title: root._editing ? "Edit Rate Line" : "Add Rate Line"
    subtitle: root._historical
        ? "Historical use locks economic terms. Only a future end date may be changed."
        : "Define one effective-dated selector and its authoritative financial rate."
    primaryText: root._editing ? "Save Changes" : "Add Rate Line"
    primaryIcon: root._editing ? "save" : "add"
    primaryEnabled: !root.busy && root.projectId.length > 0

    function _indexOf(model, value) {
        for (let i = 0; i < model.length; i += 1)
            if (String(model[i].value) === String(value || "")) return i
        return 0
    }
    function _selectorKind() {
        const item = root._selectorKinds[selectorKind.currentIndex]
        return item ? String(item.value) : "resource"
    }
    function _optionalNumber(field, label) {
        const value = field.text.trim()
        if (!value) return ""
        if (!/^\d+(\.\d+)?$/.test(value)) {
            root.errorMessage = label + " must be a non-negative decimal."
            field.forceActiveFocus()
            return null
        }
        return value
    }
    function submitDialog() {
        const amount = amountField.text.trim()
        if (!/^\d+(\.\d+)?$/.test(amount)) {
            root.errorMessage = "Rate amount must be a non-negative decimal."
            amountField.forceActiveFocus(); return
        }
        const kind = root._selectorKind()
        let selectorValue = ""
        if (kind === "resource") selectorValue = resourceSelector.selectedId
        else if (kind === "department") selectorValue = departmentSelector.selectedId
        else selectorValue = dimensionField.text.trim()
        if (!selectorValue) {
            root.errorMessage = "Select or enter the Rate Line dimension."
            return
        }
        const overtime = root._optionalNumber(overtimeField, "Overtime multiplier")
        if (overtime === null) return
        const weekend = root._optionalNumber(weekendField, "Weekend multiplier")
        if (weekend === null) return
        const holiday = root._optionalNumber(holidayField, "Holiday multiplier")
        if (holiday === null) return
        const fromDate = effectiveFromField.text.trim()
        const toDate = effectiveToField.text.trim()
        if (fromDate && toDate && toDate < fromDate) {
            root.errorMessage = "Effective to cannot be earlier than effective from."
            effectiveToField.forceActiveFocus(); return
        }
        const typeItem = root._rateTypes[rateType.currentIndex]
        const unitItem = root._units[unitCombo.currentIndex]
        const currencyItem = currencyCombo.model[currencyCombo.currentIndex]
        root.errorMessage = ""
        root.submitted({
            "rateCardId": String(root.rateCard ? root.rateCard.id || "" : ""),
            "cardVersion": Number(root._cardState.version || 0),
            "rateLineId": String(root.rateLine ? root.rateLine.id || "" : ""),
            "version": Number(root._lineState.version || 0),
            "rateType": typeItem ? String(typeItem.value) : "cost",
            "unit": unitItem ? String(unitItem.value) : "HOUR",
            "amount": amount,
            "currency": currencyItem ? String(currencyItem.value || currencyItem.code || "") : "",
            "resourceId": kind === "resource" ? selectorValue : "",
            "role": kind === "role" ? selectorValue : "",
            "skillCode": kind === "skill" ? selectorValue : "",
            "departmentId": kind === "department" ? selectorValue : "",
            "effectiveFrom": fromDate,
            "effectiveTo": toDate,
            "overtimeMultiplier": overtime,
            "weekendMultiplier": weekend,
            "holidayMultiplier": holiday
        })
    }
    function populate() {
        const kind = String(root._lineState.selectorKind || "resource")
        selectorKind.currentIndex = root._indexOf(root._selectorKinds, kind)
        rateType.currentIndex = root._indexOf(root._rateTypes, root._lineState.rateType || "cost")
        unitCombo.currentIndex = root._indexOf(root._units, root._lineState.unit || "HOUR")
        currencyCombo.currentIndex = root._indexOf(currencyCombo.model, root._lineState.currency || (root.workspaceController ? root.workspaceController.defaultCurrencyCode : "XAF"))
        resourceSelector.selectedId = String(root._lineState.resourceId || "")
        resourceSelector.selectedLabel = String(root._lineState.resourceName || root._lineState.resourceCode || "")
        departmentSelector.selectedId = String(root._lineState.departmentId || "")
        departmentSelector.selectedLabel = String(root._lineState.departmentName || "")
        dimensionField.text = kind === "role" ? String(root._lineState.role || "") : String(root._lineState.skillCode || "")
        amountField.text = root._editing ? String(root._lineState.amount || "") : ""
        effectiveFromField.text = String(root._lineState.effectiveFrom || "")
        effectiveToField.text = String(root._lineState.effectiveTo || "")
        overtimeField.text = String(root._lineState.overtimeMultiplier || "")
        weekendField.text = String(root._lineState.weekendMultiplier || "")
        holidayField.text = String(root._lineState.holidayMultiplier || "")
        root.errorMessage = ""
    }
    onOpened: root.populate()
    onRejected: root.close()

    GridLayout {
        Layout.fillWidth: true
        columns: width >= 620 ? 2 : 1
        columnSpacing: Theme.AppTheme.spacingMd
        rowSpacing: Theme.AppTheme.spacingSm

        AppWidgets.FormField { Layout.fillWidth: true; label: "Applies by"; required: true
            AppControls.ComboBox { id: selectorKind; Layout.fillWidth: true; model: root._selectorKinds; textRole: "label"; enabled: !root._editing } }
        AppWidgets.FormField { Layout.fillWidth: true; label: "Purpose"; required: true
            AppControls.ComboBox { id: rateType; Layout.fillWidth: true; model: root._rateTypes; textRole: "label"; enabled: !root._editing } }
        AppWidgets.FormField { Layout.fillWidth: true; Layout.columnSpan: parent.columns; label: "Resource"; required: root._selectorKind() === "resource"; visible: root._selectorKind() === "resource"
            AppControls.SearchablePagedSelector { id: resourceSelector; Layout.fillWidth: true; searchPlaceholder: "Search active resources..."; contextKey: root.projectId + "|rate-resource"; enabled: !root._editing
                onLookupRequested: function(query, page, pageSize, generation, contextKey) { const result = root.workspaceController ? root.workspaceController.searchRateResources(root.projectId, query, page, pageSize) : ({"ok":false,"message":"Rate resource lookup unavailable."}); resourceSelector.acceptResult(result, generation, contextKey) } } }
        AppWidgets.FormField { Layout.fillWidth: true; Layout.columnSpan: parent.columns; label: "Department"; required: root._selectorKind() === "department"; visible: root._selectorKind() === "department"
            AppControls.SearchablePagedSelector { id: departmentSelector; Layout.fillWidth: true; searchPlaceholder: "Search active departments..."; contextKey: root.projectId + "|rate-department"; enabled: !root._editing
                onLookupRequested: function(query, page, pageSize, generation, contextKey) { const result = root.workspaceController ? root.workspaceController.searchRateDepartments(root.projectId, query, page, pageSize) : ({"ok":false,"message":"Rate department lookup unavailable."}); departmentSelector.acceptResult(result, generation, contextKey) } } }
        AppWidgets.FormField { Layout.fillWidth: true; Layout.columnSpan: parent.columns; label: root._selectorKind() === "role" ? "Role" : "Skill code"; required: true; visible: root._selectorKind() === "role" || root._selectorKind() === "skill"
            AppControls.TextField { id: dimensionField; Layout.fillWidth: true; enabled: !root._editing; placeholderText: root._selectorKind() === "role" ? "senior engineer" : "python" } }
        AppWidgets.FormField { Layout.fillWidth: true; label: "Rate amount"; required: true
            AppControls.TextField { id: amountField; Layout.fillWidth: true; enabled: !root._historical; placeholderText: "0.00" } }
        AppWidgets.FormField { Layout.fillWidth: true; label: "Currency"; required: true
            AppControls.ComboBox { id: currencyCombo; Layout.fillWidth: true; enabled: !root._editing && !root._historical; model: root.workspaceController ? root.workspaceController.currencyOptions : []; textRole: "label" } }
        AppWidgets.FormField { Layout.fillWidth: true; label: "Per unit"; required: true
            AppControls.ComboBox { id: unitCombo; Layout.fillWidth: true; enabled: !root._editing && !root._historical; model: root._units; textRole: "label" } }
        AppWidgets.FormField { Layout.fillWidth: true; label: "Effective from"
            AppControls.DateField { id: effectiveFromField; Layout.fillWidth: true; enabled: !root._historical } }
        AppWidgets.FormField { Layout.fillWidth: true; label: "Effective to"
            AppControls.DateField { id: effectiveToField; Layout.fillWidth: true } }
        AppWidgets.FormField { Layout.fillWidth: true; label: "Overtime multiplier"
            AppControls.TextField { id: overtimeField; Layout.fillWidth: true; enabled: !root._historical; placeholderText: "1.50" } }
        AppWidgets.FormField { Layout.fillWidth: true; label: "Weekend multiplier"
            AppControls.TextField { id: weekendField; Layout.fillWidth: true; enabled: !root._historical; placeholderText: "1.25" } }
        AppWidgets.FormField { Layout.fillWidth: true; label: "Holiday multiplier"
            AppControls.TextField { id: holidayField; Layout.fillWidth: true; enabled: !root._historical; placeholderText: "2.00" } }
    }
}

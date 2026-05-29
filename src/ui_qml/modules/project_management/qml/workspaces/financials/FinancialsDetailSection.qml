import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import App.Controls 1.0 as AppControls

Item {
    id: root

    property var costDetail: ({
        "id": "", "title": "", "statusLabel": "", "subtitle": "",
        "description": "", "emptyState": "", "fields": [], "state": {}
    })
    property var cashflowModel: ({ "title": "", "subtitle": "", "emptyState": "", "items": [] })
    property var ledgerModel: ({ "title": "", "subtitle": "", "emptyState": "", "items": [] })
    property var ledgerTableModel: null
    property var sourceAnalyticsModel: ({ "title": "", "subtitle": "", "emptyState": "", "items": [] })
    property var overviewModel: ({ "title": "", "subtitle": "", "metrics": [] })
    property var forecastModel: ({
        "method": "", "methodLabel": "", "bacLabel": "", "acLabel": "", "evLabel": "",
        "etcLabel": "", "eacLabel": "", "vacLabel": "", "cpiLabel": "",
        "isOverBudget": false, "exceedsThreshold": false, "alertMessage": "", "metrics": []
    })
    property var commitmentSummaryModel: ({
        "plannedLabel": "", "uncommittedLabel": "", "committedLabel": "",
        "invoicedLabel": "", "paidLabel": "", "exposureLabel": "", "commitmentRatePct": 0
    })
    property var baselineVarianceModel: []
    property bool isBusy: false
    property var detailPage: null

    readonly property bool _hasCost: String(root.costDetail.id || "").length > 0
    readonly property int _idx: root.detailPage ? root.detailPage.activeSectionIndex : 0
    readonly property var _sections: root.detailPage ? (root.detailPage.sections || []) : []

    function _secIdx(name) {
        const secs = root._sections
        for (let i = 0; i < secs.length; i++) {
            const s = secs[i]
            const sLabel = (typeof s === "string") ? s : (s.label || "")
            if (sLabel === name) return i
        }
        return -1
    }

    readonly property int _activeSectionH: {
        const secs = root._sections
        const entry = (secs.length > root._idx) ? secs[root._idx] : null
        const name = entry ? ((typeof entry === "string") ? entry : (entry.label || "")) : ""
        if (name === "Budget")          return _sec0.implicitHeight
        if (name === "Actuals")         return _sec1.implicitHeight
        if (name === "Forecast")        return _sec2.implicitHeight
        if (name === "Commitments")     return _sec3.implicitHeight
        if (name === "Invoices")        return _sec4.implicitHeight
        if (name === "Purchase Orders") return _sec5.implicitHeight
        if (name === "Earned Value")    return _sec6.implicitHeight
        if (name === "Variance")        return _sec8.implicitHeight
        if (name === "Activity")        return _sec7.implicitHeight
        return 0
    }

    readonly property var _ledgerColumns: [
        { "key": "title", "label": "Reference", "flex": 2 },
        { "key": "subtitle", "label": "Source / Stage", "flex": 1.5 },
        { "key": "statusLabel", "label": "Amount", "flex": 0, "minWidth": 110 },
        { "key": "supportingText", "label": "Task / Resource", "flex": 1.5 },
        { "key": "metaText", "label": "Date / Policy", "flex": 0, "minWidth": 130 }
    ]
    readonly property var _cashflowColumns: [
        { "key": "title", "label": "Period", "flex": 1 },
        { "key": "statusLabel", "label": "Forecast", "flex": 0, "minWidth": 110 },
        { "key": "subtitle", "label": "Planned / Committed", "flex": 2 },
        { "key": "supportingText", "label": "Actual / Exposure", "flex": 2 }
    ]
    readonly property var _commitmentColumns: [
        { "key": "title", "label": "Source", "flex": 2 },
        { "key": "statusLabel", "label": "Exposure", "flex": 0, "minWidth": 100 },
        { "key": "subtitle", "label": "Planned / Forecast", "flex": 2 },
        { "key": "supportingText", "label": "Committed / Actual", "flex": 2 }
    ]

    implicitHeight: _activeSectionH
    height: implicitHeight

    function _sv(key) {
        const s = root.costDetail.state || {}
        return String(s[key] || "")
    }

    AppWidgets.LazySectionLoader {
        id: _sec0
        anchors.left: parent.left
        anchors.right: parent.right
        active: root._idx === root._secIdx("Budget")
        sourceComponent: Component {
            Column {
                width: parent ? parent.width : 0
                spacing: 0

                AppWidgets.SectionHeading { width: parent.width; label: "Budget" }

                AppWidgets.EmptyState {
                    width: parent.width
                    visible: !root._hasCost
                    title: "No cost item selected"
                    message: root.costDetail.emptyState || "Select a cost item from the list to review its financial detail."
                }

                Item {
                    width: parent.width
                    visible: root._hasCost
                    implicitHeight: _budgetContent.implicitHeight + Theme.AppTheme.spacingMd * 2
                    height: implicitHeight

                    ColumnLayout {
                        id: _budgetContent
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.margins: Theme.AppTheme.spacingMd
                        spacing: Theme.AppTheme.spacingMd

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 0

                            Repeater {
                                model: [
                                    { "lbl": "Budget", "val": root._sv("plannedAmountLabel") },
                                    { "lbl": "Committed", "val": root._sv("committedAmountLabel") },
                                    { "lbl": "Actual", "val": root._sv("actualAmountLabel") },
                                    { "lbl": "Cost Type", "val": root.costDetail.statusLabel || "" }
                                ]

                                delegate: ColumnLayout {
                                    id: _budgetCell
                                    required property var modelData
                                    Layout.fillWidth: true
                                    spacing: Theme.AppTheme.spacingXs

                                    AppControls.Label {
                                        Layout.fillWidth: true
                                        text: String(_budgetCell.modelData.lbl)
                                        color: Theme.AppTheme.textMuted
                                        font.family: Theme.AppTheme.fontFamily
                                        font.pixelSize: Theme.AppTheme.captionSize
                                    }
                                    AppControls.Label {
                                        Layout.fillWidth: true
                                        text: String(_budgetCell.modelData.val)
                                        color: Theme.AppTheme.textPrimary
                                        font.family: Theme.AppTheme.fontFamily
                                        font.pixelSize: Theme.AppTheme.bodySize
                                        font.bold: true
                                        wrapMode: Text.NoWrap
                                        elide: Text.ElideRight
                                    }
                                }
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            height: 1
                            color: Theme.AppTheme.divider
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 0

                            Repeater {
                                model: [
                                    { "lbl": "Task", "val": root._sv("taskName") },
                                    { "lbl": "Date", "val": root._sv("incurredDateLabel") },
                                    { "lbl": "Currency", "val": root._sv("currency") },
                                    { "lbl": "Version", "val": root._sv("version") }
                                ]

                                delegate: ColumnLayout {
                                    id: _metaCell
                                    required property var modelData
                                    Layout.fillWidth: true
                                    spacing: Theme.AppTheme.spacingXs

                                    AppControls.Label {
                                        Layout.fillWidth: true
                                        text: String(_metaCell.modelData.lbl)
                                        color: Theme.AppTheme.textMuted
                                        font.family: Theme.AppTheme.fontFamily
                                        font.pixelSize: Theme.AppTheme.captionSize
                                    }
                                    AppControls.Label {
                                        Layout.fillWidth: true
                                        text: String(_metaCell.modelData.val) || "-"
                                        color: Theme.AppTheme.textSecondary
                                        font.family: Theme.AppTheme.fontFamily
                                        font.pixelSize: Theme.AppTheme.smallSize
                                        wrapMode: Text.NoWrap
                                        elide: Text.ElideRight
                                    }
                                }
                            }
                        }

                        AppControls.Label {
                            Layout.fillWidth: true
                            visible: String(root.costDetail.description || "").length > 0
                            text: root.costDetail.description || ""
                            color: Theme.AppTheme.textSecondary
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.smallSize
                            wrapMode: Text.WordWrap
                        }
                    }
                }
            }
        }
    }

    AppWidgets.LazySectionLoader {
        id: _sec1
        anchors.left: parent.left
        anchors.right: parent.right
        active: root._idx === root._secIdx("Actuals")
        sourceComponent: Component {
            Column {
                width: parent ? parent.width : 0
                spacing: 0
                AppWidgets.SectionHeading { width: parent.width; label: "Actuals" }
                AppWidgets.EmptyState {
                    width: parent.width
                    visible: (root.ledgerModel.items || []).length === 0
                    title: root.ledgerModel.emptyState || "No ledger entries"
                    message: "No ledger entries are available for the selected project."
                }
                Item {
                    width: parent.width
                    height: 220
                    visible: (root.ledgerModel.items || []).length > 0
                    AppWidgets.DataTable {
                        anchors.fill: parent
                        columns: root._ledgerColumns
                        sourceModel: root.ledgerTableModel
                        rows: root.ledgerModel.items || []
                        loading: root.isBusy
                        emptyText: root.ledgerModel.emptyState || "No ledger entries."
                    }
                }
            }
        }
    }

    AppWidgets.LazySectionLoader {
        id: _sec2
        anchors.left: parent.left
        anchors.right: parent.right
        active: root._idx === root._secIdx("Forecast")
        sourceComponent: Component {
            Column {
                width: parent ? parent.width : 0
                spacing: 0

                AppWidgets.SectionHeading { width: parent.width; label: "Forecast" }

                AppWidgets.InlineMessage {
                    width: parent.width
                    visible: String(root.forecastModel.alertMessage || "").length > 0
                    tone: root.forecastModel.exceedsThreshold ? "danger" : "warning"
                    message: root.forecastModel.alertMessage || ""
                }

                Item {
                    width: parent.width
                    implicitHeight: _fcastContent.implicitHeight + Theme.AppTheme.spacingMd * 2
                    height: implicitHeight

                    ColumnLayout {
                        id: _fcastContent
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.margins: Theme.AppTheme.spacingMd
                        spacing: Theme.AppTheme.spacingMd

                        AppControls.Label {
                            Layout.fillWidth: true
                            visible: String(root.forecastModel.methodLabel || "").length > 0
                            text: "Method: " + String(root.forecastModel.methodLabel || "")
                            color: Theme.AppTheme.textMuted
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.captionSize
                        }

                        GridLayout {
                            Layout.fillWidth: true
                            columns: 4
                            columnSpacing: Theme.AppTheme.spacingSm
                            rowSpacing: Theme.AppTheme.spacingSm

                            Repeater {
                                model: root.forecastModel.metrics || []

                                delegate: Rectangle {
                                    id: _fcastCell
                                    required property var modelData
                                    Layout.fillWidth: true
                                    radius: Theme.AppTheme.radiusMd
                                    color: Theme.AppTheme.surfaceAlt
                                    implicitHeight: _fcastCellContent.implicitHeight + Theme.AppTheme.spacingSm * 2

                                    readonly property color _valueColor: {
                                        const hint = String(_fcastCell.modelData.colorHint || "")
                                        if (hint === "success") return Theme.AppTheme.success
                                        if (hint === "warning") return Theme.AppTheme.warning
                                        if (hint === "danger")  return Theme.AppTheme.danger
                                        return Theme.AppTheme.textPrimary
                                    }

                                    ColumnLayout {
                                        id: _fcastCellContent
                                        anchors.left: parent.left
                                        anchors.right: parent.right
                                        anchors.top: parent.top
                                        anchors.margins: Theme.AppTheme.spacingSm
                                        spacing: 2

                                        AppControls.Label {
                                            Layout.fillWidth: true
                                            text: String(_fcastCell.modelData.label || "")
                                            color: Theme.AppTheme.textMuted
                                            font.family: Theme.AppTheme.fontFamily
                                            font.pixelSize: Theme.AppTheme.captionSize
                                        }
                                        AppControls.Label {
                                            Layout.fillWidth: true
                                            text: String(_fcastCell.modelData.value || "-")
                                            color: _fcastCell._valueColor
                                            font.family: Theme.AppTheme.fontFamily
                                            font.pixelSize: Theme.AppTheme.smallSize
                                            font.bold: true
                                            wrapMode: Text.NoWrap
                                            elide: Text.ElideRight
                                        }
                                    }
                                }
                            }
                        }

                        AppControls.Label {
                            Layout.fillWidth: true
                            visible: (root.forecastModel.metrics || []).length === 0
                            text: "Select a project to view EAC/ETC forecast metrics."
                            color: Theme.AppTheme.textMuted
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.smallSize
                            wrapMode: Text.WordWrap
                        }
                    }
                }
            }
        }
    }

    AppWidgets.LazySectionLoader {
        id: _sec3
        anchors.left: parent.left
        anchors.right: parent.right
        active: root._idx === root._secIdx("Commitments")
        sourceComponent: Component {
            Column {
                width: parent ? parent.width : 0
                spacing: 0

                AppWidgets.SectionHeading { width: parent.width; label: "Commitments" }

                Item {
                    width: parent.width
                    implicitHeight: _commitContent.implicitHeight + Theme.AppTheme.spacingMd * 2
                    height: implicitHeight

                    ColumnLayout {
                        id: _commitContent
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.margins: Theme.AppTheme.spacingMd
                        spacing: Theme.AppTheme.spacingMd

                        // Lifecycle strip: Uncommitted → Committed → Invoiced → Paid
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 0

                            Repeater {
                                model: [
                                    { "lbl": "Uncommitted", "val": root.commitmentSummaryModel.uncommittedLabel || "—" },
                                    { "lbl": "Committed",   "val": root.commitmentSummaryModel.committedLabel   || "—" },
                                    { "lbl": "Invoiced",    "val": root.commitmentSummaryModel.invoicedLabel    || "—" },
                                    { "lbl": "Paid",        "val": root.commitmentSummaryModel.paidLabel        || "—" }
                                ]

                                delegate: ColumnLayout {
                                    id: _commitCell
                                    required property var modelData
                                    Layout.fillWidth: true
                                    spacing: Theme.AppTheme.spacingXs

                                    AppControls.Label {
                                        Layout.fillWidth: true
                                        text: String(_commitCell.modelData.lbl)
                                        color: Theme.AppTheme.textMuted
                                        font.family: Theme.AppTheme.fontFamily
                                        font.pixelSize: Theme.AppTheme.captionSize
                                    }
                                    AppControls.Label {
                                        Layout.fillWidth: true
                                        text: String(_commitCell.modelData.val)
                                        color: Theme.AppTheme.textPrimary
                                        font.family: Theme.AppTheme.fontFamily
                                        font.pixelSize: Theme.AppTheme.bodySize
                                        font.bold: true
                                        wrapMode: Text.NoWrap
                                        elide: Text.ElideRight
                                    }
                                }
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            height: 1
                            color: Theme.AppTheme.divider
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 0

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: Theme.AppTheme.spacingXs
                                AppControls.Label {
                                    Layout.fillWidth: true
                                    text: "Exposure"
                                    color: Theme.AppTheme.textMuted
                                    font.family: Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.captionSize
                                }
                                AppControls.Label {
                                    Layout.fillWidth: true
                                    text: String(root.commitmentSummaryModel.exposureLabel || "—")
                                    color: Theme.AppTheme.textPrimary
                                    font.family: Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.bodySize
                                    font.bold: true
                                }
                            }

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: Theme.AppTheme.spacingXs
                                AppControls.Label {
                                    Layout.fillWidth: true
                                    text: "Commitment Rate"
                                    color: Theme.AppTheme.textMuted
                                    font.family: Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.captionSize
                                }
                                AppControls.Label {
                                    Layout.fillWidth: true
                                    text: Number(root.commitmentSummaryModel.commitmentRatePct || 0).toFixed(1) + "%"
                                    color: Theme.AppTheme.textPrimary
                                    font.family: Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.bodySize
                                    font.bold: true
                                }
                            }

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: Theme.AppTheme.spacingXs
                                AppControls.Label {
                                    Layout.fillWidth: true
                                    text: "Planned Total"
                                    color: Theme.AppTheme.textMuted
                                    font.family: Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.captionSize
                                }
                                AppControls.Label {
                                    Layout.fillWidth: true
                                    text: String(root.commitmentSummaryModel.plannedLabel || "—")
                                    color: Theme.AppTheme.textSecondary
                                    font.family: Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.smallSize
                                }
                            }
                        }

                        AppControls.Label {
                            Layout.fillWidth: true
                            visible: String(root.commitmentSummaryModel.plannedLabel || "").length === 0
                            text: "Select a project to view the commitment lifecycle breakdown."
                            color: Theme.AppTheme.textMuted
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.smallSize
                            wrapMode: Text.WordWrap
                        }
                    }
                }
            }
        }
    }

    AppWidgets.LazySectionLoader {
        id: _sec4
        anchors.left: parent.left
        anchors.right: parent.right
        active: root._idx === root._secIdx("Invoices")
        sourceComponent: Component {
            Column {
                width: parent ? parent.width : 0
                spacing: 0
                AppWidgets.SectionHeading { width: parent.width; label: "Invoices" }
                AppWidgets.EmptyState {
                    width: parent.width
                    title: "No invoices"
                    message: "Invoice management will be available in a future release."
                }
            }
        }
    }

    AppWidgets.LazySectionLoader {
        id: _sec5
        anchors.left: parent.left
        anchors.right: parent.right
        active: root._idx === root._secIdx("Purchase Orders")
        sourceComponent: Component {
            Column {
                width: parent ? parent.width : 0
                spacing: 0
                AppWidgets.SectionHeading { width: parent.width; label: "Purchase Orders" }
                AppWidgets.EmptyState {
                    width: parent.width
                    title: "No purchase orders"
                    message: "Purchase order tracking will be available in a future release."
                }
            }
        }
    }

    AppWidgets.LazySectionLoader {
        id: _sec6
        anchors.left: parent.left
        anchors.right: parent.right
        active: root._idx === root._secIdx("Earned Value")
        sourceComponent: Component {
            Column {
                width: parent ? parent.width : 0
                spacing: 0

                AppWidgets.SectionHeading { width: parent.width; label: "Earned Value" }

                AppWidgets.InlineMessage {
                    width: parent.width
                    visible: String(root.forecastModel.alertMessage || "").length > 0
                    tone: root.forecastModel.exceedsThreshold ? "danger" : "warning"
                    message: root.forecastModel.alertMessage || ""
                }

                AppWidgets.EmptyState {
                    width: parent.width
                    visible: (root.forecastModel.metrics || []).length === 0
                    title: "No EV data"
                    message: "Select a project to view earned value metrics (BAC, AC, EV, ETC, EAC, VAC, CPI)."
                }

                Item {
                    width: parent.width
                    visible: (root.forecastModel.metrics || []).length > 0
                    implicitHeight: _evGrid.implicitHeight + Theme.AppTheme.spacingMd * 2
                    height: implicitHeight

                    GridLayout {
                        id: _evGrid
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.margins: Theme.AppTheme.spacingMd
                        columns: 4
                        columnSpacing: Theme.AppTheme.spacingSm
                        rowSpacing: Theme.AppTheme.spacingSm

                        Repeater {
                            model: root.forecastModel.metrics || []

                            delegate: Rectangle {
                                id: _evCard
                                required property var modelData
                                Layout.fillWidth: true
                                radius: Theme.AppTheme.radiusMd
                                color: Theme.AppTheme.surfaceAlt
                                implicitHeight: _evCardContent.implicitHeight + Theme.AppTheme.spacingSm * 2

                                readonly property color _valueColor: {
                                    const hint = String(_evCard.modelData.colorHint || "")
                                    if (hint === "success") return Theme.AppTheme.success
                                    if (hint === "warning") return Theme.AppTheme.warning
                                    if (hint === "danger")  return Theme.AppTheme.danger
                                    return Theme.AppTheme.textPrimary
                                }

                                ColumnLayout {
                                    id: _evCardContent
                                    anchors.left: parent.left
                                    anchors.right: parent.right
                                    anchors.top: parent.top
                                    anchors.margins: Theme.AppTheme.spacingSm
                                    spacing: 2

                                    AppControls.Label {
                                        Layout.fillWidth: true
                                        text: String(_evCard.modelData.label || "")
                                        color: Theme.AppTheme.textMuted
                                        font.family: Theme.AppTheme.fontFamily
                                        font.pixelSize: Theme.AppTheme.captionSize
                                    }
                                    AppControls.Label {
                                        Layout.fillWidth: true
                                        text: String(_evCard.modelData.value || "-")
                                        color: _evCard._valueColor
                                        font.family: Theme.AppTheme.fontFamily
                                        font.pixelSize: Theme.AppTheme.smallSize
                                        font.bold: true
                                        wrapMode: Text.NoWrap
                                        elide: Text.ElideRight
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    AppWidgets.LazySectionLoader {
        id: _sec7
        anchors.left: parent.left
        anchors.right: parent.right
        active: root._idx === root._secIdx("Activity")
        sourceComponent: Component {
            Column {
                width: parent ? parent.width : 0
                spacing: 0
                AppWidgets.SectionHeading { width: parent.width; label: "Activity" }
                Item {
                    width: parent.width
                    implicitHeight: _activityFeed.implicitHeight + Theme.AppTheme.spacingMd * 2
                    height: implicitHeight
                    AppWidgets.ActivityFeed {
                        id: _activityFeed
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.margins: Theme.AppTheme.spacingMd
                        items: root.ledgerModel.items || []
                        emptyText: "No ledger activity recorded for the selected project."
                    }
                }
            }
        }
    }

    AppWidgets.LazySectionLoader {
        id: _sec8
        anchors.left: parent.left
        anchors.right: parent.right
        active: root._idx === root._secIdx("Variance")
        sourceComponent: Component {
            Column {
                width: parent ? parent.width : 0
                spacing: 0

                AppWidgets.SectionHeading { width: parent.width; label: "Variance" }

                AppWidgets.EmptyState {
                    width: parent.width
                    visible: (root.baselineVarianceModel || []).length === 0
                    title: "No variance data"
                    message: "Approve a baseline to see cost drift against the plan."
                }

                Item {
                    width: parent.width
                    visible: (root.baselineVarianceModel || []).length > 0
                    implicitHeight: _varianceTable.implicitHeight + Theme.AppTheme.spacingMd * 2
                    height: implicitHeight

                    Column {
                        id: _varianceTable
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.margins: Theme.AppTheme.spacingMd
                        spacing: 2

                        Repeater {
                            model: root.baselineVarianceModel || []

                            delegate: Rectangle {
                                id: _varRow
                                required property var modelData
                                width: _varianceTable.width
                                implicitHeight: _varRowContent.implicitHeight + Theme.AppTheme.spacingSm * 2
                                color: index % 2 === 0 ? Theme.AppTheme.surfaceAlt : "transparent"
                                radius: Theme.AppTheme.radiusSm

                                readonly property color _toneColor: {
                                    const t = String(_varRow.modelData.tone || "")
                                    if (t === "danger")  return Theme.AppTheme.danger
                                    if (t === "success") return Theme.AppTheme.success
                                    return Theme.AppTheme.textPrimary
                                }

                                RowLayout {
                                    id: _varRowContent
                                    anchors.left: parent.left
                                    anchors.right: parent.right
                                    anchors.top: parent.top
                                    anchors.margins: Theme.AppTheme.spacingSm
                                    spacing: Theme.AppTheme.spacingSm

                                    AppControls.Label {
                                        Layout.fillWidth: true
                                        text: String(_varRow.modelData.taskName || "")
                                        color: Theme.AppTheme.textPrimary
                                        font.family: Theme.AppTheme.fontFamily
                                        font.pixelSize: Theme.AppTheme.smallSize
                                        elide: Text.ElideRight
                                    }
                                    AppControls.Label {
                                        text: {
                                            const sv = _varRow.modelData.startVarianceDays || 0
                                            const fv = _varRow.modelData.finishVarianceDays || 0
                                            if (sv === 0 && fv === 0) return "On schedule"
                                            const parts = []
                                            if (sv !== 0) parts.push("Start " + (sv > 0 ? "+" : "") + sv + "d")
                                            if (fv !== 0) parts.push("Finish " + (fv > 0 ? "+" : "") + fv + "d")
                                            return parts.join(" / ")
                                        }
                                        color: Theme.AppTheme.textMuted
                                        font.family: Theme.AppTheme.fontFamily
                                        font.pixelSize: Theme.AppTheme.captionSize
                                    }
                                    AppControls.Label {
                                        text: String(_varRow.modelData.costVarianceLabel || "—")
                                        color: _varRow._toneColor
                                        font.family: Theme.AppTheme.fontFamily
                                        font.pixelSize: Theme.AppTheme.smallSize
                                        font.bold: true
                                        horizontalAlignment: Text.AlignRight
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

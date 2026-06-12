pragma ComponentBehavior: Bound

import QtQuick
import ProjectManagement.Controllers 1.0 as ProjectManagementControllers
import "FinancialsColumnConfig.js" as ColumnConfig

Item {
    id: root

    property ProjectManagementControllers.ProjectManagementWorkspaceCatalog pmCatalog: null
    property var workspaceController: null

    readonly property string tableId: "pm.financials.table"

    readonly property var workspaceModel: root.workspaceController
        ? root.workspaceController.workspace
        : ({
            "routeId": "project_management.financials",
            "title": "Financials",
            "summary": "Cost tracking, budget analysis, and financial reporting across projects."
        })

    readonly property var overviewModel: root.workspaceController
        ? root.workspaceController.overview
        : ({
            "title": root.workspaceModel.title,
            "subtitle": root.workspaceModel.summary,
            "metrics": []
        })

    readonly property var costItemsModel: root.workspaceController
        ? root.workspaceController.costItems
        : ({
            "title": "Cost Register",
            "subtitle": "Track budget, forecast, actuals, and commitments for project cost items.",
            "emptyState": "Project-management financials desktop API is not connected in this QML preview.",
            "items": []
        })

    readonly property var selectedCostItemModel: root.workspaceController
        ? root.workspaceController.selectedCostItem
        : ({
            "id": "",
            "title": "",
            "statusLabel": "",
            "subtitle": "",
            "description": "",
            "emptyState": "Select a cost item to review details or edit its values.",
            "fields": [],
            "state": {}
        })

    readonly property var detailSections: ["Details", "Activity"]

    property var columns: []

    function initializeColumns() {
        const base = ColumnConfig.baseColumns()
        if (root.workspaceController !== null) {
            const saved = root.workspaceController.loadTableColumnState(root.tableId)
            root.columns = ColumnConfig.applyColumnState(base, saved)
        } else {
            root.columns = base
        }
    }

    function saveColumnState(newColumns) {
        if (root.workspaceController !== null) {
            root.workspaceController.saveTableColumnState(
                root.tableId, ColumnConfig.buildColumnState(newColumns))
        }
        root.columns = newColumns
    }

    readonly property var bulkChangeProperties: {
        const props = []
        const costTypeOptions = root.workspaceController
            ? (root.workspaceController.costTypeOptions || []) : []
        if (costTypeOptions.length > 0)
            props.push({ "id": "costType", "label": "Cost Type", "values": costTypeOptions })
        return props
    }

    function optionIndexForValue(options, value) {
        const list = options || []
        for (let i = 0; i < list.length; i++) {
            if (String(list[i].value || "") === String(value || "")) return i
        }
        return 0
    }

    function lazyLoadDetailSection(detailPage, sectionIndex) {
        if (root.workspaceController === null) return
        const secName = root.detailSections[sectionIndex] || ""
        if (secName === "Activity") root.workspaceController.loadCostItemActivity()
    }

    Component.onCompleted: { root.initializeColumns() }
}

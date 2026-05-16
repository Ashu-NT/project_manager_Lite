import QtQuick
import Maintenance.Widgets 1.0 as MaintenanceWidgets
import Maintenance.Controllers 1.0 as MaintenanceControllers

MaintenanceWidgets.WorkspacePlaceholderPage {
    property MaintenanceControllers.MaintenanceWorkspaceCatalog maintenanceCatalog
    routeId: "maintenance_management.work_orders"
    fallbackTitle: "Work Orders"
    fallbackSummary: "Execution planning, task/step tracking, labor, materials, and evidence capture."
    architectureSummary: "Maintenance work-order migration is queued on top of the new desktop API boundary."
}

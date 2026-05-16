import QtQuick
import Maintenance.Widgets 1.0 as MaintenanceWidgets
import Maintenance.Controllers 1.0 as MaintenanceControllers

MaintenanceWidgets.WorkspacePlaceholderPage {
    property MaintenanceControllers.MaintenanceWorkspaceCatalog maintenanceCatalog
    routeId: "maintenance_management.work_requests"
    fallbackTitle: "Work Requests"
    fallbackSummary: "Request intake, triage, conversion to execution, and backlog prioritization."
    architectureSummary: "Maintenance work-request migration is queued on top of the new desktop API boundary."
}

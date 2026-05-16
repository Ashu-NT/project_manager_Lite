import QtQuick
import Maintenance.Widgets 1.0 as MaintenanceWidgets
import Maintenance.Controllers 1.0 as MaintenanceControllers

MaintenanceWidgets.WorkspacePlaceholderPage {
    property MaintenanceControllers.MaintenanceWorkspaceCatalog maintenanceCatalog
    routeId: "maintenance_management.preventive"
    fallbackTitle: "Preventive"
    fallbackSummary: "Plans, task templates, generated work packages, and schedule compliance management."
    architectureSummary: "Maintenance preventive-plan migration is queued on top of the new desktop API boundary."
}

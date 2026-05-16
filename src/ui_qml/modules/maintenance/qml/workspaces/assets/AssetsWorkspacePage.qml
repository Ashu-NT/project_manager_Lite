import QtQuick
import Maintenance.Widgets 1.0 as MaintenanceWidgets
import Maintenance.Controllers 1.0 as MaintenanceControllers

MaintenanceWidgets.WorkspacePlaceholderPage {
    property MaintenanceControllers.MaintenanceWorkspaceCatalog maintenanceCatalog
    routeId: "maintenance_management.assets"
    fallbackTitle: "Assets"
    fallbackSummary: "Sites, locations, systems, assets, and component-library structures for maintenance scope."
    architectureSummary: "Maintenance asset-library migration is queued on top of the new desktop API boundary."
}

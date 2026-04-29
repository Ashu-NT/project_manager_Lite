"""Platform QML presenters."""
from src.ui_qml.platform.presenters.access_workspace_presenter import PlatformAccessWorkspacePresenter
from src.ui_qml.platform.presenters.admin_presenter import PlatformAdminWorkspacePresenter
from src.ui_qml.platform.presenters.control_queue_presenter import PlatformControlQueuePresenter
from src.ui_qml.platform.presenters.control_presenter import PlatformControlWorkspacePresenter
from src.ui_qml.platform.presenters.department_catalog_presenter import (
    PlatformDepartmentCatalogPresenter,
)
from src.ui_qml.platform.presenters.document_catalog_presenter import PlatformDocumentCatalogPresenter
from src.ui_qml.platform.presenters.document_management_presenter import (
    PlatformDocumentManagementPresenter,
)
from src.ui_qml.platform.presenters.employee_catalog_presenter import PlatformEmployeeCatalogPresenter
from src.ui_qml.platform.presenters.organization_catalog_presenter import (
    PlatformOrganizationCatalogPresenter,
)
from src.ui_qml.platform.presenters.party_catalog_presenter import PlatformPartyCatalogPresenter
from src.ui_qml.platform.presenters.runtime_presenter import PlatformRuntimePresenter
from src.ui_qml.platform.presenters.settings_catalog_presenter import PlatformSettingsCatalogPresenter
from src.ui_qml.platform.presenters.settings_presenter import PlatformSettingsWorkspacePresenter
from src.ui_qml.platform.presenters.site_catalog_presenter import PlatformSiteCatalogPresenter
from src.ui_qml.platform.presenters.support_workspace_presenter import (
    PlatformSupportWorkspacePresenter,
)
from src.ui_qml.platform.presenters.user_catalog_presenter import PlatformUserCatalogPresenter

__all__ = [
    "PlatformAdminWorkspacePresenter",
    "PlatformAccessWorkspacePresenter",
    "PlatformControlQueuePresenter",
    "PlatformControlWorkspacePresenter",
    "PlatformDepartmentCatalogPresenter",
    "PlatformDocumentCatalogPresenter",
    "PlatformDocumentManagementPresenter",
    "PlatformEmployeeCatalogPresenter",
    "PlatformOrganizationCatalogPresenter",
    "PlatformPartyCatalogPresenter",
    "PlatformRuntimePresenter",
    "PlatformSettingsCatalogPresenter",
    "PlatformSettingsWorkspacePresenter",
    "PlatformSiteCatalogPresenter",
    "PlatformSupportWorkspacePresenter",
    "PlatformUserCatalogPresenter",
]

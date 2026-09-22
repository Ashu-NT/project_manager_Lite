"""Platform QML presenters."""
from src.ui_qml.platform.presenters.access.access_workspace_presenter import (
    PlatformAccessWorkspacePresenter,
)
from src.ui_qml.platform.presenters.overview.admin_overview_presenter import (
    PlatformAdminWorkspacePresenter,
)
from src.ui_qml.platform.presenters.calendars.calendar_catalog_presenter import (
    PlatformCalendarCatalogPresenter,
)
from src.ui_qml.platform.presenters.control.control_queue_presenter import (
    PlatformControlQueuePresenter,
)
from src.ui_qml.platform.presenters.control.control_presenter import (
    PlatformControlWorkspacePresenter,
)
from src.ui_qml.platform.presenters.departments.department_catalog_presenter import (
    PlatformDepartmentCatalogPresenter,
)
from src.ui_qml.platform.presenters.documents.document_catalog_presenter import (
    PlatformDocumentCatalogPresenter,
)
from src.ui_qml.platform.presenters.documents.document_management_presenter import (
    PlatformDocumentManagementPresenter,
)
from src.ui_qml.platform.presenters.employees.employee_catalog_presenter import (
    PlatformEmployeeCatalogPresenter,
)
from src.ui_qml.platform.presenters.organizations.organization_catalog_presenter import (
    PlatformOrganizationCatalogPresenter,
)
from src.ui_qml.platform.presenters.organizations.organization_activity_presenter import (
    PlatformOrganizationActivityPresenter,
)
from src.ui_qml.platform.presenters.parties.party_catalog_presenter import (
    PlatformPartyCatalogPresenter,
)
from src.ui_qml.platform.presenters.overview.runtime_overview_presenter import (
    PlatformRuntimePresenter,
)
from src.ui_qml.platform.presenters.settings.settings_catalog_presenter import (
    PlatformSettingsCatalogPresenter,
)
from src.ui_qml.platform.presenters.settings.settings_presenter import (
    PlatformSettingsWorkspacePresenter,
)
from src.ui_qml.platform.presenters.sites.site_catalog_presenter import (
    PlatformSiteCatalogPresenter,
)
from src.ui_qml.platform.presenters.support.support_workspace_presenter import (
    PlatformSupportWorkspacePresenter,
)
from src.ui_qml.platform.presenters.tenant_management.organization_switcher_presenter import (
    OrganizationSwitcherPresenter,
)
from src.ui_qml.platform.presenters.tenant_management.tenant_switcher_presenter import TenantSwitcherPresenter
from src.ui_qml.platform.presenters.users.user_catalog_presenter import (
    PlatformUserCatalogPresenter,
)

__all__ = [
    "PlatformAdminWorkspacePresenter",
    "PlatformAccessWorkspacePresenter",
    "PlatformCalendarCatalogPresenter",
    "PlatformControlQueuePresenter",
    "PlatformControlWorkspacePresenter",
    "PlatformDepartmentCatalogPresenter",
    "PlatformDocumentCatalogPresenter",
    "PlatformDocumentManagementPresenter",
    "PlatformEmployeeCatalogPresenter",
    "OrganizationSwitcherPresenter",
    "PlatformOrganizationCatalogPresenter",
    "PlatformOrganizationActivityPresenter",
    "PlatformPartyCatalogPresenter",
    "PlatformRuntimePresenter",
    "PlatformSettingsCatalogPresenter",
    "PlatformSettingsWorkspacePresenter",
    "PlatformSiteCatalogPresenter",
    "PlatformSupportWorkspacePresenter",
    "TenantSwitcherPresenter",
    "PlatformUserCatalogPresenter",
]



from __future__ import annotations

from PySide6.QtCore import Property, QObject, Signal, Slot
from PySide6.QtQml import QmlElement, QmlUncreatable

from src.ui_qml.platform.presenters.overview.admin_overview_presenter import (
    PlatformAdminWorkspacePresenter,
)
from src.ui_qml.platform.presenters.calendars.calendar_catalog_presenter import (
    PlatformCalendarCatalogPresenter,
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
from src.ui_qml.platform.presenters.sites.site_catalog_presenter import (
    PlatformSiteCatalogPresenter,
)
from src.ui_qml.platform.presenters.sites.site_activity_presenter import (
    PlatformSiteActivityPresenter,
)
from src.ui_qml.platform.presenters.users.user_catalog_presenter import (
    PlatformUserCatalogPresenter,
)

from src.ui_qml.platform.controllers.calendars.actions import (
    add_calendar_exception,
    add_calendar_recurring_event,
    assign_calendar,
    calculate_calendar_working_days,
    create_enterprise_calendar,
    delete_calendar_exception,
    delete_calendar_recurring_event,
    remove_calendar_assignment,
    update_enterprise_calendar,
)
from src.ui_qml.platform.controllers.calendars.context import (
    calendar_assignment_context,
    calendar_detail_context,
    site_calendar_summary,
)
from src.ui_qml.platform.controllers.calendars.calendar_controller import PlatformCalendarController
from src.ui_qml.platform.controllers.documents.actions import (
    add_document_link,
    create_document,
    create_document_structure,
    remove_document_link,
    select_document,
    toggle_document_active,
    toggle_document_structure_active,
    update_document,
    update_document_structure,
)
from src.ui_qml.platform.controllers.documents.document_controller import PlatformDocumentController
from src.ui_qml.platform.controllers.documents.document_structure_controller import (
    PlatformDocumentStructureController,
)
from src.ui_qml.platform.controllers.departments.department_controller import (
    PlatformDepartmentController,
)
from src.ui_qml.platform.controllers.departments.actions import (
    create_department,
    toggle_department_active,
    update_department,
)
from src.ui_qml.platform.controllers.employees.employee_controller import (
    PlatformEmployeeController,
)
from src.ui_qml.platform.controllers.employees.actions import (
    create_employee,
    toggle_employee_active,
    update_employee,
)
from src.ui_qml.platform.controllers.organizations.organization_controller import (
    PlatformOrganizationController,
)
from src.ui_qml.platform.controllers.organizations.actions import (
    activate_organization,
    apply_bulk_organization_currency,
    apply_bulk_organization_modules,
    apply_bulk_organization_timezone,
    archive_organization,
    bulk_activate_organizations,
    bulk_archive_organizations,
    bulk_deactivate_organizations,
    create_organization,
    deactivate_organization,
    update_organization,
)
from src.ui_qml.platform.controllers.parties.party_controller import (
    PlatformPartyController,
)
from src.ui_qml.platform.controllers.parties.actions import (
    create_party,
    toggle_party_active,
    update_party,
)
from src.ui_qml.platform.controllers.sites.site_controller import PlatformSiteController
from src.ui_qml.platform.controllers.sites.actions import (
    activate_site,
    archive_site,
    create_site,
    deactivate_site,
    update_site,
)
from src.ui_qml.platform.controllers.users.user_controller import (
    PlatformUserController,
)
from src.ui_qml.platform.controllers.users.actions import (
    create_user,
    toggle_user_active,
    update_user,
)
from src.ui_qml.platform.controllers.common import PlatformWorkspaceControllerBase

from .entity_code_dispatch import generate_entity_code
from .refresh_coordinator import do_refresh, refresh_overview
from .signal_binder import bind_child_signals

QML_IMPORT_NAME = "Platform.Controllers"
QML_IMPORT_MAJOR_VERSION = 1


@QmlElement
@QmlUncreatable("Platform workspace controllers are provided by the shell runtime.")
class PlatformAdminWorkspaceController(PlatformWorkspaceControllerBase):
    organizationsChanged = Signal()
    calendarsChanged = Signal()
    sitesChanged = Signal()
    departmentsChanged = Signal()
    employeesChanged = Signal()
    usersChanged = Signal()
    partiesChanged = Signal()
    documentsChanged = Signal()
    selectedDocumentChanged = Signal()
    documentPreviewChanged = Signal()
    documentLinksChanged = Signal()
    documentStructuresChanged = Signal()
    organizationEditorOptionsChanged = Signal()
    organizationSearchTextChanged = Signal()
    organizationStatusFilterChanged = Signal()
    selectedOrganizationIdsChanged = Signal()
    siteSearchTextChanged = Signal()
    siteStatusFilterChanged = Signal()
    departmentEditorOptionsChanged = Signal()
    employeeEditorOptionsChanged = Signal()
    userEditorOptionsChanged = Signal()
    partyEditorOptionsChanged = Signal()
    documentEditorOptionsChanged = Signal()
    documentStructureEditorOptionsChanged = Signal()

    def __init__(
        self,
        *,
        overview_presenter: PlatformAdminWorkspacePresenter,
        organization_presenter: PlatformOrganizationCatalogPresenter,
        organization_activity_presenter: PlatformOrganizationActivityPresenter | None = None,
        calendar_presenter: PlatformCalendarCatalogPresenter,
        site_presenter: PlatformSiteCatalogPresenter,
        site_activity_presenter: PlatformSiteActivityPresenter | None = None,
        department_presenter: PlatformDepartmentCatalogPresenter,
        employee_presenter: PlatformEmployeeCatalogPresenter,
        user_presenter: PlatformUserCatalogPresenter,
        party_presenter: PlatformPartyCatalogPresenter,
        document_presenter: PlatformDocumentCatalogPresenter,
        document_management_presenter: PlatformDocumentManagementPresenter,
        enterprise_calendar_api=None,
        runtime_api=None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._overview_presenter = overview_presenter
        self._enterprise_calendar_api = enterprise_calendar_api
        self._runtime_api = runtime_api
        self._organization_controller = PlatformOrganizationController(
            organization_presenter, self, activity_presenter=organization_activity_presenter
        )
        self._calendar_controller = PlatformCalendarController(calendar_presenter, self)
        self._site_controller = PlatformSiteController(
            site_presenter, self, activity_presenter=site_activity_presenter
        )
        self._department_controller = PlatformDepartmentController(department_presenter, self)
        self._employee_controller = PlatformEmployeeController(employee_presenter, self)
        self._user_controller = PlatformUserController(user_presenter, self)
        self._party_controller = PlatformPartyController(party_presenter, self)
        self._document_controller = PlatformDocumentController(
            presenter=document_presenter,
            management_presenter=document_management_presenter,
            parent=self,
        )
        self._document_structure_controller = PlatformDocumentStructureController(
            document_management_presenter,
            self,
        )
        self._bind_child_signals()
        self.refresh()

    # ── Properties ───────────────────────────────────────────────────────

    @Property("QVariantMap", notify=organizationsChanged)
    def organizations(self) -> dict[str, object]:
        return self._organization_controller.organizations

    @Property(str, notify=organizationSearchTextChanged)
    def organizationSearchText(self) -> str:
        return self._organization_controller.organizationSearchText

    @Property(str, notify=organizationStatusFilterChanged)
    def organizationStatusFilter(self) -> str:
        return self._organization_controller.organizationStatusFilter

    @Property("QVariantList", constant=True)
    def organizationPageSizeOptions(self) -> list[int]:
        return self._organization_controller.organizationPageSizeOptions

    @Property("QVariantList", notify=selectedOrganizationIdsChanged)
    def selectedOrganizationIds(self) -> list[str]:
        return self._organization_controller.selectedOrganizationIds

    @Property("QVariantMap", notify=calendarsChanged)
    def calendars(self) -> dict[str, object]:
        return self._calendar_controller.calendars

    @Property("QVariantMap", notify=sitesChanged)
    def sites(self) -> dict[str, object]:
        return self._site_controller.sites

    @Property(str, notify=siteSearchTextChanged)
    def siteSearchText(self) -> str:
        return self._site_controller.siteSearchText

    @Property(str, notify=siteStatusFilterChanged)
    def siteStatusFilter(self) -> str:
        return self._site_controller.siteStatusFilter

    @Property("QVariantList", constant=True)
    def sitePageSizeOptions(self) -> list[int]:
        return self._site_controller.sitePageSizeOptions

    @Property("QVariantMap", notify=departmentsChanged)
    def departments(self) -> dict[str, object]:
        return self._department_controller.departments

    @Property("QVariantMap", notify=employeesChanged)
    def employees(self) -> dict[str, object]:
        return self._employee_controller.employees

    @Property("QVariantMap", notify=usersChanged)
    def users(self) -> dict[str, object]:
        return self._user_controller.users

    @Property("QVariantMap", notify=partiesChanged)
    def parties(self) -> dict[str, object]:
        return self._party_controller.parties

    @Property("QVariantMap", notify=documentsChanged)
    def documents(self) -> dict[str, object]:
        return self._document_controller.documents

    @Property("QVariantMap", notify=selectedDocumentChanged)
    def selectedDocument(self) -> dict[str, object]:
        return self._document_controller.selectedDocument

    @Property("QVariantMap", notify=documentPreviewChanged)
    def documentPreview(self) -> dict[str, object]:
        return self._document_controller.documentPreview

    @Property("QVariantMap", notify=documentLinksChanged)
    def documentLinks(self) -> dict[str, object]:
        return self._document_controller.documentLinks

    @Property("QVariantMap", notify=documentStructuresChanged)
    def documentStructures(self) -> dict[str, object]:
        return self._document_structure_controller.documentStructures

    # ── Table models (sourceModel path) ──────────────────────────────────

    @Property(QObject, constant=True)
    def organizationsTableModel(self) -> QObject:
        return self._organization_controller.tableModel

    @Property(QObject, constant=True)
    def calendarsTableModel(self) -> QObject:
        return self._calendar_controller.tableModel

    @Property(QObject, constant=True)
    def sitesTableModel(self) -> QObject:
        return self._site_controller.tableModel

    @Property(QObject, constant=True)
    def departmentsTableModel(self) -> QObject:
        return self._department_controller.tableModel

    @Property(QObject, constant=True)
    def employeesTableModel(self) -> QObject:
        return self._employee_controller.tableModel

    @Property(QObject, constant=True)
    def usersTableModel(self) -> QObject:
        return self._user_controller.tableModel

    @Property(QObject, constant=True)
    def partiesTableModel(self) -> QObject:
        return self._party_controller.tableModel

    @Property(QObject, constant=True)
    def documentsTableModel(self) -> QObject:
        return self._document_controller.tableModel

    @Property(QObject, constant=True)
    def documentStructuresTableModel(self) -> QObject:
        return self._document_structure_controller.tableModel

    @Property("QVariantMap", notify=organizationEditorOptionsChanged)
    def organizationEditorOptions(self) -> dict[str, object]:
        return self._organization_controller.organizationEditorOptions

    @Property("QVariantMap", notify=departmentEditorOptionsChanged)
    def departmentEditorOptions(self) -> dict[str, object]:
        return self._department_controller.departmentEditorOptions

    @Property("QVariantMap", notify=employeeEditorOptionsChanged)
    def employeeEditorOptions(self) -> dict[str, object]:
        return self._employee_controller.employeeEditorOptions

    @Property("QVariantMap", notify=userEditorOptionsChanged)
    def userEditorOptions(self) -> dict[str, object]:
        return self._user_controller.userEditorOptions

    @Property("QVariantMap", notify=partyEditorOptionsChanged)
    def partyEditorOptions(self) -> dict[str, object]:
        return self._party_controller.partyEditorOptions

    @Property("QVariantMap", notify=documentEditorOptionsChanged)
    def documentEditorOptions(self) -> dict[str, object]:
        return self._document_controller.documentEditorOptions

    @Property("QVariantMap", notify=documentStructureEditorOptionsChanged)
    def documentStructureEditorOptions(self) -> dict[str, object]:
        return self._document_structure_controller.documentStructureEditorOptions

    # ── Core slots ────────────────────────────────────────────────────────

    @Slot()
    def refresh(self) -> None:
        do_refresh(self)

    def refresh_organizations(self) -> None:
        """Narrow reaction to the organization-collection ViewInvalidation target -- delegates
        to the organization sub-controller's own narrow refresh, unlike `refresh()`'s coarse
        cascade over every entity sub-controller (calendars/sites/departments/etc.), none of
        which are stale after an organization creation."""
        self._organization_controller.refresh_organizations()

    def refresh_users(self) -> None:
        self._user_controller.refresh()
        refresh_overview(self)

    def refresh_employees(self) -> None:
        self._employee_controller.refresh()

    def refresh_departments(self) -> None:
        self._department_controller.refresh()

    def refresh_sites(self) -> None:
        self._site_controller.refresh()

    def refresh_parties(self) -> None:
        self._party_controller.refresh()

    def refresh_documents(self) -> None:
        self._document_controller.refresh()

    def refresh_document_structures(self) -> None:
        self._document_structure_controller.refresh()

    def on_document_links_stale(self, module_code: str, entity_type: str, entity_id: str) -> None:
        """Narrow reaction to the reverse (`entity_type="document"`) shape of the
        `document_links` ViewInvalidation target -- refreshes the currently-selected
        document's link panel only when it's the document that actually changed, never a
        full workspace cascade."""
        if entity_type == "document" and entity_id == self._document_controller._selected_document_id:
            self._document_controller.refreshFocus()

    @Slot(str, "QVariantMap", result=str)
    def generateEntityCode(self, entity_type: str, payload: dict[str, object]) -> str:
        return generate_entity_code(self, entity_type, payload)

    # ── Organization slots ────────────────────────────────────────────────

    @Slot("QVariantMap", result="QVariantMap")
    def createOrganization(self, payload: dict[str, object]) -> dict[str, object]:
        return create_organization(self, payload)

    @Slot("QVariantMap", result="QVariantMap")
    def updateOrganization(self, payload: dict[str, object]) -> dict[str, object]:
        return update_organization(self, payload)

    @Slot(str, result="QVariantMap")
    def activateOrganization(self, organization_id: str) -> dict[str, object]:
        return activate_organization(self, organization_id)

    @Slot(str, result="QVariantMap")
    def deactivateOrganization(self, organization_id: str) -> dict[str, object]:
        return deactivate_organization(self, organization_id)

    @Slot(str, result="QVariantMap")
    def archiveOrganization(self, organization_id: str) -> dict[str, object]:
        return archive_organization(self, organization_id)

    @Slot(str, bool)
    def setOrganizationBulkSelection(self, organization_id: str, selected: bool) -> None:
        self._organization_controller.setOrganizationBulkSelection(organization_id, selected)

    @Slot()
    def clearOrganizationBulkSelection(self) -> None:
        self._organization_controller.clearOrganizationBulkSelection()

    @Slot()
    def selectVisibleOrganizations(self) -> None:
        self._organization_controller.selectVisibleOrganizations()

    @Slot(result="QVariantMap")
    def bulkActivateOrganizations(self) -> dict[str, object]:
        return bulk_activate_organizations(self)

    @Slot(result="QVariantMap")
    def bulkDeactivateOrganizations(self) -> dict[str, object]:
        return bulk_deactivate_organizations(self)

    @Slot(result="QVariantMap")
    def bulkArchiveOrganizations(self) -> dict[str, object]:
        return bulk_archive_organizations(self)

    @Slot("QVariantMap", result="QVariantMap")
    def applyBulkOrganizationCurrency(self, payload: dict[str, object]) -> dict[str, object]:
        return apply_bulk_organization_currency(self, payload)

    @Slot("QVariantMap", result="QVariantMap")
    def applyBulkOrganizationTimezone(self, payload: dict[str, object]) -> dict[str, object]:
        return apply_bulk_organization_timezone(self, payload)

    @Slot("QVariantMap", result="QVariantMap")
    def applyBulkOrganizationModules(self, payload: dict[str, object]) -> dict[str, object]:
        return apply_bulk_organization_modules(self, payload)

    @Slot(int)
    def setOrganizationPage(self, page: int) -> None:
        self._organization_controller.setOrganizationPage(page)

    @Slot(int)
    def setOrganizationPageSize(self, page_size: int) -> None:
        self._organization_controller.setOrganizationPageSize(page_size)

    @Slot(str)
    def setOrganizationSearchText(self, text: str) -> None:
        self._organization_controller.setOrganizationSearchText(text)

    @Slot(str)
    def setOrganizationStatusFilter(self, status: str) -> None:
        self._organization_controller.setOrganizationStatusFilter(status)

    @Slot(str, result="QVariantMap")
    def organizationDetailContext(self, organization_id: str) -> dict[str, object]:
        return self._organization_controller.organizationDetailContext(organization_id)

    @Slot(str, result="QVariantList")
    def organizationActivity(self, organization_id: str) -> list[dict[str, object]]:
        return self._organization_controller.organizationActivity(organization_id)

    @Slot(str, result="QVariantMap")
    def organizationCalendarSummary(self, organization_id: str) -> dict[str, object]:
        return self._organization_controller.organizationCalendarSummary(organization_id)

    @Slot(str, int, int, str, str, str, result="QVariantMap")
    def organizationActivityPage(
        self,
        organization_id: str,
        page: int,
        page_size: int,
        search: str,
        entity_type: str,
        date_range: str,
    ) -> dict[str, object]:
        return self._organization_controller.organizationActivityPage(
            organization_id, page, page_size, search, entity_type, date_range
        )

    # ── Calendar slots ────────────────────────────────────────────────────

    @Slot("QVariantMap", result="QVariantMap")
    def calculateCalendarWorkingDays(self, payload: dict[str, object]) -> dict[str, object]:
        return calculate_calendar_working_days(self, payload)

    @Slot("QVariantMap", result="QVariantMap")
    def createEnterpriseCalendar(self, payload: dict[str, object]) -> dict[str, object]:
        return create_enterprise_calendar(self, payload)

    @Slot("QVariantMap", result="QVariantMap")
    def updateEnterpriseCalendar(self, payload: dict[str, object]) -> dict[str, object]:
        return update_enterprise_calendar(self, payload)

    @Slot("QVariantMap", result="QVariantMap")
    def addCalendarException(self, payload: dict[str, object]) -> dict[str, object]:
        return add_calendar_exception(self, payload)

    @Slot("QVariantMap", result="QVariantMap")
    def addCalendarRecurringEvent(self, payload: dict[str, object]) -> dict[str, object]:
        return add_calendar_recurring_event(self, payload)

    @Slot(str, result="QVariantMap")
    def deleteCalendarException(self, exception_id: str) -> dict[str, object]:
        return delete_calendar_exception(self, exception_id)

    @Slot(str, result="QVariantMap")
    def deleteCalendarRecurringEvent(self, event_id: str) -> dict[str, object]:
        return delete_calendar_recurring_event(self, event_id)

    @Slot("QVariantMap", result="QVariantMap")
    def assignCalendar(self, payload: dict[str, object]) -> dict[str, object]:
        return assign_calendar(self, payload)

    @Slot(str, str, result="QVariantMap")
    def removeCalendarAssignment(
        self, assignment_id: str, entity_type: str
    ) -> dict[str, object]:
        return remove_calendar_assignment(self, assignment_id, entity_type)

    @Slot(str, result="QVariantMap")
    def calendarDetailContext(self, calendar_id: str) -> dict[str, object]:
        return calendar_detail_context(self, calendar_id)

    @Slot(str, str, str, str, result="QVariantMap")
    def calendarAssignmentContext(
        self,
        entity_type: str,
        entity_id: str,
        site_id: str = "",
        department_id: str = "",
    ) -> dict[str, object]:
        return calendar_assignment_context(self, entity_type, entity_id, site_id, department_id)

    @Slot(str, str, result="QVariantMap")
    def siteCalendarSummary(self, site_id: str, organization_id: str) -> dict[str, object]:
        return site_calendar_summary(self, site_id, organization_id)

    # ── Site slots ────────────────────────────────────────────────────────

    @Slot("QVariantMap", result="QVariantMap")
    def createSite(self, payload: dict[str, object]) -> dict[str, object]:
        return create_site(self, payload)

    @Slot("QVariantMap", result="QVariantMap")
    def updateSite(self, payload: dict[str, object]) -> dict[str, object]:
        return update_site(self, payload)

    @Slot(str, result="QVariantMap")
    def activateSite(self, site_id: str) -> dict[str, object]:
        return activate_site(self, site_id)

    @Slot(str, result="QVariantMap")
    def deactivateSite(self, site_id: str) -> dict[str, object]:
        return deactivate_site(self, site_id)

    @Slot(str, result="QVariantMap")
    def archiveSite(self, site_id: str) -> dict[str, object]:
        return archive_site(self, site_id)

    @Slot(int)
    def setSitePage(self, page: int) -> None:
        self._site_controller.setSitePage(page)

    @Slot(int)
    def setSitePageSize(self, page_size: int) -> None:
        self._site_controller.setSitePageSize(page_size)

    @Slot(str)
    def setSiteSearchText(self, text: str) -> None:
        self._site_controller.setSiteSearchText(text)

    @Slot(str)
    def setSiteStatusFilter(self, status: str) -> None:
        self._site_controller.setSiteStatusFilter(status)

    @Slot(str, int, int, str, str, result="QVariantMap")
    def organizationSitesPage(
        self,
        organization_id: str,
        page: int,
        page_size: int,
        search: str,
        status: str,
    ) -> dict[str, object]:
        return self._site_controller.organizationSitesPage(organization_id, page, page_size, search, status)

    @Slot(str, str, result="QVariantList")
    def siteActivity(self, site_id: str, organization_id: str) -> list[dict[str, object]]:
        return self._site_controller.siteActivity(site_id, organization_id)

    @Slot(str, str, int, int, str, str, result="QVariantMap")
    def siteActivityPage(
        self,
        site_id: str,
        organization_id: str,
        page: int,
        page_size: int,
        search: str,
        date_range: str,
    ) -> dict[str, object]:
        return self._site_controller.siteActivityPage(site_id, organization_id, page, page_size, search, date_range)

    # ── Department slots ──────────────────────────────────────────────────

    @Slot("QVariantMap", result="QVariantMap")
    def createDepartment(self, payload: dict[str, object]) -> dict[str, object]:
        return create_department(self, payload)

    @Slot("QVariantMap", result="QVariantMap")
    def updateDepartment(self, payload: dict[str, object]) -> dict[str, object]:
        return update_department(self, payload)

    @Slot(str, result="QVariantMap")
    def toggleDepartmentActive(self, department_id: str) -> dict[str, object]:
        return toggle_department_active(self, department_id)

    @Slot(str, int, int, str, str, result="QVariantMap")
    def organizationDepartmentsPage(
        self,
        organization_id: str,
        page: int,
        page_size: int,
        search: str,
        status: str,
    ) -> dict[str, object]:
        return self._department_controller.organizationDepartmentsPage(
            organization_id, page, page_size, search, status
        )

    @Slot(str, result="QVariantMap")
    def departmentsForSite(self, site_id: str) -> dict[str, object]:
        return self._department_controller.departmentsForSite(site_id)

    @Slot(str, str, int, int, str, str, result="QVariantMap")
    def departmentsForSitePage(
        self,
        site_id: str,
        organization_id: str,
        page: int,
        page_size: int,
        search: str,
        status: str,
    ) -> dict[str, object]:
        return self._department_controller.departmentsForSitePage(
            site_id, organization_id, page, page_size, search, status
        )

    # ── Employee slots ────────────────────────────────────────────────────

    @Slot("QVariantMap", result="QVariantMap")
    def createEmployee(self, payload: dict[str, object]) -> dict[str, object]:
        return create_employee(self, payload)

    @Slot("QVariantMap", result="QVariantMap")
    def updateEmployee(self, payload: dict[str, object]) -> dict[str, object]:
        return update_employee(self, payload)

    @Slot(str, result="QVariantMap")
    def toggleEmployeeActive(self, employee_id: str) -> dict[str, object]:
        return toggle_employee_active(self, employee_id)

    @Slot(str, int, int, str, str, result="QVariantMap")
    def organizationEmployeesPage(
        self,
        organization_id: str,
        page: int,
        page_size: int,
        search: str,
        status: str,
    ) -> dict[str, object]:
        return self._employee_controller.organizationEmployeesPage(
            organization_id, page, page_size, search, status
        )

    @Slot(str, result="QVariantMap")
    def employeesForDepartment(self, department_id: str) -> dict[str, object]:
        return self._employee_controller.employeesForDepartment(department_id)

    @Slot(str, result="QVariantMap")
    def employeesForSite(self, site_id: str) -> dict[str, object]:
        return self._employee_controller.employeesForSite(site_id)

    @Slot(str, str, int, int, str, str, str, result="QVariantMap")
    def employeesForSitePage(
        self,
        site_id: str,
        organization_id: str,
        page: int,
        page_size: int,
        search: str,
        status: str,
        department_id: str,
    ) -> dict[str, object]:
        return self._employee_controller.employeesForSitePage(
            site_id, organization_id, page, page_size, search, status, department_id
        )

    # ── User slots ────────────────────────────────────────────────────────

    @Slot("QVariantMap", result="QVariantMap")
    def createUser(self, payload: dict[str, object]) -> dict[str, object]:
        return create_user(self, payload)

    @Slot("QVariantMap", result="QVariantMap")
    def updateUser(self, payload: dict[str, object]) -> dict[str, object]:
        return update_user(self, payload)

    @Slot(str, result="QVariantMap")
    def toggleUserActive(self, user_id: str) -> dict[str, object]:
        return toggle_user_active(self, user_id)

    # ── Party slots ───────────────────────────────────────────────────────

    @Slot("QVariantMap", result="QVariantMap")
    def createParty(self, payload: dict[str, object]) -> dict[str, object]:
        return create_party(self, payload)

    @Slot("QVariantMap", result="QVariantMap")
    def updateParty(self, payload: dict[str, object]) -> dict[str, object]:
        return update_party(self, payload)

    @Slot(str, result="QVariantMap")
    def togglePartyActive(self, party_id: str) -> dict[str, object]:
        return toggle_party_active(self, party_id)

    # ── Document slots ────────────────────────────────────────────────────

    @Slot("QVariantMap", result="QVariantMap")
    def createDocument(self, payload: dict[str, object]) -> dict[str, object]:
        return create_document(self, payload)

    @Slot("QVariantMap", result="QVariantMap")
    def updateDocument(self, payload: dict[str, object]) -> dict[str, object]:
        return update_document(self, payload)

    @Slot(str, result="QVariantMap")
    def toggleDocumentActive(self, document_id: str) -> dict[str, object]:
        return toggle_document_active(self, document_id)

    @Slot(str)
    def selectDocument(self, document_id: str) -> None:
        select_document(self, document_id)

    @Slot(str, int, int, str, str, result="QVariantMap")
    def organizationDocumentsPage(
        self,
        organization_id: str,
        page: int,
        page_size: int,
        search: str,
        status: str,
    ) -> dict[str, object]:
        return self._document_controller.organizationDocumentsPage(
            organization_id, page, page_size, search, status
        )

    @Slot("QVariantMap", result="QVariantMap")
    def createDocumentStructure(self, payload: dict[str, object]) -> dict[str, object]:
        return create_document_structure(self, payload)

    @Slot("QVariantMap", result="QVariantMap")
    def updateDocumentStructure(self, payload: dict[str, object]) -> dict[str, object]:
        return update_document_structure(self, payload)

    @Slot(str, result="QVariantMap")
    def toggleDocumentStructureActive(self, structure_id: str) -> dict[str, object]:
        return toggle_document_structure_active(self, structure_id)

    @Slot("QVariantMap", result="QVariantMap")
    def addDocumentLink(self, payload: dict[str, object]) -> dict[str, object]:
        return add_document_link(self, payload)

    @Slot(str, result="QVariantMap")
    def removeDocumentLink(self, link_id: str) -> dict[str, object]:
        return remove_document_link(self, link_id)

    # ── Internal wiring ───────────────────────────────────────────────────

    def _bind_child_signals(self) -> None:
        bind_child_signals(self)


__all__ = ["PlatformAdminWorkspaceController"]

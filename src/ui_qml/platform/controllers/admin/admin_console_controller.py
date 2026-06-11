from __future__ import annotations

from PySide6.QtCore import Property, QObject, Signal, Slot
from PySide6.QtQml import QmlElement, QmlUncreatable

from src.ui_qml.platform.presenters.admin_presenter import PlatformAdminWorkspacePresenter
from src.ui_qml.platform.presenters.calendar_catalog_presenter import PlatformCalendarCatalogPresenter
from src.ui_qml.platform.presenters.department_catalog_presenter import PlatformDepartmentCatalogPresenter
from src.ui_qml.platform.presenters.document_catalog_presenter import PlatformDocumentCatalogPresenter
from src.ui_qml.platform.presenters.document_management_presenter import (
    PlatformDocumentManagementPresenter,
)
from src.ui_qml.platform.presenters.employee_catalog_presenter import PlatformEmployeeCatalogPresenter
from src.ui_qml.platform.presenters.organization_catalog_presenter import (
    PlatformOrganizationCatalogPresenter,
)
from src.ui_qml.platform.presenters.party_catalog_presenter import PlatformPartyCatalogPresenter
from src.ui_qml.platform.presenters.site_catalog_presenter import PlatformSiteCatalogPresenter
from src.ui_qml.platform.presenters.user_catalog_presenter import PlatformUserCatalogPresenter

from .admin_calendar_actions import (
    add_calendar_exception,
    add_calendar_holiday,
    add_calendar_recurring_event,
    assign_calendar,
    calculate_calendar_working_days,
    create_enterprise_calendar,
    delete_calendar_exception,
    delete_calendar_holiday,
    delete_calendar_recurring_event,
    remove_calendar_assignment,
    update_calendar,
    update_enterprise_calendar,
)
from .admin_calendar_context import calendar_assignment_context, calendar_detail_context
from .admin_child_signal_binder import bind_child_signals
from .admin_document_actions import (
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
from .admin_domain_event_binder import bind_domain_events
from .admin_entity_actions import (
    create_department,
    create_employee,
    create_organization,
    create_party,
    create_site,
    create_user,
    generate_entity_code,
    set_active_organization,
    toggle_department_active,
    toggle_employee_active,
    toggle_party_active,
    toggle_site_active,
    toggle_user_active,
    update_department,
    update_employee,
    update_organization,
    update_party,
    update_site,
    update_user,
)
from .admin_refresh_service import do_refresh
from .calendar_controller import PlatformCalendarController
from .department_controller import PlatformDepartmentController
from .document_controller import PlatformDocumentController
from .document_structure_controller import PlatformDocumentStructureController
from .employee_controller import PlatformEmployeeController
from .organization_controller import PlatformOrganizationController
from .party_controller import PlatformPartyController
from .site_controller import PlatformSiteController
from .user_controller import PlatformUserController
from ..common import PlatformWorkspaceControllerBase

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
        calendar_presenter: PlatformCalendarCatalogPresenter,
        site_presenter: PlatformSiteCatalogPresenter,
        department_presenter: PlatformDepartmentCatalogPresenter,
        employee_presenter: PlatformEmployeeCatalogPresenter,
        user_presenter: PlatformUserCatalogPresenter,
        party_presenter: PlatformPartyCatalogPresenter,
        document_presenter: PlatformDocumentCatalogPresenter,
        document_management_presenter: PlatformDocumentManagementPresenter,
        enterprise_calendar_api=None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._overview_presenter = overview_presenter
        self._enterprise_calendar_api = enterprise_calendar_api
        self._organization_controller = PlatformOrganizationController(organization_presenter, self)
        self._calendar_controller = PlatformCalendarController(calendar_presenter, self)
        self._site_controller = PlatformSiteController(site_presenter, self)
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
        self._bind_domain_events()
        self.refresh()

    # ── Properties ───────────────────────────────────────────────────────

    @Property("QVariantMap", notify=organizationsChanged)
    def organizations(self) -> dict[str, object]:
        return self._organization_controller.organizations

    @Property("QVariantMap", notify=calendarsChanged)
    def calendars(self) -> dict[str, object]:
        return self._calendar_controller.calendars

    @Property("QVariantMap", notify=sitesChanged)
    def sites(self) -> dict[str, object]:
        return self._site_controller.sites

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
    def setActiveOrganization(self, organization_id: str) -> dict[str, object]:
        return set_active_organization(self, organization_id)

    # ── Calendar slots ────────────────────────────────────────────────────

    @Slot("QVariantMap", result="QVariantMap")
    def updateCalendar(self, payload: dict[str, object]) -> dict[str, object]:
        return update_calendar(self, payload)

    @Slot("QVariantMap", result="QVariantMap")
    def addCalendarHoliday(self, payload: dict[str, object]) -> dict[str, object]:
        return add_calendar_holiday(self, payload)

    @Slot(str, result="QVariantMap")
    def deleteCalendarHoliday(self, holiday_id: str) -> dict[str, object]:
        return delete_calendar_holiday(self, holiday_id)

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

    # ── Site slots ────────────────────────────────────────────────────────

    @Slot("QVariantMap", result="QVariantMap")
    def createSite(self, payload: dict[str, object]) -> dict[str, object]:
        return create_site(self, payload)

    @Slot("QVariantMap", result="QVariantMap")
    def updateSite(self, payload: dict[str, object]) -> dict[str, object]:
        return update_site(self, payload)

    @Slot(str, result="QVariantMap")
    def toggleSiteActive(self, site_id: str) -> dict[str, object]:
        return toggle_site_active(self, site_id)

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

    def _bind_domain_events(self) -> None:
        bind_domain_events(self)


__all__ = ["PlatformAdminWorkspaceController"]

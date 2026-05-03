from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Property, QObject, Signal, Slot

from src.core.platform.notifications.domain_events import domain_events
from src.ui_qml.platform.presenters.admin_presenter import PlatformAdminWorkspacePresenter
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

from .department_controller import PlatformDepartmentController
from .document_controller import PlatformDocumentController
from .document_structure_controller import PlatformDocumentStructureController
from .employee_controller import PlatformEmployeeController
from .organization_controller import PlatformOrganizationController
from .party_controller import PlatformPartyController
from .site_controller import PlatformSiteController
from .user_controller import PlatformUserController
from ..common import PlatformWorkspaceControllerBase, serialize_workspace_overview


class PlatformAdminWorkspaceController(PlatformWorkspaceControllerBase):
    organizationsChanged = Signal()
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
        site_presenter: PlatformSiteCatalogPresenter,
        department_presenter: PlatformDepartmentCatalogPresenter,
        employee_presenter: PlatformEmployeeCatalogPresenter,
        user_presenter: PlatformUserCatalogPresenter,
        party_presenter: PlatformPartyCatalogPresenter,
        document_presenter: PlatformDocumentCatalogPresenter,
        document_management_presenter: PlatformDocumentManagementPresenter,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._overview_presenter = overview_presenter
        self._organization_controller = PlatformOrganizationController(organization_presenter, self)
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

    @Property("QVariantMap", notify=organizationsChanged)
    def organizations(self) -> dict[str, object]:
        return self._organization_controller.organizations

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

    @Slot()
    def refresh(self) -> None:
        self._set_is_loading(True)
        self._set_error_message("")
        self._refresh_overview()
        self._organization_controller.refresh()
        self._site_controller.refresh()
        self._department_controller.refresh()
        self._employee_controller.refresh()
        self._user_controller.refresh()
        self._party_controller.refresh()
        self._document_controller.refresh()
        self._document_structure_controller.refresh()
        self._refresh_empty_state()
        self._set_is_loading(False)

    @Slot("QVariantMap", result="QVariantMap")
    def createOrganization(self, payload: dict[str, object]) -> dict[str, object]:
        return self._run_admin_action(
            action=lambda: self._organization_controller.createOrganization(payload),
            on_success=self._refresh_after_organization_change,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def updateOrganization(self, payload: dict[str, object]) -> dict[str, object]:
        return self._run_admin_action(
            action=lambda: self._organization_controller.updateOrganization(payload),
            on_success=self._refresh_after_organization_change,
        )

    @Slot(str, result="QVariantMap")
    def setActiveOrganization(self, organization_id: str) -> dict[str, object]:
        return self._run_admin_action(
            action=lambda: self._organization_controller.setActiveOrganization(organization_id),
            on_success=self._refresh_after_organization_change,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def createSite(self, payload: dict[str, object]) -> dict[str, object]:
        return self._run_admin_action(
            action=lambda: self._site_controller.createSite(payload),
            on_success=self._refresh_after_site_change,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def updateSite(self, payload: dict[str, object]) -> dict[str, object]:
        return self._run_admin_action(
            action=lambda: self._site_controller.updateSite(payload),
            on_success=self._refresh_after_site_change,
        )

    @Slot(str, result="QVariantMap")
    def toggleSiteActive(self, site_id: str) -> dict[str, object]:
        return self._run_admin_action(
            action=lambda: self._site_controller.toggleSiteActive(site_id),
            on_success=self._refresh_after_site_change,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def createDepartment(self, payload: dict[str, object]) -> dict[str, object]:
        return self._run_admin_action(
            action=lambda: self._department_controller.createDepartment(payload),
            on_success=self._refresh_after_department_change,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def updateDepartment(self, payload: dict[str, object]) -> dict[str, object]:
        return self._run_admin_action(
            action=lambda: self._department_controller.updateDepartment(payload),
            on_success=self._refresh_after_department_change,
        )

    @Slot(str, result="QVariantMap")
    def toggleDepartmentActive(self, department_id: str) -> dict[str, object]:
        return self._run_admin_action(
            action=lambda: self._department_controller.toggleDepartmentActive(department_id),
            on_success=self._refresh_after_department_change,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def createEmployee(self, payload: dict[str, object]) -> dict[str, object]:
        return self._run_admin_action(
            action=lambda: self._employee_controller.createEmployee(payload),
            on_success=self._refresh_after_employee_change,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def updateEmployee(self, payload: dict[str, object]) -> dict[str, object]:
        return self._run_admin_action(
            action=lambda: self._employee_controller.updateEmployee(payload),
            on_success=self._refresh_after_employee_change,
        )

    @Slot(str, result="QVariantMap")
    def toggleEmployeeActive(self, employee_id: str) -> dict[str, object]:
        return self._run_admin_action(
            action=lambda: self._employee_controller.toggleEmployeeActive(employee_id),
            on_success=self._refresh_after_employee_change,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def createUser(self, payload: dict[str, object]) -> dict[str, object]:
        return self._run_admin_action(
            action=lambda: self._user_controller.createUser(payload),
            on_success=self._refresh_after_user_change,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def updateUser(self, payload: dict[str, object]) -> dict[str, object]:
        return self._run_admin_action(
            action=lambda: self._user_controller.updateUser(payload),
            on_success=self._refresh_after_user_change,
        )

    @Slot(str, result="QVariantMap")
    def toggleUserActive(self, user_id: str) -> dict[str, object]:
        return self._run_admin_action(
            action=lambda: self._user_controller.toggleUserActive(user_id),
            on_success=self._refresh_after_user_change,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def createParty(self, payload: dict[str, object]) -> dict[str, object]:
        return self._run_admin_action(
            action=lambda: self._party_controller.createParty(payload),
            on_success=self._refresh_after_party_change,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def updateParty(self, payload: dict[str, object]) -> dict[str, object]:
        return self._run_admin_action(
            action=lambda: self._party_controller.updateParty(payload),
            on_success=self._refresh_after_party_change,
        )

    @Slot(str, result="QVariantMap")
    def togglePartyActive(self, party_id: str) -> dict[str, object]:
        return self._run_admin_action(
            action=lambda: self._party_controller.togglePartyActive(party_id),
            on_success=self._refresh_after_party_change,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def createDocument(self, payload: dict[str, object]) -> dict[str, object]:
        return self._run_admin_action(
            action=lambda: self._document_controller.createDocument(payload),
            on_success=self._refresh_after_document_change,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def updateDocument(self, payload: dict[str, object]) -> dict[str, object]:
        return self._run_admin_action(
            action=lambda: self._document_controller.updateDocument(payload),
            on_success=self._refresh_after_document_change,
        )

    @Slot(str, result="QVariantMap")
    def toggleDocumentActive(self, document_id: str) -> dict[str, object]:
        return self._run_admin_action(
            action=lambda: self._document_controller.toggleDocumentActive(document_id),
            on_success=self._refresh_after_document_change,
        )

    @Slot(str)
    def selectDocument(self, document_id: str) -> None:
        self._document_controller.selectDocument(document_id)

    @Slot("QVariantMap", result="QVariantMap")
    def createDocumentStructure(self, payload: dict[str, object]) -> dict[str, object]:
        return self._run_admin_action(
            action=lambda: self._document_structure_controller.createDocumentStructure(payload),
            on_success=self._refresh_after_document_structure_change,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def updateDocumentStructure(self, payload: dict[str, object]) -> dict[str, object]:
        return self._run_admin_action(
            action=lambda: self._document_structure_controller.updateDocumentStructure(payload),
            on_success=self._refresh_after_document_structure_change,
        )

    @Slot(str, result="QVariantMap")
    def toggleDocumentStructureActive(self, structure_id: str) -> dict[str, object]:
        return self._run_admin_action(
            action=lambda: self._document_structure_controller.toggleDocumentStructureActive(structure_id),
            on_success=self._refresh_after_document_structure_change,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def addDocumentLink(self, payload: dict[str, object]) -> dict[str, object]:
        return self._run_admin_action(
            action=lambda: self._document_controller.addDocumentLink(payload),
            on_success=self._refresh_after_document_link_change,
        )

    @Slot(str, result="QVariantMap")
    def removeDocumentLink(self, link_id: str) -> dict[str, object]:
        return self._run_admin_action(
            action=lambda: self._document_controller.removeDocumentLink(link_id),
            on_success=self._refresh_after_document_link_change,
        )

    def _bind_domain_events(self) -> None:
        for signal in (
            domain_events.organizations_changed,
            domain_events.sites_changed,
            domain_events.departments_changed,
            domain_events.employees_changed,
            domain_events.auth_changed,
            domain_events.parties_changed,
            domain_events.documents_changed,
        ):
            self._subscribe_domain_signal(signal, self._on_domain_event)

    def _on_domain_event(self, _payload: object) -> None:
        self._request_domain_refresh()

    def _bind_child_signals(self) -> None:
        self._organization_controller.organizationsChanged.connect(self.organizationsChanged.emit)
        self._organization_controller.organizationEditorOptionsChanged.connect(
            self.organizationEditorOptionsChanged.emit
        )
        self._site_controller.sitesChanged.connect(self.sitesChanged.emit)
        self._department_controller.departmentsChanged.connect(self.departmentsChanged.emit)
        self._department_controller.departmentEditorOptionsChanged.connect(
            self.departmentEditorOptionsChanged.emit
        )
        self._employee_controller.employeesChanged.connect(self.employeesChanged.emit)
        self._employee_controller.employeeEditorOptionsChanged.connect(
            self.employeeEditorOptionsChanged.emit
        )
        self._user_controller.usersChanged.connect(self.usersChanged.emit)
        self._user_controller.userEditorOptionsChanged.connect(self.userEditorOptionsChanged.emit)
        self._party_controller.partiesChanged.connect(self.partiesChanged.emit)
        self._party_controller.partyEditorOptionsChanged.connect(self.partyEditorOptionsChanged.emit)
        self._document_controller.documentsChanged.connect(self.documentsChanged.emit)
        self._document_controller.documentEditorOptionsChanged.connect(
            self.documentEditorOptionsChanged.emit
        )
        self._document_controller.selectedDocumentChanged.connect(self.selectedDocumentChanged.emit)
        self._document_controller.documentPreviewChanged.connect(self.documentPreviewChanged.emit)
        self._document_controller.documentLinksChanged.connect(self.documentLinksChanged.emit)
        self._document_structure_controller.documentStructuresChanged.connect(
            self.documentStructuresChanged.emit
        )
        self._document_structure_controller.documentStructureEditorOptionsChanged.connect(
            self.documentStructureEditorOptionsChanged.emit
        )

    def _run_admin_action(
        self,
        *,
        action: Callable[[], dict[str, object]],
        on_success: Callable[[], None],
    ) -> dict[str, object]:
        self._set_is_busy(True)
        self._set_error_message("")
        try:
            result = dict(action())
            self._set_operation_result(result)
            if result.get("ok"):
                self._set_feedback_message(str(result.get("message", "")))
                on_success()
            else:
                self._set_feedback_message("")
                self._set_error_message(str(result.get("message", "")))
            return result
        finally:
            self._set_is_busy(False)

    def _refresh_after_organization_change(self) -> None:
        self._refresh_overview()
        self._site_controller.refresh()
        self._department_controller.refresh()
        self._employee_controller.refresh()
        self._party_controller.refresh()
        self._document_controller.refresh()
        self._document_structure_controller.refresh()
        self._refresh_empty_state()

    def _refresh_after_site_change(self) -> None:
        self._refresh_overview()
        self._department_controller.refresh()
        self._employee_controller.refresh()
        self._refresh_empty_state()

    def _refresh_after_department_change(self) -> None:
        self._refresh_overview()
        self._employee_controller.refresh()
        self._refresh_empty_state()

    def _refresh_after_employee_change(self) -> None:
        self._refresh_overview()
        self._refresh_empty_state()

    def _refresh_after_user_change(self) -> None:
        self._refresh_overview()
        self._refresh_empty_state()

    def _refresh_after_party_change(self) -> None:
        self._refresh_overview()
        self._refresh_empty_state()

    def _refresh_after_document_change(self) -> None:
        self._refresh_overview()
        self._refresh_empty_state()

    def _refresh_after_document_structure_change(self) -> None:
        self._document_controller.refresh()
        self._refresh_empty_state()

    def _refresh_after_document_link_change(self) -> None:
        self._refresh_empty_state()

    def _refresh_overview(self) -> None:
        self._set_overview(serialize_workspace_overview(self._overview_presenter.build_overview()))

    def _refresh_empty_state(self) -> None:
        has_items = any(
            catalog.get("items")
            for catalog in (
                self.organizations,
                self.sites,
                self.departments,
                self.employees,
                self.users,
                self.parties,
                self.documents,
            )
        )
        self._set_empty_state("" if has_items else "No platform administration records are available yet.")


__all__ = ["PlatformAdminWorkspaceController"]

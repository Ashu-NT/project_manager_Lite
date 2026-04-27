from __future__ import annotations

from typing import Any, Callable

from PySide6.QtCore import Property, QObject, Signal, Slot

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

from ..common import (
    PlatformWorkspaceControllerBase,
    run_mutation,
    serialize_action_list,
    serialize_operation_result,
    serialize_workspace_overview,
)


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
        self._organization_presenter = organization_presenter
        self._organization_controller = PlatformOrganizationController(organization_presenter)
        self._site_presenter = site_presenter
        self._site_controller = PlatformSiteController(site_presenter)
        self._department_presenter = department_presenter
        self._department_controller = PlatformDepartmentController(department_presenter)
        self._employee_presenter = employee_presenter
        self._employee_controller = PlatformEmployeeController(employee_presenter)
        self._user_presenter = user_presenter
        self._user_controller = PlatformUserController(user_presenter)
        self._party_presenter = party_presenter
        self._party_controller = PlatformPartyController(party_presenter)
        self._document_presenter = document_presenter
        self._document_controller = PlatformDocumentController(document_presenter)
        self._document_management_presenter = document_management_presenter
        self._document_structure_controller = PlatformDocumentStructureController(document_management_presenter)
        self._organizations: dict[str, object] = {"title": "", "subtitle": "", "emptyState": "", "items": []}
        self._sites: dict[str, object] = {"title": "", "subtitle": "", "emptyState": "", "items": []}
        self._departments: dict[str, object] = {"title": "", "subtitle": "", "emptyState": "", "items": []}
        self._employees: dict[str, object] = {"title": "", "subtitle": "", "emptyState": "", "items": []}
        self._users: dict[str, object] = {"title": "", "subtitle": "", "emptyState": "", "items": []}
        self._parties: dict[str, object] = {"title": "", "subtitle": "", "emptyState": "", "items": []}
        self._documents: dict[str, object] = {"title": "", "subtitle": "", "emptyState": "", "items": []}
        self._selected_document: dict[str, object] = {
            "hasSelection": False,
            "documentId": "",
            "title": "Select a document",
            "summary": "",
            "badges": [],
            "metadataRows": [],
            "notes": "",
        }
        self._document_preview: dict[str, object] = {
            "statusLabel": "No document selected",
            "summary": "",
            "canOpen": False,
            "openLabel": "Open Source",
            "openTargetUrl": "",
        }
        self._document_links: dict[str, object] = {"title": "", "subtitle": "", "emptyState": "", "items": []}
        self._document_structures: dict[str, object] = {"title": "", "subtitle": "", "emptyState": "", "items": []}
        self._organization_editor_options: dict[str, object] = {"moduleOptions": []}
        self._department_editor_options: dict[str, object] = {
            "siteOptions": [],
            "locationOptions": [],
            "parentOptions": [],
        }
        self._employee_editor_options: dict[str, object] = {
            "siteOptions": [],
            "departmentOptions": [],
        }
        self._user_editor_options: dict[str, object] = {"roleOptions": []}
        self._party_editor_options: dict[str, object] = {"typeOptions": []}
        self._document_editor_options: dict[str, object] = {
            "typeOptions": [],
            "structureOptions": [],
            "storageKindOptions": [],
        }
        self._document_structure_editor_options: dict[str, object] = {
            "parentOptions": [],
            "objectScopeOptions": [],
            "defaultTypeOptions": [],
        }
        self._selected_document_id = ""
        self.refresh()

    @Property("QVariantMap", notify=organizationsChanged)
    def organizations(self) -> dict[str, object]:
        return self._organizations

    @Property("QVariantMap", notify=sitesChanged)
    def sites(self) -> dict[str, object]:
        return self._sites

    @Property("QVariantMap", notify=departmentsChanged)
    def departments(self) -> dict[str, object]:
        return self._departments

    @Property("QVariantMap", notify=employeesChanged)
    def employees(self) -> dict[str, object]:
        return self._employees

    @Property("QVariantMap", notify=usersChanged)
    def users(self) -> dict[str, object]:
        return self._users

    @Property("QVariantMap", notify=partiesChanged)
    def parties(self) -> dict[str, object]:
        return self._parties

    @Property("QVariantMap", notify=documentsChanged)
    def documents(self) -> dict[str, object]:
        return self._documents

    @Property("QVariantMap", notify=selectedDocumentChanged)
    def selectedDocument(self) -> dict[str, object]:
        return self._selected_document

    @Property("QVariantMap", notify=documentPreviewChanged)
    def documentPreview(self) -> dict[str, object]:
        return self._document_preview

    @Property("QVariantMap", notify=documentLinksChanged)
    def documentLinks(self) -> dict[str, object]:
        return self._document_links

    @Property("QVariantMap", notify=documentStructuresChanged)
    def documentStructures(self) -> dict[str, object]:
        return self._document_structures

    @Property("QVariantMap", notify=organizationEditorOptionsChanged)
    def organizationEditorOptions(self) -> dict[str, object]:
        return self._organization_editor_options

    @Property("QVariantMap", notify=departmentEditorOptionsChanged)
    def departmentEditorOptions(self) -> dict[str, object]:
        return self._department_editor_options

    @Property("QVariantMap", notify=employeeEditorOptionsChanged)
    def employeeEditorOptions(self) -> dict[str, object]:
        return self._employee_editor_options

    @Property("QVariantMap", notify=userEditorOptionsChanged)
    def userEditorOptions(self) -> dict[str, object]:
        return self._user_editor_options

    @Property("QVariantMap", notify=partyEditorOptionsChanged)
    def partyEditorOptions(self) -> dict[str, object]:
        return self._party_editor_options

    @Property("QVariantMap", notify=documentEditorOptionsChanged)
    def documentEditorOptions(self) -> dict[str, object]:
        return self._document_editor_options

    @Property("QVariantMap", notify=documentStructureEditorOptionsChanged)
    def documentStructureEditorOptions(self) -> dict[str, object]:
        return self._document_structure_editor_options

    @Slot()
    def refresh(self) -> None:
        self._set_is_loading(True)
        self._set_error_message("")
        self._refresh_overview()
        self._refresh_organizations()
        self._refresh_sites()
        self._refresh_departments()
        self._refresh_employees()
        self._refresh_users()
        self._refresh_parties()
        self._refresh_documents()
        self._refresh_document_management()
        self._refresh_empty_state()
        self._set_is_loading(False)

    @Slot("QVariantMap", result="QVariantMap")
    def createOrganization(self, payload: dict[str, object]) -> dict[str, object]:
        return self._organization_controller.create_organization(
            payload,
            self._refresh_after_organization_change,
            self._set_is_busy,
            self._set_error_message,
            self._set_operation_result,
            self._set_feedback_message,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def updateOrganization(self, payload: dict[str, object]) -> dict[str, object]:
        return self._organization_controller.update_organization(
            payload,
            self._refresh_after_organization_change,
            self._set_is_busy,
            self._set_error_message,
            self._set_operation_result,
            self._set_feedback_message,
        )

    @Slot(str, result="QVariantMap")
    def setActiveOrganization(self, organization_id: str) -> dict[str, object]:
        return self._organization_controller.set_active_organization(
            organization_id,
            self._refresh_after_organization_change,
            self._set_is_busy,
            self._set_error_message,
            self._set_operation_result,
            self._set_feedback_message,
            self.operationResult,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def createSite(self, payload: dict[str, object]) -> dict[str, object]:
        return self._site_controller.create_site(
            payload,
            self._refresh_after_site_change,
            self._set_is_busy,
            self._set_error_message,
            self._set_operation_result,
            self._set_feedback_message,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def updateSite(self, payload: dict[str, object]) -> dict[str, object]:
        return self._site_controller.update_site(
            payload,
            self._refresh_after_site_change,
            self._set_is_busy,
            self._set_error_message,
            self._set_operation_result,
            self._set_feedback_message,
        )

    @Slot(str, result="QVariantMap")
    def toggleSiteActive(self, site_id: str) -> dict[str, object]:
        return self._site_controller.toggle_site_active(
            site_id,
            self._sites,
            self._refresh_after_site_change,
            self._set_is_busy,
            self._set_error_message,
            self._set_operation_result,
            self._set_feedback_message,
            self.operationResult,
            self._find_item_state,
            self._to_int,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def createDepartment(self, payload: dict[str, object]) -> dict[str, object]:
        return self._department_controller.create_department(
            payload,
            self._refresh_after_department_change,
            self._set_is_busy,
            self._set_error_message,
            self._set_operation_result,
            self._set_feedback_message,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def updateDepartment(self, payload: dict[str, object]) -> dict[str, object]:
        return self._department_controller.update_department(
            payload,
            self._refresh_after_department_change,
            self._set_is_busy,
            self._set_error_message,
            self._set_operation_result,
            self._set_feedback_message,
        )

    @Slot(str, result="QVariantMap")
    def toggleDepartmentActive(self, department_id: str) -> dict[str, object]:
        return self._department_controller.toggle_department_active(
            department_id,
            self._departments,
            self._refresh_after_department_change,
            self._set_is_busy,
            self._set_error_message,
            self._set_operation_result,
            self._set_feedback_message,
            self.operationResult,
            self._find_item_state,
            self._to_int,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def createEmployee(self, payload: dict[str, object]) -> dict[str, object]:
        return self._employee_controller.create_employee(
            payload,
            self._refresh_after_employee_change,
            self._set_is_busy,
            self._set_error_message,
            self._set_operation_result,
            self._set_feedback_message,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def updateEmployee(self, payload: dict[str, object]) -> dict[str, object]:
        return self._employee_controller.update_employee(
            payload,
            self._refresh_after_employee_change,
            self._set_is_busy,
            self._set_error_message,
            self._set_operation_result,
            self._set_feedback_message,
        )

    @Slot(str, result="QVariantMap")
    def toggleEmployeeActive(self, employee_id: str) -> dict[str, object]:
        return self._employee_controller.toggle_employee_active(
            employee_id,
            self._employees,
            self._refresh_after_employee_change,
            self._set_is_busy,
            self._set_error_message,
            self._set_operation_result,
            self._set_feedback_message,
            self.operationResult,
            self._find_item_state,
            self._to_int,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def createUser(self, payload: dict[str, object]) -> dict[str, object]:
        return self._user_controller.create_user(
            payload,
            self._refresh_after_user_change,
            self._set_is_busy,
            self._set_error_message,
            self._set_operation_result,
            self._set_feedback_message,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def updateUser(self, payload: dict[str, object]) -> dict[str, object]:
        return self._user_controller.update_user(
            payload,
            self._refresh_after_user_change,
            self._set_is_busy,
            self._set_error_message,
            self._set_operation_result,
            self._set_feedback_message,
        )

    @Slot(str, result="QVariantMap")
    def toggleUserActive(self, user_id: str) -> dict[str, object]:
        return self._user_controller.toggle_user_active(
            user_id,
            self._users,
            self._refresh_after_user_change,
            self._set_is_busy,
            self._set_error_message,
            self._set_operation_result,
            self._set_feedback_message,
            self.operationResult,
            self._find_item_state,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def createParty(self, payload: dict[str, object]) -> dict[str, object]:
        return self._party_controller.create_party(
            payload,
            self._refresh_after_party_change,
            self._set_is_busy,
            self._set_error_message,
            self._set_operation_result,
            self._set_feedback_message,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def updateParty(self, payload: dict[str, object]) -> dict[str, object]:
        return self._party_controller.update_party(
            payload,
            self._refresh_after_party_change,
            self._set_is_busy,
            self._set_error_message,
            self._set_operation_result,
            self._set_feedback_message,
        )

    @Slot(str, result="QVariantMap")
    def togglePartyActive(self, party_id: str) -> dict[str, object]:
        return self._party_controller.toggle_party_active(
            party_id,
            self._parties,
            self._refresh_after_party_change,
            self._set_is_busy,
            self._set_error_message,
            self._set_operation_result,
            self._set_feedback_message,
            self.operationResult,
            self._find_item_state,
            self._to_int,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def createDocument(self, payload: dict[str, object]) -> dict[str, object]:
        return self._document_controller.create_document(
            payload,
            self._refresh_after_document_change,
            self._set_is_busy,
            self._set_error_message,
            self._set_operation_result,
            self._set_feedback_message,
            self._select_document_from_result,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def updateDocument(self, payload: dict[str, object]) -> dict[str, object]:
        return self._document_controller.update_document(
            payload,
            self._refresh_after_document_change,
            self._set_is_busy,
            self._set_error_message,
            self._set_operation_result,
            self._set_feedback_message,
            self._select_document_from_result,
        )

    @Slot(str, result="QVariantMap")
    def toggleDocumentActive(self, document_id: str) -> dict[str, object]:
        return self._document_controller.toggle_document_active(
            document_id,
            self._documents,
            self._refresh_after_document_change,
            self._set_is_busy,
            self._set_error_message,
            self._set_operation_result,
            self._set_feedback_message,
            self.operationResult,
            self._find_item_state,
            self._to_int,
            self._select_document_from_result,
        )

    @Slot(str)
    def selectDocument(self, document_id: str) -> None:
        self._document_controller.select_document(
            document_id,
            lambda id: setattr(self, '_selected_document_id', id),
            self._refresh_document_focus,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def createDocumentStructure(self, payload: dict[str, object]) -> dict[str, object]:
        return self._document_structure_controller.create_document_structure(
            payload,
            self._refresh_after_document_structure_change,
            self._set_is_busy,
            self._set_error_message,
            self._set_operation_result,
            self._set_feedback_message,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def updateDocumentStructure(self, payload: dict[str, object]) -> dict[str, object]:
        return self._document_structure_controller.update_document_structure(
            payload,
            self._refresh_after_document_structure_change,
            self._set_is_busy,
            self._set_error_message,
            self._set_operation_result,
            self._set_feedback_message,
        )

    @Slot(str, result="QVariantMap")
    def toggleDocumentStructureActive(self, structure_id: str) -> dict[str, object]:
        return self._document_structure_controller.toggle_document_structure_active(
            structure_id,
            self._document_structures,
            self._refresh_after_document_structure_change,
            self._set_is_busy,
            self._set_error_message,
            self._set_operation_result,
            self._set_feedback_message,
            self.operationResult,
            self._find_item_state,
            self._to_int,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def addDocumentLink(self, payload: dict[str, object]) -> dict[str, object]:
        return self._document_structure_controller.add_document_link(
            payload,
            self._refresh_after_document_link_change,
            self._set_is_busy,
            self._set_error_message,
            self._set_operation_result,
            self._set_feedback_message,
        )

    @Slot(str, result="QVariantMap")
    def removeDocumentLink(self, link_id: str) -> dict[str, object]:
        return self._document_structure_controller.remove_document_link(
            link_id,
            self._refresh_after_document_link_change,
            self._set_is_busy,
            self._set_error_message,
            self._set_operation_result,
            self._set_feedback_message,
            self.operationResult,
        )

    def _run_mutation(
        self,
        *,
        operation: Callable[[], object],
        success_message: str,
        on_success: Callable[[], None],
        success_result_handler: Callable[[object], None] | None = None,
    ) -> dict[str, object]:
        return run_mutation(
            operation=operation,
            success_message=success_message,
            on_success=on_success,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_operation_result=self._set_operation_result,
            set_feedback_message=self._set_feedback_message,
            success_result_handler=success_result_handler,
        )

    def _refresh_after_organization_change(self) -> None:
        self._refresh_overview()
        self._refresh_organizations()
        self._refresh_sites()
        self._refresh_departments()
        self._refresh_employees()
        self._refresh_users()
        self._refresh_parties()
        self._refresh_documents()
        self._refresh_empty_state()

    def _refresh_after_site_change(self) -> None:
        self._refresh_overview()
        self._refresh_sites()
        self._refresh_departments()
        self._refresh_employees()
        self._refresh_documents()
        self._refresh_empty_state()

    def _refresh_after_department_change(self) -> None:
        self._refresh_overview()
        self._refresh_departments()
        self._refresh_employees()
        self._refresh_empty_state()

    def _refresh_after_employee_change(self) -> None:
        self._refresh_overview()
        self._refresh_employees()
        self._refresh_empty_state()

    def _refresh_after_user_change(self) -> None:
        self._refresh_overview()
        self._refresh_users()
        self._refresh_empty_state()

    def _refresh_after_party_change(self) -> None:
        self._refresh_overview()
        self._refresh_parties()
        self._refresh_empty_state()

    def _refresh_after_document_change(self) -> None:
        self._refresh_overview()
        self._refresh_documents()
        self._refresh_document_management()
        self._refresh_empty_state()

    def _refresh_after_document_structure_change(self) -> None:
        self._refresh_documents()
        self._refresh_document_management()
        self._refresh_empty_state()

    def _refresh_after_document_link_change(self) -> None:
        self._refresh_document_focus()
        self._refresh_empty_state()

    def _refresh_overview(self) -> None:
        self._set_overview(serialize_workspace_overview(self._overview_presenter.build_overview()))

    def _refresh_organizations(self) -> None:
        self._set_organizations(serialize_action_list(self._organization_presenter.build_catalog()))
        self._set_organization_editor_options(
            {
                "moduleOptions": list(self._organization_presenter.build_module_options()),
            }
        )

    def _refresh_sites(self) -> None:
        self._set_sites(serialize_action_list(self._site_presenter.build_catalog()))

    def _refresh_departments(self) -> None:
        catalog = serialize_action_list(self._department_presenter.build_catalog())
        self._set_departments(catalog)
        self._set_department_editor_options(
            {
                "siteOptions": list(self._department_presenter.build_site_options()),
                "locationOptions": list(self._department_presenter.build_location_options()),
                "parentOptions": list(self._department_presenter.build_parent_options()),
            }
        )

    def _refresh_employees(self) -> None:
        self._set_employees(serialize_action_list(self._employee_presenter.build_catalog()))
        self._set_employee_editor_options(
            {
                "siteOptions": list(self._employee_presenter.build_site_options()),
                "departmentOptions": list(self._employee_presenter.build_department_options()),
            }
        )

    def _refresh_users(self) -> None:
        self._set_users(serialize_action_list(self._user_presenter.build_catalog()))
        self._set_user_editor_options(
            {
                "roleOptions": list(self._user_presenter.build_role_options()),
            }
        )

    def _refresh_parties(self) -> None:
        self._set_parties(serialize_action_list(self._party_presenter.build_catalog()))
        self._set_party_editor_options(
            {
                "typeOptions": list(self._party_presenter.build_type_options()),
            }
        )

    def _refresh_documents(self) -> None:
        self._set_documents(serialize_action_list(self._document_presenter.build_catalog()))
        self._set_document_editor_options(
            {
                "typeOptions": list(self._document_presenter.build_type_options()),
                "structureOptions": list(self._document_presenter.build_structure_options()),
                "storageKindOptions": list(self._document_presenter.build_storage_kind_options()),
            }
        )

    def _refresh_document_management(self) -> None:
        self._refresh_document_structures()
        self._refresh_document_focus()

    def _refresh_document_structures(self) -> None:
        catalog, editor_options = self._document_management_presenter.build_structure_management()
        self._set_document_structures(serialize_action_list(catalog))
        self._set_document_structure_editor_options(editor_options)

    def _refresh_document_focus(self) -> None:
        selected_document_id, detail, preview, links = self._document_management_presenter.build_document_focus(
            self._selected_document_id
        )
        self._selected_document_id = selected_document_id
        self._set_selected_document(detail)
        self._set_document_preview(preview)
        self._set_document_links(serialize_action_list(links))

    def _refresh_empty_state(self) -> None:
        has_items = any(
            catalog.get("items")
            for catalog in (
                self._organizations,
                self._sites,
                self._departments,
                self._employees,
                self._users,
                self._parties,
                self._documents,
            )
        )
        self._set_empty_state("" if has_items else "No platform administration records are available yet.")

    def _set_organizations(self, organizations: dict[str, object]) -> None:
        if organizations == self._organizations:
            return
        self._organizations = organizations
        self.organizationsChanged.emit()

    def _set_sites(self, sites: dict[str, object]) -> None:
        if sites == self._sites:
            return
        self._sites = sites
        self.sitesChanged.emit()

    def _set_departments(self, departments: dict[str, object]) -> None:
        if departments == self._departments:
            return
        self._departments = departments
        self.departmentsChanged.emit()

    def _set_employees(self, employees: dict[str, object]) -> None:
        if employees == self._employees:
            return
        self._employees = employees
        self.employeesChanged.emit()

    def _set_users(self, users: dict[str, object]) -> None:
        if users == self._users:
            return
        self._users = users
        self.usersChanged.emit()

    def _set_parties(self, parties: dict[str, object]) -> None:
        if parties == self._parties:
            return
        self._parties = parties
        self.partiesChanged.emit()

    def _set_documents(self, documents: dict[str, object]) -> None:
        if documents == self._documents:
            return
        self._documents = documents
        self.documentsChanged.emit()

    def _set_selected_document(self, selected_document: dict[str, object]) -> None:
        if selected_document == self._selected_document:
            return
        self._selected_document = selected_document
        self.selectedDocumentChanged.emit()

    def _set_document_preview(self, preview: dict[str, object]) -> None:
        if preview == self._document_preview:
            return
        self._document_preview = preview
        self.documentPreviewChanged.emit()

    def _set_document_links(self, links: dict[str, object]) -> None:
        if links == self._document_links:
            return
        self._document_links = links
        self.documentLinksChanged.emit()

    def _set_document_structures(self, structures: dict[str, object]) -> None:
        if structures == self._document_structures:
            return
        self._document_structures = structures
        self.documentStructuresChanged.emit()

    def _set_organization_editor_options(self, options: dict[str, object]) -> None:
        if options == self._organization_editor_options:
            return
        self._organization_editor_options = options
        self.organizationEditorOptionsChanged.emit()

    def _set_department_editor_options(self, options: dict[str, object]) -> None:
        if options == self._department_editor_options:
            return
        self._department_editor_options = options
        self.departmentEditorOptionsChanged.emit()

    def _set_employee_editor_options(self, options: dict[str, object]) -> None:
        if options == self._employee_editor_options:
            return
        self._employee_editor_options = options
        self.employeeEditorOptionsChanged.emit()

    def _set_user_editor_options(self, options: dict[str, object]) -> None:
        if options == self._user_editor_options:
            return
        self._user_editor_options = options
        self.userEditorOptionsChanged.emit()

    def _set_party_editor_options(self, options: dict[str, object]) -> None:
        if options == self._party_editor_options:
            return
        self._party_editor_options = options
        self.partyEditorOptionsChanged.emit()

    def _set_document_editor_options(self, options: dict[str, object]) -> None:
        if options == self._document_editor_options:
            return
        self._document_editor_options = options
        self.documentEditorOptionsChanged.emit()

    def _set_document_structure_editor_options(self, options: dict[str, object]) -> None:
        if options == self._document_structure_editor_options:
            return
        self._document_structure_editor_options = options
        self.documentStructureEditorOptionsChanged.emit()

    def _select_document_from_result(self, result: object) -> None:
        data = getattr(result, "data", None)
        document_id = str(getattr(data, "id", "") or "").strip()
        if document_id:
            self._selected_document_id = document_id

    @staticmethod
    def _find_item_state(catalog: dict[str, object], item_id: str) -> dict[str, Any] | None:
        normalized_id = item_id.strip()
        if not normalized_id:
            return None
        for item in catalog.get("items", []):
            if item.get("id") == normalized_id:
                return dict(item.get("state") or {})
        return None

    @staticmethod
    def _to_int(value: object) -> int | None:
        if value in {None, ""}:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None


__all__ = ["PlatformAdminWorkspaceController"]

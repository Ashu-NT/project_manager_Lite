from __future__ import annotations

from typing import Any, Callable

from PySide6.QtCore import Property, QObject, Signal, Slot

from src.ui_qml.platform.presenters.admin_presenter import PlatformAdminWorkspacePresenter
from src.ui_qml.platform.presenters.department_catalog_presenter import PlatformDepartmentCatalogPresenter
from src.ui_qml.platform.presenters.document_catalog_presenter import PlatformDocumentCatalogPresenter
from src.ui_qml.platform.presenters.employee_catalog_presenter import PlatformEmployeeCatalogPresenter
from src.ui_qml.platform.presenters.organization_catalog_presenter import (
    PlatformOrganizationCatalogPresenter,
)
from src.ui_qml.platform.presenters.party_catalog_presenter import PlatformPartyCatalogPresenter
from src.ui_qml.platform.presenters.site_catalog_presenter import PlatformSiteCatalogPresenter
from src.ui_qml.platform.presenters.user_catalog_presenter import PlatformUserCatalogPresenter
from src.ui_qml.platform.workspace_state import (
    PlatformWorkspaceControllerBase,
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
    organizationEditorOptionsChanged = Signal()
    departmentEditorOptionsChanged = Signal()
    employeeEditorOptionsChanged = Signal()
    userEditorOptionsChanged = Signal()
    partyEditorOptionsChanged = Signal()
    documentEditorOptionsChanged = Signal()

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
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._overview_presenter = overview_presenter
        self._organization_presenter = organization_presenter
        self._site_presenter = site_presenter
        self._department_presenter = department_presenter
        self._employee_presenter = employee_presenter
        self._user_presenter = user_presenter
        self._party_presenter = party_presenter
        self._document_presenter = document_presenter
        self._organizations: dict[str, object] = {"title": "", "subtitle": "", "emptyState": "", "items": []}
        self._sites: dict[str, object] = {"title": "", "subtitle": "", "emptyState": "", "items": []}
        self._departments: dict[str, object] = {"title": "", "subtitle": "", "emptyState": "", "items": []}
        self._employees: dict[str, object] = {"title": "", "subtitle": "", "emptyState": "", "items": []}
        self._users: dict[str, object] = {"title": "", "subtitle": "", "emptyState": "", "items": []}
        self._parties: dict[str, object] = {"title": "", "subtitle": "", "emptyState": "", "items": []}
        self._documents: dict[str, object] = {"title": "", "subtitle": "", "emptyState": "", "items": []}
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
        self._refresh_empty_state()
        self._set_is_loading(False)

    @Slot("QVariantMap", result="QVariantMap")
    def createOrganization(self, payload: dict[str, object]) -> dict[str, object]:
        return self._run_mutation(
            operation=lambda: self._organization_presenter.create_organization(dict(payload)),
            success_message="Organization created.",
            on_success=self._refresh_after_organization_change,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def updateOrganization(self, payload: dict[str, object]) -> dict[str, object]:
        return self._run_mutation(
            operation=lambda: self._organization_presenter.update_organization(dict(payload)),
            success_message="Organization updated.",
            on_success=self._refresh_after_organization_change,
        )

    @Slot(str, result="QVariantMap")
    def setActiveOrganization(self, organization_id: str) -> dict[str, object]:
        normalized_id = organization_id.strip()
        if not normalized_id:
            return dict(self.operationResult)
        return self._run_mutation(
            operation=lambda: self._organization_presenter.set_active_organization(normalized_id),
            success_message="Organization activated.",
            on_success=self._refresh_after_organization_change,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def createSite(self, payload: dict[str, object]) -> dict[str, object]:
        return self._run_mutation(
            operation=lambda: self._site_presenter.create_site(dict(payload)),
            success_message="Site created.",
            on_success=self._refresh_after_site_change,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def updateSite(self, payload: dict[str, object]) -> dict[str, object]:
        return self._run_mutation(
            operation=lambda: self._site_presenter.update_site(dict(payload)),
            success_message="Site updated.",
            on_success=self._refresh_after_site_change,
        )

    @Slot(str, result="QVariantMap")
    def toggleSiteActive(self, site_id: str) -> dict[str, object]:
        state = self._find_item_state(self._sites, site_id)
        if state is None:
            return dict(self.operationResult)
        return self._run_mutation(
            operation=lambda: self._site_presenter.toggle_site_active(
                site_id=site_id,
                is_active=bool(state.get("isActive")),
                expected_version=self._to_int(state.get("version")),
            ),
            success_message="Site active state updated.",
            on_success=self._refresh_after_site_change,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def createDepartment(self, payload: dict[str, object]) -> dict[str, object]:
        return self._run_mutation(
            operation=lambda: self._department_presenter.create_department(dict(payload)),
            success_message="Department created.",
            on_success=self._refresh_after_department_change,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def updateDepartment(self, payload: dict[str, object]) -> dict[str, object]:
        return self._run_mutation(
            operation=lambda: self._department_presenter.update_department(dict(payload)),
            success_message="Department updated.",
            on_success=self._refresh_after_department_change,
        )

    @Slot(str, result="QVariantMap")
    def toggleDepartmentActive(self, department_id: str) -> dict[str, object]:
        state = self._find_item_state(self._departments, department_id)
        if state is None:
            return dict(self.operationResult)
        return self._run_mutation(
            operation=lambda: self._department_presenter.toggle_department_active(
                department_id=department_id,
                is_active=bool(state.get("isActive")),
                expected_version=self._to_int(state.get("version")),
            ),
            success_message="Department active state updated.",
            on_success=self._refresh_after_department_change,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def createEmployee(self, payload: dict[str, object]) -> dict[str, object]:
        return self._run_mutation(
            operation=lambda: self._employee_presenter.create_employee(dict(payload)),
            success_message="Employee created.",
            on_success=self._refresh_after_employee_change,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def updateEmployee(self, payload: dict[str, object]) -> dict[str, object]:
        return self._run_mutation(
            operation=lambda: self._employee_presenter.update_employee(dict(payload)),
            success_message="Employee updated.",
            on_success=self._refresh_after_employee_change,
        )

    @Slot(str, result="QVariantMap")
    def toggleEmployeeActive(self, employee_id: str) -> dict[str, object]:
        state = self._find_item_state(self._employees, employee_id)
        if state is None:
            return dict(self.operationResult)
        return self._run_mutation(
            operation=lambda: self._employee_presenter.toggle_employee_active(
                employee_id=employee_id,
                is_active=bool(state.get("isActive")),
                expected_version=self._to_int(state.get("version")),
            ),
            success_message="Employee active state updated.",
            on_success=self._refresh_after_employee_change,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def createUser(self, payload: dict[str, object]) -> dict[str, object]:
        return self._run_mutation(
            operation=lambda: self._user_presenter.create_user(dict(payload)),
            success_message="User created.",
            on_success=self._refresh_after_user_change,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def updateUser(self, payload: dict[str, object]) -> dict[str, object]:
        return self._run_mutation(
            operation=lambda: self._user_presenter.update_user(dict(payload)),
            success_message="User updated.",
            on_success=self._refresh_after_user_change,
        )

    @Slot(str, result="QVariantMap")
    def toggleUserActive(self, user_id: str) -> dict[str, object]:
        state = self._find_item_state(self._users, user_id)
        if state is None:
            return dict(self.operationResult)
        return self._run_mutation(
            operation=lambda: self._user_presenter.toggle_user_active(
                user_id=user_id,
                is_active=bool(state.get("isActive")),
            ),
            success_message="User active state updated.",
            on_success=self._refresh_after_user_change,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def createParty(self, payload: dict[str, object]) -> dict[str, object]:
        return self._run_mutation(
            operation=lambda: self._party_presenter.create_party(dict(payload)),
            success_message="Party created.",
            on_success=self._refresh_after_party_change,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def updateParty(self, payload: dict[str, object]) -> dict[str, object]:
        return self._run_mutation(
            operation=lambda: self._party_presenter.update_party(dict(payload)),
            success_message="Party updated.",
            on_success=self._refresh_after_party_change,
        )

    @Slot(str, result="QVariantMap")
    def togglePartyActive(self, party_id: str) -> dict[str, object]:
        state = self._find_item_state(self._parties, party_id)
        if state is None:
            return dict(self.operationResult)
        return self._run_mutation(
            operation=lambda: self._party_presenter.toggle_party_active(
                party_id=party_id,
                is_active=bool(state.get("isActive")),
                expected_version=self._to_int(state.get("version")),
            ),
            success_message="Party active state updated.",
            on_success=self._refresh_after_party_change,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def createDocument(self, payload: dict[str, object]) -> dict[str, object]:
        return self._run_mutation(
            operation=lambda: self._document_presenter.create_document(dict(payload)),
            success_message="Document created.",
            on_success=self._refresh_after_document_change,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def updateDocument(self, payload: dict[str, object]) -> dict[str, object]:
        return self._run_mutation(
            operation=lambda: self._document_presenter.update_document(dict(payload)),
            success_message="Document updated.",
            on_success=self._refresh_after_document_change,
        )

    @Slot(str, result="QVariantMap")
    def toggleDocumentActive(self, document_id: str) -> dict[str, object]:
        state = self._find_item_state(self._documents, document_id)
        if state is None:
            return dict(self.operationResult)
        return self._run_mutation(
            operation=lambda: self._document_presenter.toggle_document_active(
                document_id=document_id,
                is_active=bool(state.get("isActive")),
                expected_version=self._to_int(state.get("version")),
            ),
            success_message="Document active state updated.",
            on_success=self._refresh_after_document_change,
        )

    def _run_mutation(
        self,
        *,
        operation: Callable[[], object],
        success_message: str,
        on_success: Callable[[], None],
    ) -> dict[str, object]:
        self._set_is_busy(True)
        self._set_error_message("")
        result = operation()
        payload = serialize_operation_result(result, success_message=success_message)
        self._set_operation_result(payload)
        if payload["ok"]:
            self._set_feedback_message(str(payload["message"]))
            on_success()
        else:
            self._set_feedback_message("")
            self._set_error_message(str(payload["message"]))
        self._set_is_busy(False)
        return dict(self.operationResult)

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

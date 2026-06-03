from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Property, QObject, Signal, Slot
from PySide6.QtQml import QmlElement, QmlUncreatable

from src.core.shared.events.domain_events import domain_events
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

from .department_controller import PlatformDepartmentController
from .document_controller import PlatformDocumentController
from .document_structure_controller import PlatformDocumentStructureController
from .employee_controller import PlatformEmployeeController
from .calendar_controller import PlatformCalendarController
from .organization_controller import PlatformOrganizationController
from .party_controller import PlatformPartyController
from .site_controller import PlatformSiteController
from .user_controller import PlatformUserController
from ..common import (
    PlatformWorkspaceControllerBase,
    serialize_operation_result,
    serialize_workspace_overview,
)

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

    # ── Python-owned table models (sourceModel path) ──────────────────

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

    @Slot()
    def refresh(self) -> None:
        self._set_is_loading(True)
        self._set_error_message("")
        self._refresh_overview()
        self._organization_controller.refresh()
        self._calendar_controller.refresh()
        self._site_controller.refresh()
        self._department_controller.refresh()
        self._employee_controller.refresh()
        self._user_controller.refresh()
        self._party_controller.refresh()
        self._document_controller.refresh()
        self._document_structure_controller.refresh()
        self._refresh_empty_state()
        self._set_is_loading(False)

    @Slot(str, "QVariantMap", result=str)
    def generateEntityCode(self, entity_type: str, payload: dict[str, object]) -> str:
        """Suggest a unique code for an admin entity editor dialog.

        Generic dispatch by entity type so a single slot serves every admin
        dialog. Returns "" if the entity type has no generator wired yet.
        """
        key = (entity_type or "").strip().lower()
        generators = {
            "organization": self._organization_controller.generateCode,
            "site": self._site_controller.generateCode,
            "department": self._department_controller.generateCode,
            "employee": self._employee_controller.generateCode,
            "party": self._party_controller.generateCode,
            "document": self._document_controller.generateCode,
            "document_structure": self._document_structure_controller.generateCode,
        }
        handler = generators.get(key)
        if handler is None:
            return ""
        return handler(dict(payload))

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
    def updateCalendar(self, payload: dict[str, object]) -> dict[str, object]:
        return self._run_admin_result_action(
            operation=lambda: self._calendar_controller.updateCalendar(dict(payload)),
            success_message="Working calendar updated.",
            on_success=self._refresh_after_calendar_change,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def addCalendarHoliday(self, payload: dict[str, object]) -> dict[str, object]:
        return self._run_admin_result_action(
            operation=lambda: self._calendar_controller.addCalendarHoliday(dict(payload)),
            success_message="Calendar exception added.",
            on_success=self._refresh_after_calendar_change,
        )

    @Slot(str, result="QVariantMap")
    def deleteCalendarHoliday(self, holiday_id: str) -> dict[str, object]:
        return self._run_admin_result_action(
            operation=lambda: self._calendar_controller.deleteCalendarHoliday(holiday_id),
            success_message="Calendar exception removed.",
            on_success=self._refresh_after_calendar_change,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def calculateCalendarWorkingDays(self, payload: dict[str, object]) -> dict[str, object]:
        self._set_is_busy(True)
        self._set_error_message("")
        try:
            result = self._calendar_controller.calculateCalendarWorkingDays(dict(payload))
            if result is not None and getattr(result, "ok", False) and getattr(result, "data", None) is not None:
                message = self._calendar_controller.formatCalculationResult(result.data)
                payload_map = {
                    "ok": True,
                    "category": "",
                    "code": "",
                    "message": message,
                }
                self._set_feedback_message("")
                self._set_operation_result(payload_map)
                return dict(payload_map)
            payload_map = serialize_operation_result(
                result,
                success_message="Working-day calculation completed.",
            )
            self._set_feedback_message("")
            self._set_error_message(str(payload_map.get("message", "")))
            self._set_operation_result(payload_map)
            return dict(payload_map)
        finally:
            self._set_is_busy(False)

    @Slot("QVariantMap", result="QVariantMap")
    def createEnterpriseCalendar(self, payload: dict[str, object]) -> dict[str, object]:
        return self._run_admin_result_action(
            operation=lambda: self._enterprise_calendar_api.create_calendar(
                self._build_calendar_create_command(payload)
            ) if self._enterprise_calendar_api else None,
            success_message="Calendar created.",
            on_success=self._refresh_after_calendar_change,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def updateEnterpriseCalendar(self, payload: dict[str, object]) -> dict[str, object]:
        return self._run_admin_result_action(
            operation=lambda: self._enterprise_calendar_api.update_calendar(
                self._build_calendar_update_command(payload)
            ) if self._enterprise_calendar_api else None,
            success_message="Calendar updated.",
            on_success=self._refresh_after_calendar_change,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def addCalendarException(self, payload: dict[str, object]) -> dict[str, object]:
        return self._run_admin_result_action(
            operation=lambda: self._enterprise_calendar_api.add_exception(
                self._build_exception_create_command(payload)
            ) if self._enterprise_calendar_api else None,
            success_message="Calendar exception added.",
            on_success=self._refresh_after_calendar_change,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def addCalendarRecurringEvent(self, payload: dict[str, object]) -> dict[str, object]:
        return self._run_admin_result_action(
            operation=lambda: self._enterprise_calendar_api.add_recurring_event(
                self._build_recurring_event_create_command(payload)
            ) if self._enterprise_calendar_api else None,
            success_message="Recurring event added.",
            on_success=self._refresh_after_calendar_change,
        )

    @Slot(str, result="QVariantMap")
    def deleteCalendarException(self, exception_id: str) -> dict[str, object]:
        return self._run_admin_result_action(
            operation=lambda: self._enterprise_calendar_api.delete_exception(exception_id)
            if self._enterprise_calendar_api
            else None,
            success_message="Calendar exception removed.",
            on_success=self._refresh_after_calendar_change,
        )

    @Slot(str, result="QVariantMap")
    def deleteCalendarRecurringEvent(self, event_id: str) -> dict[str, object]:
        return self._run_admin_result_action(
            operation=lambda: self._enterprise_calendar_api.delete_recurring_event(event_id)
            if self._enterprise_calendar_api
            else None,
            success_message="Recurring event removed.",
            on_success=self._refresh_after_calendar_change,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def assignCalendar(self, payload: dict[str, object]) -> dict[str, object]:
        entity_type = str(payload.get("entityType", "")).lower()
        return self._run_admin_result_action(
            operation=lambda: self._dispatch_calendar_assign(payload, entity_type),
            success_message="Calendar assigned.",
            on_success=self._refresh_after_calendar_change,
        )

    @Slot(str, str, result="QVariantMap")
    def removeCalendarAssignment(
        self, assignment_id: str, entity_type: str
    ) -> dict[str, object]:
        return self._run_admin_result_action(
            operation=lambda: self._enterprise_calendar_api.remove_assignment(
                assignment_id,
                entity_type,
            )
            if self._enterprise_calendar_api
            else None,
            success_message="Calendar assignment removed.",
            on_success=self._refresh_after_calendar_change,
        )

    @Slot(str, result="QVariantMap")
    def calendarDetailContext(self, calendar_id: str) -> dict[str, object]:
        if self._enterprise_calendar_api is None or not str(calendar_id or "").strip():
            return self._empty_calendar_detail_context()

        calendar_id = str(calendar_id).strip()
        rules_result = self._enterprise_calendar_api.list_working_rules(calendar_id)
        exceptions_result = self._enterprise_calendar_api.list_exceptions(calendar_id)
        recurring_result = self._enterprise_calendar_api.list_recurring_events(
            calendar_id,
            active_only=False,
        )
        assignments_result = self._enterprise_calendar_api.list_calendar_assignments(
            calendar_id
        )

        return {
            "workingRules": [
                self._serialize_working_rule(rule)
                for rule in self._result_sequence(rules_result)
            ],
            "exceptions": [
                self._serialize_calendar_exception(exception)
                for exception in self._result_sequence(exceptions_result)
            ],
            "recurringEvents": [
                self._serialize_recurring_event(event)
                for event in self._result_sequence(recurring_result)
            ],
            "assignments": self._serialize_assignment_groups(
                assignments_result.data
                if getattr(assignments_result, "ok", False)
                and getattr(assignments_result, "data", None) is not None
                else {}
            ),
        }

    @Slot(str, str, str, str, result="QVariantMap")
    def calendarAssignmentContext(
        self,
        entity_type: str,
        entity_id: str,
        site_id: str = "",
        department_id: str = "",
    ) -> dict[str, object]:
        if self._enterprise_calendar_api is None or not str(entity_id or "").strip():
            return self._empty_calendar_assignment_context()

        normalized_type = str(entity_type or "").strip().lower()
        normalized_id = str(entity_id or "").strip()
        assignment_result = None
        if normalized_type == "site":
            assignment_result = self._enterprise_calendar_api.list_site_calendar_assignments(
                normalized_id
            )
            site_id = normalized_id
        elif normalized_type == "department":
            assignment_result = (
                self._enterprise_calendar_api.list_department_calendar_assignments(
                    normalized_id
                )
            )
            department_id = normalized_id
        elif normalized_type == "employee":
            assignment_result = (
                self._enterprise_calendar_api.list_employee_calendar_assignments(
                    normalized_id
                )
            )
        else:
            return self._empty_calendar_assignment_context()

        assignments = self._result_sequence(assignment_result)
        selected_assignment = assignments[0] if assignments else None
        source_chain = self._calendar_source_chain(
            normalized_type=normalized_type,
            entity_id=normalized_id,
            site_id=site_id,
            department_id=department_id,
        )
        return {
            "assignedCalendar": self._serialize_calendar_assignment(selected_assignment),
            "sourceChain": source_chain,
        }

    def _dispatch_calendar_assign(self, payload: dict, entity_type: str):
        if self._enterprise_calendar_api is None:
            return None
        from src.api.desktop.platform.models.enterprise_calendar import (
            SiteCalendarAssignCommand,
            DeptCalendarAssignCommand,
            EmpCalendarAssignCommand,
            ProjectCalendarAssignCommand,
            ResourceCalendarAssignCommand,
        )
        cal_id = str(payload.get("calendarId", ""))
        eff_from = str(payload.get("effectiveFrom", ""))
        eff_to = str(payload.get("effectiveTo", ""))
        entity_id = str(payload.get("entityId", ""))
        if entity_type == "site":
            return self._enterprise_calendar_api.assign_site_calendar(
                SiteCalendarAssignCommand(site_id=entity_id, calendar_id=cal_id, effective_from=eff_from, effective_to=eff_to)
            )
        if entity_type == "department":
            return self._enterprise_calendar_api.assign_department_calendar(
                DeptCalendarAssignCommand(department_id=entity_id, calendar_id=cal_id, effective_from=eff_from, effective_to=eff_to)
            )
        if entity_type == "employee":
            return self._enterprise_calendar_api.assign_employee_calendar(
                EmpCalendarAssignCommand(employee_id=entity_id, calendar_id=cal_id, effective_from=eff_from, effective_to=eff_to)
            )
        if entity_type == "project":
            return self._enterprise_calendar_api.assign_project_calendar(
                ProjectCalendarAssignCommand(project_id=entity_id, calendar_id=cal_id, effective_from=eff_from, effective_to=eff_to)
            )
        if entity_type == "resource":
            return self._enterprise_calendar_api.assign_resource_calendar(
                ResourceCalendarAssignCommand(resource_id=entity_id, calendar_id=cal_id, effective_from=eff_from, effective_to=eff_to)
            )
        return None

    @staticmethod
    def _empty_calendar_detail_context() -> dict[str, object]:
        return {
            "workingRules": [],
            "exceptions": [],
            "recurringEvents": [],
            "assignments": {
                "sites": [],
                "departments": [],
                "employees": [],
                "projects": [],
                "resources": [],
            },
        }

    @staticmethod
    def _empty_calendar_assignment_context() -> dict[str, object]:
        return {
            "assignedCalendar": {},
            "sourceChain": [],
        }

    @staticmethod
    def _result_sequence(result) -> list[object]:
        if (
            result is None
            or not getattr(result, "ok", False)
            or getattr(result, "data", None) is None
        ):
            return []
        data = result.data
        if isinstance(data, (list, tuple)):
            return list(data)
        return []

    def _calendar_source_chain(
        self,
        *,
        normalized_type: str,
        entity_id: str,
        site_id: str,
        department_id: str,
    ) -> list[str]:
        if self._enterprise_calendar_api is None:
            return []
        result = self._enterprise_calendar_api.get_source_chain(
            site_id=entity_id if normalized_type == "site" else str(site_id or ""),
            department_id=entity_id
            if normalized_type == "department"
            else str(department_id or ""),
            employee_id=entity_id if normalized_type == "employee" else "",
        )
        if (
            result is None
            or not getattr(result, "ok", False)
            or getattr(result, "data", None) is None
        ):
            return []
        return [str(item) for item in result.data]

    @staticmethod
    def _serialize_calendar_assignment(assignment) -> dict[str, object]:
        if assignment is None:
            return {}
        return {
            "assignmentId": str(getattr(assignment, "id", "") or ""),
            "entityType": str(getattr(assignment, "entity_type", "") or ""),
            "entityId": str(getattr(assignment, "entity_id", "") or ""),
            "calendarId": str(getattr(assignment, "calendar_id", "") or ""),
            "calendarName": str(getattr(assignment, "calendar_name", "") or ""),
            "calendarType": str(getattr(assignment, "calendar_type", "") or ""),
            "isDefault": bool(getattr(assignment, "is_default", False)),
            "priority": int(getattr(assignment, "priority", 0) or 0),
            "effectiveFrom": str(getattr(assignment, "effective_from", "") or ""),
            "effectiveTo": str(getattr(assignment, "effective_to", "") or ""),
        }

    def _serialize_assignment_groups(self, assignments: object) -> dict[str, object]:
        if not isinstance(assignments, dict):
            return self._empty_calendar_detail_context()["assignments"]
        return {
            "sites": [
                self._serialize_calendar_assignment(item)
                for item in assignments.get("sites", ())
            ],
            "departments": [
                self._serialize_calendar_assignment(item)
                for item in assignments.get("departments", ())
            ],
            "employees": [
                self._serialize_calendar_assignment(item)
                for item in assignments.get("employees", ())
            ],
            "projects": [
                self._serialize_calendar_assignment(item)
                for item in assignments.get("projects", ())
            ],
            "resources": [
                self._serialize_calendar_assignment(item)
                for item in assignments.get("resources", ())
            ],
        }

    @staticmethod
    def _serialize_working_rule(rule) -> dict[str, object]:
        return {
            "id": str(getattr(rule, "id", "") or ""),
            "weekday": int(getattr(rule, "weekday", 0) or 0),
            "isWorkingDay": bool(getattr(rule, "is_working_day", False)),
            "startTime": str(getattr(rule, "start_time", "") or ""),
            "endTime": str(getattr(rule, "end_time", "") or ""),
            "breakMinutes": int(getattr(rule, "break_minutes", 0) or 0),
            "computedHours": float(getattr(rule, "computed_hours", 0.0) or 0.0),
        }

    @staticmethod
    def _serialize_calendar_exception(exception) -> dict[str, object]:
        return {
            "id": str(getattr(exception, "id", "") or ""),
            "exceptionDate": str(getattr(exception, "exception_date", "") or ""),
            "exceptionType": str(getattr(exception, "exception_type", "") or ""),
            "name": str(getattr(exception, "name", "") or ""),
            "impactType": str(getattr(exception, "impact_type", "") or ""),
            "approvalStatus": str(getattr(exception, "approval_status", "") or ""),
        }

    @staticmethod
    def _serialize_recurring_event(event) -> dict[str, object]:
        return {
            "id": str(getattr(event, "id", "") or ""),
            "title": str(getattr(event, "title", "") or ""),
            "eventType": str(getattr(event, "event_type", "") or ""),
            "recurrenceRule": str(getattr(event, "recurrence_rule", "") or ""),
            "impactType": str(getattr(event, "impact_type", "") or ""),
            "isActive": bool(getattr(event, "is_active", False)),
        }

    def _build_calendar_create_command(self, payload: dict):
        from src.api.desktop.platform.models.enterprise_calendar import CalendarCreateCommand
        return CalendarCreateCommand(
            code=str(payload.get("code", "")),
            name=str(payload.get("name", "")),
            calendar_type=str(payload.get("calendarType", "GLOBAL")),
            timezone=str(payload.get("timezone", "UTC")),
            description=str(payload.get("description", "")),
            is_default=bool(payload.get("isDefault", False)),
        )

    def _build_calendar_update_command(self, payload: dict):
        from src.api.desktop.platform.models.enterprise_calendar import CalendarUpdateCommand
        return CalendarUpdateCommand(
            calendar_id=str(payload.get("calendarId", "")),
            name=str(payload.get("name", "")),
            timezone=str(payload.get("timezone", "")),
            description=str(payload.get("description", "")),
        )

    def _build_exception_create_command(self, payload: dict):
        from src.api.desktop.platform.models.enterprise_calendar import ExceptionCreateCommand
        return ExceptionCreateCommand(
            calendar_id=str(payload.get("calendarId", "")),
            exception_date=str(payload.get("exceptionDate", "")),
            exception_type=str(payload.get("exceptionType", "HOLIDAY")),
            name=str(payload.get("name", "")),
            impact_type=str(payload.get("impactType", "UNAVAILABLE")),
            description=str(payload.get("description", "")),
            hours_override=float(payload.get("hoursOverride", 0.0) or 0.0),
        )

    def _build_recurring_event_create_command(self, payload: dict):
        from src.api.desktop.platform.models.enterprise_calendar import RecurringEventCreateCommand
        return RecurringEventCreateCommand(
            calendar_id=str(payload.get("calendarId", "")),
            title=str(payload.get("title", "")),
            event_type=str(payload.get("eventType", "MEETING")),
            recurrence_rule=str(payload.get("recurrenceRule", "")),
            start_time=str(payload.get("startTime", "")),
            end_time=str(payload.get("endTime", "")),
            impact_type=str(payload.get("impactType", "UNAVAILABLE")),
            effective_from=str(payload.get("effectiveFrom", "")),
            effective_to=str(payload.get("effectiveTo", "")),
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
            domain_events.calendars_changed,
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
        self._calendar_controller.calendarsChanged.connect(self.calendarsChanged.emit)
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

    def _run_admin_result_action(
        self,
        *,
        operation,
        success_message: str,
        on_success: Callable[[], None],
    ) -> dict[str, object]:
        self._set_is_busy(True)
        self._set_error_message("")
        try:
            result = operation()
            payload = serialize_operation_result(result, success_message=success_message)
            self._set_operation_result(payload)
            if payload.get("ok"):
                self._set_feedback_message(str(payload.get("message", "")))
                on_success()
            else:
                self._set_feedback_message("")
                self._set_error_message(str(payload.get("message", "")))
            return dict(payload)
        finally:
            self._set_is_busy(False)

    def _refresh_after_organization_change(self) -> None:
        self._refresh_overview()
        self._calendar_controller.refresh()
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

    def _refresh_after_calendar_change(self) -> None:
        self._calendar_controller.refresh()
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
                self.calendars,
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

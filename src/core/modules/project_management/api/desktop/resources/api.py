from __future__ import annotations

from src.core.modules.project_management.api.desktop.resources.builders.availability_builder import (
    build_resource_availability,
)
from src.core.modules.project_management.api.desktop.resources.builders.employee_option_builder import (
    build_employee_lookup,
    build_employee_options,
)
from src.core.modules.project_management.api.desktop.resources.builders.option_builder import (
    build_category_options,
    build_department_options,
    build_kind_options,
    build_site_options,
    build_worker_type_options,
)
from src.core.modules.project_management.api.desktop.resources.commands.certification_commands import (
    ResourceAddCertificationCommand,
    ResourceRemoveCertificationCommand,
    ResourceUpdateCertificationCommand,
)
from src.core.modules.project_management.api.desktop.resources.commands.resource_commands import (
    ResourceCreateCommand,
    ResourceLifecycleCommand,
    ResourcePurgeCommand,
    ResourceUpdateCommand,
)
from src.core.modules.project_management.api.desktop.resources.commands.skill_commands import (
    ResourceAddSkillCommand,
    ResourceRemoveSkillCommand,
    ResourceUpdateSkillCommand,
)
from src.core.modules.project_management.api.desktop.resources.models.context import (
    ResourceActivityPageDesktopDto,
    ResourceAssignmentDesktopDto,
    ResourceAssignmentsPageDesktopDto,
    ResourceProjectsPageDesktopDto,
)
from src.core.modules.project_management.api.desktop.resources.models.availability import (
    ResourceAvailabilityDto,
)
from src.core.modules.project_management.api.desktop.resources.models.certifications import (
    ResourceCertificationDesktopDto,
    ResourceCertificationsPageDesktopDto,
)
from src.core.modules.project_management.api.desktop.resources.models.options import (
    ResourceCategoryDescriptor,
    ResourceEmployeeOptionDescriptor,
    ResourceKindDescriptor,
    ResourceScopeOptionDescriptor,
    ResourceWorkerTypeDescriptor,
)
from src.core.modules.project_management.api.desktop.resources.models.resources import (
    ResourceCatalogPageDesktopDto,
    ResourceDesktopDto,
    ResourceInspectorDesktopDto,
    ResourceSummaryDesktopDto,
)
from src.core.modules.project_management.api.desktop.resources.models.skills import (
    ResourceSkillDesktopDto,
    ResourceSkillsPageDesktopDto,
)
from src.core.modules.project_management.api.desktop.resources.serializers.certification_serializer import (
    serialize_certification,
)
from src.core.modules.project_management.api.desktop.resources.serializers.resource_serializer import (
    serialize_resource,
    serialize_resource_catalog_item,
    serialize_resource_inspector,
    serialize_resource_summary,
)
from src.core.modules.project_management.api.desktop.resources.serializers.skill_serializer import (
    serialize_skill,
)
from src.core.modules.project_management.api.desktop.resources.serializers.context_serializer import (
    serialize_resource_activity,
    serialize_resource_assignment,
    serialize_resource_project,
)
from src.core.modules.project_management.api.desktop.resources.utils.date_utils import (
    parse_date,
)
from src.core.modules.project_management.api.desktop.resources.utils.resource_enum_utils import (
    coerce_cost_type,
    coerce_worker_type,
)
from src.core.modules.project_management.application.resources import ResourceService
from src.core.modules.project_management.domain.enums import ProjectStatus, TaskStatus
from src.core.platform.application.master_data.employee.employee_service import EmployeeService


def _coerce_project_status(value: object) -> ProjectStatus | None:
    normalized = str(value or "all").strip().upper()
    if normalized == "ALL":
        return None
    try:
        return ProjectStatus(normalized)
    except ValueError:
        return None


def _coerce_task_status(value: object) -> TaskStatus | None:
    normalized = str(value or "all").strip().upper()
    if normalized == "ALL":
        return None
    try:
        return TaskStatus(normalized)
    except ValueError:
        return None


class ProjectManagementResourcesDesktopApi:
    def __init__(
        self,
        *,
        resource_service: ResourceService | None = None,
        employee_service: EmployeeService | None = None,
        workload_service: object | None = None,
        department_service: object | None = None,
        site_service: object | None = None,
    ) -> None:
        self._resource_service = resource_service
        self._employee_service = employee_service
        self._workload_service = workload_service
        self._department_service = department_service
        self._site_service = site_service

    def list_worker_types(self) -> tuple[ResourceWorkerTypeDescriptor, ...]:
        return build_worker_type_options()

    def list_categories(self) -> tuple[ResourceCategoryDescriptor, ...]:
        return build_category_options()

    def list_resource_kinds(self) -> tuple[ResourceKindDescriptor, ...]:
        return build_kind_options()

    def list_departments(self) -> tuple[ResourceScopeOptionDescriptor, ...]:
        return build_department_options(self._department_service)

    def list_sites(self) -> tuple[ResourceScopeOptionDescriptor, ...]:
        return build_site_options(self._site_service)

    def list_employees(self) -> tuple[ResourceEmployeeOptionDescriptor, ...]:
        return build_employee_options(self._employee_service)

    def list_resources(self) -> tuple[ResourceDesktopDto, ...]:
        if self._resource_service is None:
            return ()
        employee_lookup = build_employee_lookup(self._employee_service)
        resources = sorted(
            self._resource_service.list_resources(),
            key=lambda resource: (
                not bool(getattr(resource, "is_active", True)),
                str(getattr(resource, "name", "") or "").casefold(),
            ),
        )
        return tuple(
            serialize_resource(resource, employee_lookup=employee_lookup)
            for resource in resources
        )

    def list_resource_page(
        self,
        *,
        search_text: str = "",
        active: str = "all",
        category: str = "all",
        page: int = 1,
        page_size: int = 25,
        sort_key: str = "catalog",
        sort_direction: str = "asc",
    ) -> ResourceCatalogPageDesktopDto:
        service = self._require_resource_service()
        normalized_active = str(active or "all").strip().lower()
        active_value = (
            True if normalized_active == "active"
            else False if normalized_active == "inactive"
            else None
        )
        normalized_category = str(category or "all").strip().upper()
        category_value = (
            None if normalized_category == "ALL" else coerce_cost_type(normalized_category)
        )
        result = service.query_catalog_page(
            search_text=search_text,
            active=active_value,
            category=category_value,
            page=page,
            page_size=page_size,
            sort_key=sort_key,
            sort_direction=sort_direction,
        )
        return ResourceCatalogPageDesktopDto(
            items=tuple(serialize_resource_catalog_item(item) for item in result.items),
            filtered_total=result.filtered_total,
            total=result.summary.total,
            active=result.summary.active,
            employees=result.summary.employees,
            external=result.summary.external,
            average_capacity=result.summary.average_capacity,
            page=result.page,
            page_size=result.page_size,
            sort_key=result.sort.key,
            sort_direction=result.sort.direction.value,
        )

    def get_resource_inspector(self, resource_id: str) -> ResourceInspectorDesktopDto:
        fact = self._require_resource_service().get_resource_inspector(resource_id)
        return serialize_resource_inspector(fact)

    def get_resource_summary(self, resource_id: str) -> ResourceSummaryDesktopDto:
        fact = self._require_resource_service().get_resource_summary(resource_id)
        return serialize_resource_summary(fact)

    def create_resource(self, command: ResourceCreateCommand) -> ResourceDesktopDto:
        service = self._require_resource_service()
        resource = service.create_resource(
            name=command.name,
            code=command.code,
            kind=command.kind,
            role=command.role,
            hourly_rate=command.hourly_rate,
            cost_type=coerce_cost_type(command.cost_type),
            currency_code=command.currency_code,
            capacity_percent=command.capacity_percent,
            address=command.address,
            contact=command.contact,
            worker_type=coerce_worker_type(command.worker_type),
            employee_id=command.employee_id,
            department_id=command.department_id,
            site_id=command.site_id,
        )
        return serialize_resource(
            resource,
            employee_lookup=build_employee_lookup(self._employee_service),
        )

    def update_resource(self, command: ResourceUpdateCommand) -> ResourceDesktopDto:
        service = self._require_resource_service()
        resource = service.update_resource(
            resource_id=command.resource_id,
            expected_version=command.expected_version,
            name=command.name,
            code=command.code,
            kind=command.kind,
            role=command.role,
            hourly_rate=command.hourly_rate,
            cost_type=coerce_cost_type(command.cost_type),
            currency_code=command.currency_code,
            capacity_percent=command.capacity_percent,
            address=command.address,
            contact=command.contact,
            worker_type=coerce_worker_type(command.worker_type),
            employee_id=command.employee_id,
            department_id=command.department_id,
            site_id=command.site_id,
        )
        return serialize_resource(
            resource,
            employee_lookup=build_employee_lookup(self._employee_service),
        )

    def deactivate_resource(self, command: ResourceLifecycleCommand) -> ResourceDesktopDto:
        service = self._require_resource_service()
        updated = service.deactivate_resource(
            resource_id=command.resource_id,
            expected_version=command.expected_version,
        )
        return serialize_resource(
            updated,
            employee_lookup=build_employee_lookup(self._employee_service),
        )

    def reactivate_resource(self, command: ResourceLifecycleCommand) -> ResourceDesktopDto:
        service = self._require_resource_service()
        updated = service.reactivate_resource(
            resource_id=command.resource_id,
            expected_version=command.expected_version,
        )
        return serialize_resource(
            updated,
            employee_lookup=build_employee_lookup(self._employee_service),
        )

    def purge_resource(self, command: ResourcePurgeCommand) -> None:
        service = self._require_resource_service()
        service.purge_resource(
            resource_id=command.resource_id,
            expected_version=command.expected_version,
        )

    def list_resource_skills_page(
        self,
        resource_id: str,
        *,
        search_text: str = "",
        proficiency: str = "all",
        page: int = 1,
        page_size: int = 25,
        sort_key: str = "skillName",
        sort_direction: str = "asc",
    ) -> ResourceSkillsPageDesktopDto:
        result = self._require_resource_service().query_resource_skills_page(
            resource_id,
            search_text=search_text,
            proficiency=None if proficiency == "all" else proficiency,
            page=page,
            page_size=page_size,
            sort_key=sort_key,
            sort_direction=sort_direction,
        )
        return ResourceSkillsPageDesktopDto(
            items=tuple(
                ResourceSkillDesktopDto(
                    id=item.skill_id,
                    resource_id=item.resource_id,
                    skill_code=item.skill_code,
                    skill_name=item.skill_name,
                    proficiency=item.proficiency,
                    proficiency_label=item.proficiency.replace("_", " ").title(),
                    notes=item.notes,
                    version=item.version,
                )
                for item in result.items
            ),
            filtered_total=result.filtered_total,
            page=result.page,
            page_size=result.page_size,
            sort_key=result.sort.key,
            sort_direction=result.sort.direction.value,
        )

    def add_resource_skill(
        self,
        command: ResourceAddSkillCommand,
    ) -> ResourceSkillDesktopDto:
        service = self._require_resource_service()
        skill = service.add_resource_skill(
            resource_id=command.resource_id,
            skill_code=command.skill_code,
            skill_name=command.skill_name,
            proficiency=command.proficiency,
            notes=command.notes,
        )
        return serialize_skill(skill)

    def list_resource_certifications_page(
        self,
        resource_id: str,
        *,
        search_text: str = "",
        status: str = "all",
        page: int = 1,
        page_size: int = 25,
        sort_key: str = "certificationName",
        sort_direction: str = "asc",
    ) -> ResourceCertificationsPageDesktopDto:
        result = self._require_resource_service().query_resource_certifications_page(
            resource_id,
            search_text=search_text,
            status=None if status == "all" else status,
            page=page,
            page_size=page_size,
            sort_key=sort_key,
            sort_direction=sort_direction,
        )
        return ResourceCertificationsPageDesktopDto(
            items=tuple(
                ResourceCertificationDesktopDto(
                    id=item.certification_id,
                    resource_id=item.resource_id,
                    certification_code=item.certification_code,
                    certification_name=item.certification_name,
                    issued_date=(item.issued_date.isoformat() if item.issued_date else None),
                    expiry_date=(item.expiry_date.isoformat() if item.expiry_date else None),
                    certificate_number=item.certificate_number,
                    issuer=item.issuer,
                    notes=item.notes,
                    cert_status=item.cert_status,
                    cert_status_label=item.cert_status.replace("-", " ").title(),
                    version=item.version,
                )
                for item in result.items
            ),
            filtered_total=result.filtered_total,
            page=result.page,
            page_size=result.page_size,
            sort_key=result.sort.key,
            sort_direction=result.sort.direction.value,
        )

    def update_resource_skill(
        self, command: ResourceUpdateSkillCommand
    ) -> ResourceSkillDesktopDto:
        service = self._require_resource_service()
        skill = service.update_resource_skill(
            skill_id=command.skill_id,
            expected_version=command.expected_version,
            skill_code=command.skill_code,
            skill_name=command.skill_name,
            proficiency=command.proficiency,
            notes=command.notes,
        )
        return serialize_skill(skill)

    def remove_resource_skill(self, command: ResourceRemoveSkillCommand) -> None:
        service = self._require_resource_service()
        service.remove_resource_skill(
            command.skill_id, expected_version=command.expected_version
        )

    def add_resource_certification(
        self,
        command: ResourceAddCertificationCommand,
    ) -> ResourceCertificationDesktopDto:
        service = self._require_resource_service()
        certification = service.add_resource_certification(
            resource_id=command.resource_id,
            certification_code=command.certification_code,
            certification_name=command.certification_name,
            issued_date=parse_date(command.issued_date),
            expiry_date=parse_date(command.expiry_date),
            certificate_number=command.certificate_number,
            issuer=command.issuer,
            notes=command.notes,
        )
        return serialize_certification(certification)

    def update_resource_certification(
        self, command: ResourceUpdateCertificationCommand
    ) -> ResourceCertificationDesktopDto:
        service = self._require_resource_service()
        certification = service.update_resource_certification(
            cert_id=command.cert_id,
            expected_version=command.expected_version,
            certification_code=command.certification_code,
            certification_name=command.certification_name,
            issued_date=parse_date(command.issued_date),
            expiry_date=parse_date(command.expiry_date),
            certificate_number=command.certificate_number,
            issuer=command.issuer,
            notes=command.notes,
        )
        return serialize_certification(certification)

    def remove_resource_certification(
        self, command: ResourceRemoveCertificationCommand
    ) -> None:
        service = self._require_resource_service()
        service.remove_resource_certification(
            command.cert_id, expected_version=command.expected_version
        )

    def list_resource_projects_page(
        self,
        resource_id: str,
        *,
        search_text: str = "",
        active: str = "all",
        status: str = "all",
        page: int = 1,
        page_size: int = 25,
        sort_key: str = "projectName",
        sort_direction: str = "asc",
    ) -> ResourceProjectsPageDesktopDto:
        active_value = (
            True if str(active).lower() == "active"
            else False if str(active).lower() == "inactive"
            else None
        )
        result = self._require_resource_service().query_resource_projects_page(
            resource_id,
            search_text=search_text,
            active=active_value,
            status=_coerce_project_status(status),
            page=page,
            page_size=page_size,
            sort_key=sort_key,
            sort_direction=sort_direction,
        )
        return ResourceProjectsPageDesktopDto(
            items=tuple(serialize_resource_project(item) for item in result.items),
            filtered_total=result.filtered_total,
            page=result.page,
            page_size=result.page_size,
            sort_key=result.sort.key,
            sort_direction=result.sort.direction.value,
        )

    def list_resource_assignments_page(
        self,
        resource_id: str,
        *,
        search_text: str = "",
        project_id: str = "",
        task_status: str = "all",
        assignment_status: str = "all",
        lifecycle: str = "current",
        start_date: str = "",
        end_date: str = "",
        page: int = 1,
        page_size: int = 25,
        sort_key: str = "scheduledStart",
        sort_direction: str = "asc",
    ) -> ResourceAssignmentsPageDesktopDto:
        result = self._require_resource_service().query_resource_assignments_page(
            resource_id,
            search_text=search_text,
            project_id=project_id or None,
            task_status=_coerce_task_status(task_status),
            assignment_status=(
                None if str(assignment_status or "all").lower() == "all"
                else str(assignment_status).lower()
            ),
            lifecycle=lifecycle,
            start_date=parse_date(start_date),
            end_date=parse_date(end_date),
            page=page,
            page_size=page_size,
            sort_key=sort_key,
            sort_direction=sort_direction,
        )
        return ResourceAssignmentsPageDesktopDto(
            items=tuple(serialize_resource_assignment(item) for item in result.items),
            filtered_total=result.filtered_total,
            page=result.page,
            page_size=result.page_size,
            sort_key=result.sort.key,
            sort_direction=result.sort.direction.value,
        )

    def list_resource_activity_page(
        self,
        resource_id: str,
        *,
        category: str = "all",
        start_date: str = "",
        end_date: str = "",
        page: int = 1,
        page_size: int = 25,
    ) -> ResourceActivityPageDesktopDto:
        result = self._require_resource_service().query_resource_activity_page(
            resource_id,
            category=category,
            start_date=parse_date(start_date),
            end_date=parse_date(end_date),
            page=page,
            page_size=page_size,
        )
        return ResourceActivityPageDesktopDto(
            items=tuple(serialize_resource_activity(item) for item in result.items),
            filtered_total=result.filtered_total,
            page=result.page,
            page_size=result.page_size,
            sort_key=result.sort.key,
            sort_direction=result.sort.direction.value,
        )

    def build_resource_availability(
        self,
        resource_id: str,
        *,
        start_date: str,
        end_date: str,
    ) -> ResourceAvailabilityDto:
        return build_resource_availability(
            resource_id,
            workload_service=self._workload_service,
            start_date=parse_date(start_date),
            end_date=parse_date(end_date),
        )

    def _require_resource_service(self) -> ResourceService:
        if self._resource_service is None:
            raise RuntimeError(
                "Project management resources desktop API is not connected."
            )
        return self._resource_service


__all__ = ["ProjectManagementResourcesDesktopApi"]

from __future__ import annotations

from src.core.modules.project_management.api.desktop.resources.builders.assignment_builder import (
    build_resource_assignments,
)
from src.core.modules.project_management.api.desktop.resources.builders.availability_builder import (
    build_resource_availability,
)
from src.core.modules.project_management.api.desktop.resources.builders.employee_option_builder import (
    build_employee_lookup,
    build_employee_options,
)
from src.core.modules.project_management.api.desktop.resources.builders.option_builder import (
    build_category_options,
    build_worker_type_options,
)
from src.core.modules.project_management.api.desktop.resources.commands.certification_commands import (
    ResourceAddCertificationCommand,
)
from src.core.modules.project_management.api.desktop.resources.commands.resource_commands import (
    ResourceCreateCommand,
    ResourceUpdateCommand,
)
from src.core.modules.project_management.api.desktop.resources.commands.skill_commands import (
    ResourceAddSkillCommand,
)
from src.core.modules.project_management.api.desktop.resources.models.assignments import (
    ResourceAssignmentDesktopDto,
)
from src.core.modules.project_management.api.desktop.resources.models.availability import (
    ResourceAvailabilityDto,
)
from src.core.modules.project_management.api.desktop.resources.models.certifications import (
    ResourceCertificationDesktopDto,
)
from src.core.modules.project_management.api.desktop.resources.models.options import (
    ResourceCategoryDescriptor,
    ResourceEmployeeOptionDescriptor,
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
from src.core.modules.project_management.api.desktop.resources.utils.date_utils import (
    parse_date,
)
from src.core.modules.project_management.api.desktop.resources.utils.resource_enum_utils import (
    coerce_cost_type,
    coerce_worker_type,
)
from src.core.modules.project_management.application.resources import (
    ResourceAvailabilityService,
    ResourceService,
)
from src.core.platform.application.master_data.employee.employee_service import EmployeeService


class ProjectManagementResourcesDesktopApi:
    def __init__(
        self,
        *,
        resource_service: ResourceService | None = None,
        employee_service: EmployeeService | None = None,
        availability_service: ResourceAvailabilityService | None = None,
        task_service: object | None = None,
        project_service: object | None = None,
    ) -> None:
        self._resource_service = resource_service
        self._employee_service = employee_service
        self._availability_service = availability_service
        self._task_service = task_service
        self._project_service = project_service

    def list_worker_types(self) -> tuple[ResourceWorkerTypeDescriptor, ...]:
        return build_worker_type_options()

    def list_categories(self) -> tuple[ResourceCategoryDescriptor, ...]:
        return build_category_options()

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
            code=getattr(command, "code", ""),
            role=command.role,
            hourly_rate=command.hourly_rate,
            is_active=command.is_active,
            cost_type=coerce_cost_type(command.cost_type),
            currency_code=command.currency_code,
            capacity_percent=command.capacity_percent,
            address=command.address,
            contact=command.contact,
            worker_type=coerce_worker_type(command.worker_type),
            employee_id=command.employee_id,
        )
        return serialize_resource(
            resource,
            employee_lookup=build_employee_lookup(self._employee_service),
        )

    def update_resource(self, command: ResourceUpdateCommand) -> ResourceDesktopDto:
        service = self._require_resource_service()
        resource = service.update_resource(
            command.resource_id,
            name=command.name,
            code=getattr(command, "code", ""),
            role=command.role,
            hourly_rate=command.hourly_rate,
            is_active=command.is_active,
            cost_type=coerce_cost_type(command.cost_type),
            currency_code=command.currency_code,
            capacity_percent=command.capacity_percent,
            address=command.address,
            contact=command.contact,
            worker_type=coerce_worker_type(command.worker_type),
            employee_id=command.employee_id,
            expected_version=command.expected_version,
        )
        return serialize_resource(
            resource,
            employee_lookup=build_employee_lookup(self._employee_service),
        )

    def toggle_resource_active(
        self,
        resource_id: str,
        *,
        expected_version: int | None = None,
    ) -> ResourceDesktopDto:
        service = self._require_resource_service()
        resource = service.get_resource(resource_id)
        updated = service.update_resource(
            resource_id,
            is_active=not bool(getattr(resource, "is_active", True)),
            expected_version=expected_version,
        )
        return serialize_resource(
            updated,
            employee_lookup=build_employee_lookup(self._employee_service),
        )

    def delete_resource(self, resource_id: str) -> None:
        self._require_resource_service().delete_resource(resource_id)

    def list_resource_skills(
        self,
        resource_id: str,
    ) -> tuple[ResourceSkillDesktopDto, ...]:
        service = self._resource_service
        if service is None:
            return ()
        try:
            skills = service.list_resource_skills(resource_id)
        except Exception:
            return ()
        return tuple(serialize_skill(skill) for skill in skills)

    def list_resource_certifications(
        self,
        resource_id: str,
    ) -> tuple[ResourceCertificationDesktopDto, ...]:
        service = self._resource_service
        if service is None:
            return ()
        try:
            certifications = service.list_resource_certifications(resource_id)
        except Exception:
            return ()
        return tuple(
            serialize_certification(certification)
            for certification in certifications
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

    def remove_resource_skill(self, skill_id: str) -> None:
        self._require_resource_service().remove_resource_skill(skill_id)

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
            issuing_body=command.issuing_body,
            notes=command.notes,
        )
        return serialize_certification(certification)

    def remove_resource_certification(self, cert_id: str) -> None:
        self._require_resource_service().remove_resource_certification(cert_id)

    def list_resource_assignments(
        self,
        resource_id: str,
    ) -> tuple[ResourceAssignmentDesktopDto, ...]:
        return build_resource_assignments(
            resource_id,
            task_service=self._task_service,
            project_service=self._project_service,
        )

    def build_resource_availability(
        self,
        resource_id: str,
    ) -> ResourceAvailabilityDto | None:
        return build_resource_availability(
            resource_id,
            availability_service=self._availability_service,
        )

    def _require_resource_service(self) -> ResourceService:
        if self._resource_service is None:
            raise RuntimeError(
                "Project management resources desktop API is not connected."
            )
        return self._resource_service


__all__ = ["ProjectManagementResourcesDesktopApi"]

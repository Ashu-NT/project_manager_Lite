from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from types import SimpleNamespace

from src.api.desktop.platform.models import (
    ApprovalRequestDto,
    ApprovalStatus,
    AuditLogEntryDto,
    DepartmentDto,
    DepartmentLocationReferenceDto,
    DesktopApiError,
    DesktopApiResult,
    DocumentDto,
    DocumentLinkDto,
    DocumentStructureDto,
    EmployeeDto,
    ModuleDto,
    ModuleEntitlementDto,
    OrganizationDto,
    PartyDto,
    PlatformCapabilityDto,
    PlatformRuntimeContextDto,
    RoleDto,
    ScopedAccessGrantDto,
    SiteDto,
    ScopeTargetDto,
    ScopeTypeChoiceDto,
    SupportBundleDto,
    SupportEventDto,
    SupportInstallLaunchDto,
    SupportPathsDto,
    SupportSettingsDto,
    SupportUpdateStatusDto,
    UserDto,
)
from src.ui_qml.platform.context import PlatformWorkspaceCatalog
from src.ui_qml.platform.presenters import PlatformRuntimePresenter


def _organization(
    *,
    organization_id: str,
    code: str,
    display_name: str,
    is_active: bool = True,
) -> OrganizationDto:
    return OrganizationDto(
        id=organization_id,
        organization_code=code,
        display_name=display_name,
        timezone_name="UTC",
        base_currency="EUR",
        is_active=is_active,
        version=1,
    )


def _module(
    *,
    code: str,
    label: str,
    description: str,
    stage: str = "active",
) -> ModuleDto:
    return ModuleDto(
        code=code,
        label=label,
        description=description,
        default_enabled=True,
        stage=stage,
        primary_capabilities=(f"{code}.core",),
    )


class _FakePlatformRuntimeApi:
    def __init__(self) -> None:
        self._organizations: list[OrganizationDto] = [
            _organization(organization_id="org-1", code="ORG", display_name="TechAsh"),
            _organization(
                organization_id="org-2",
                code="OPS",
                display_name="Operations",
                is_active=False,
            ),
        ]
        self._modules = (
            _module(code="project_management", label="Project Management", description="Projects"),
            _module(code="maintenance", label="Maintenance", description="Assets"),
            _module(code="inventory", label="Inventory", description="Stock", stage="planned"),
        )
        self._entitlements: list[ModuleEntitlementDto] = [
            ModuleEntitlementDto(
                module_code="project_management",
                label="Project Management",
                stage="active",
                licensed=True,
                enabled=True,
                runtime_enabled=True,
                lifecycle_status="active",
                lifecycle_label="Active",
                lifecycle_alert=None,
                available_to_license=True,
                planned=False,
                module=self._modules[0],
            ),
            ModuleEntitlementDto(
                module_code="maintenance",
                label="Maintenance",
                stage="active",
                licensed=True,
                enabled=False,
                runtime_enabled=False,
                lifecycle_status="active",
                lifecycle_label="Active",
                lifecycle_alert=None,
                available_to_license=True,
                planned=False,
                module=self._modules[1],
            ),
            ModuleEntitlementDto(
                module_code="inventory",
                label="Inventory",
                stage="planned",
                licensed=False,
                enabled=False,
                runtime_enabled=False,
                lifecycle_status="planned",
                lifecycle_label="Planned",
                lifecycle_alert=None,
                available_to_license=False,
                planned=True,
                module=self._modules[2],
            ),
        ]
        self._rebuild_runtime_context()

    def _rebuild_runtime_context(self) -> None:
        active_organization = next((row for row in self._organizations if row.is_active), None)
        self._runtime_context = PlatformRuntimeContextDto(
            context_label="Enterprise Runtime",
            shell_summary="2 modules licensed",
            active_organization=active_organization,
            platform_capabilities=(
                PlatformCapabilityDto(
                    code="approval",
                    label="Approvals",
                    description="Governed approval workflows",
                    always_on=True,
                ),
            ),
            entitlements=tuple(self._entitlements),
            enabled_modules=tuple(item.module for item in self._entitlements if item.enabled),
            licensed_modules=tuple(item.module for item in self._entitlements if item.licensed),
            available_modules=self._modules,
            planned_modules=tuple(item.module for item in self._entitlements if item.planned),
        )

    def get_runtime_context(self) -> DesktopApiResult[PlatformRuntimeContextDto]:
        return DesktopApiResult(ok=True, data=self._runtime_context)

    def list_organizations(
        self,
        *,
        active_only: bool | None = None,
    ) -> DesktopApiResult[tuple[OrganizationDto, ...]]:
        rows = self._organizations
        if active_only is not None:
            rows = [row for row in rows if row.is_active == active_only]
        return DesktopApiResult(ok=True, data=tuple(rows))

    def list_modules(self) -> DesktopApiResult[tuple[ModuleDto, ...]]:
        return DesktopApiResult(ok=True, data=self._modules)

    def provision_organization(self, command) -> DesktopApiResult[OrganizationDto]:
        if any(row.organization_code == command.organization_code for row in self._organizations):
            return DesktopApiResult(
                ok=False,
                error=DesktopApiError(
                    code="organization_exists",
                    message=f"Organization code '{command.organization_code}' already exists.",
                    category="conflict",
                ),
            )
        if command.is_active:
            self._organizations = [replace(row, is_active=False) for row in self._organizations]
        organization = OrganizationDto(
            id=f"org-{len(self._organizations) + 1}",
            organization_code=command.organization_code,
            display_name=command.display_name,
            timezone_name=command.timezone_name,
            base_currency=command.base_currency,
            is_active=command.is_active,
            version=1,
        )
        self._organizations.append(organization)
        self._rebuild_runtime_context()
        return DesktopApiResult(ok=True, data=organization)

    def update_organization(self, command) -> DesktopApiResult[OrganizationDto]:
        for index, row in enumerate(self._organizations):
            if row.id != command.organization_id:
                continue
            if command.is_active:
                self._organizations = [
                    replace(existing, is_active=False)
                    if existing.id != command.organization_id
                    else existing
                    for existing in self._organizations
                ]
                row = self._organizations[index]
            updated = replace(
                row,
                organization_code=command.organization_code or row.organization_code,
                display_name=command.display_name or row.display_name,
                timezone_name=command.timezone_name or row.timezone_name,
                base_currency=command.base_currency or row.base_currency,
                is_active=row.is_active if command.is_active is None else command.is_active,
                version=row.version + 1,
            )
            self._organizations[index] = updated
            self._rebuild_runtime_context()
            return DesktopApiResult(ok=True, data=updated)
        return DesktopApiResult(
            ok=False,
            error=DesktopApiError(
                code="organization_not_found",
                message=f"Organization '{command.organization_id}' was not found.",
                category="not_found",
            ),
        )

    def set_active_organization(self, organization_id: str) -> DesktopApiResult[OrganizationDto]:
        updated: OrganizationDto | None = None
        next_rows: list[OrganizationDto] = []
        for row in self._organizations:
            new_row = replace(row, is_active=row.id == organization_id)
            next_rows.append(new_row)
            if new_row.id == organization_id:
                updated = new_row
        if updated is None:
            return DesktopApiResult(
                ok=False,
                error=DesktopApiError(
                    code="organization_not_found",
                    message=f"Organization '{organization_id}' was not found.",
                    category="not_found",
                ),
            )
        self._organizations = next_rows
        self._rebuild_runtime_context()
        return DesktopApiResult(ok=True, data=updated)

    def patch_module_state(self, command) -> DesktopApiResult[ModuleEntitlementDto]:
        for index, entitlement in enumerate(self._entitlements):
            if entitlement.module_code != command.module_code:
                continue
            licensed = entitlement.licensed if command.licensed is None else command.licensed
            enabled = entitlement.enabled if command.enabled is None else command.enabled
            lifecycle_status = (
                entitlement.lifecycle_status
                if command.lifecycle_status is None
                else command.lifecycle_status
            )
            if not licensed:
                enabled = False
            runtime_enabled = enabled and lifecycle_status not in {"suspended", "expired"}
            lifecycle_label = lifecycle_status.title()
            lifecycle_alert = None if lifecycle_status in {"active", "trial", "planned"} else lifecycle_label
            updated = replace(
                entitlement,
                licensed=licensed,
                enabled=enabled,
                runtime_enabled=runtime_enabled,
                lifecycle_status=lifecycle_status,
                lifecycle_label=lifecycle_label,
                lifecycle_alert=lifecycle_alert,
            )
            self._entitlements[index] = updated
            self._rebuild_runtime_context()
            return DesktopApiResult(ok=True, data=updated)
        return DesktopApiResult(
            ok=False,
            error=DesktopApiError(
                code="module_not_found",
                message=f"Module '{command.module_code}' was not found.",
                category="not_found",
            ),
        )


class _FakePlatformSiteApi:
    def __init__(self, *, runtime_api: _FakePlatformRuntimeApi, rows: tuple[SiteDto, ...]) -> None:
        self._runtime_api = runtime_api
        self._rows = list(rows)

    def get_context(self) -> DesktopApiResult[OrganizationDto]:
        return DesktopApiResult(ok=True, data=self._runtime_api.get_runtime_context().data.active_organization)

    def list_sites(self, *, active_only: bool | None = None) -> DesktopApiResult[tuple[SiteDto, ...]]:
        rows = self._rows
        if active_only is not None:
            rows = [row for row in rows if row.is_active == active_only]
        return DesktopApiResult(ok=True, data=tuple(rows))

    def create_site(self, command) -> DesktopApiResult[SiteDto]:
        active_organization = self._runtime_api.get_runtime_context().data.active_organization
        site = SiteDto(
            id=f"site-{len(self._rows) + 1}",
            organization_id=active_organization.id if active_organization is not None else "org-1",
            site_code=command.site_code,
            name=command.name,
            description=command.description,
            country=command.country,
            region="",
            city=command.city,
            address_line_1="",
            address_line_2="",
            postal_code="",
            timezone=command.timezone_name,
            currency_code=command.currency_code,
            site_type=command.site_type,
            status=command.status,
            default_calendar_id="",
            default_language="en",
            is_active=command.is_active,
            notes=command.notes,
            version=1,
        )
        self._rows.append(site)
        return DesktopApiResult(ok=True, data=site)

    def update_site(self, command) -> DesktopApiResult[SiteDto]:
        for index, row in enumerate(self._rows):
            if row.id != command.site_id:
                continue
            updated = replace(
                row,
                site_code=command.site_code or row.site_code,
                name=command.name or row.name,
                description=row.description if command.description is None else command.description,
                city=row.city if command.city is None else command.city,
                country=row.country if command.country is None else command.country,
                timezone=row.timezone if command.timezone_name is None else command.timezone_name,
                currency_code=row.currency_code if command.currency_code is None else command.currency_code,
                site_type=row.site_type if command.site_type is None else command.site_type,
                status=row.status if command.status is None else command.status,
                notes=row.notes if command.notes is None else command.notes,
                is_active=row.is_active if command.is_active is None else command.is_active,
                version=row.version + 1,
            )
            self._rows[index] = updated
            return DesktopApiResult(ok=True, data=updated)
        return DesktopApiResult(
            ok=False,
            error=DesktopApiError(
                code="site_not_found",
                message=f"Site '{command.site_id}' was not found.",
                category="not_found",
            ),
        )


class _FakePlatformDepartmentApi:
    def __init__(
        self,
        *,
        runtime_api: _FakePlatformRuntimeApi,
        site_api: _FakePlatformSiteApi,
        rows: tuple[DepartmentDto, ...],
        location_rows: tuple[DepartmentLocationReferenceDto, ...],
    ) -> None:
        self._runtime_api = runtime_api
        self._site_api = site_api
        self._rows = list(rows)
        self._location_rows = list(location_rows)

    def get_context(self) -> DesktopApiResult[OrganizationDto]:
        return DesktopApiResult(ok=True, data=self._runtime_api.get_runtime_context().data.active_organization)

    def list_departments(
        self,
        *,
        active_only: bool | None = None,
    ) -> DesktopApiResult[tuple[DepartmentDto, ...]]:
        rows = self._rows
        if active_only is not None:
            rows = [row for row in rows if row.is_active == active_only]
        return DesktopApiResult(ok=True, data=tuple(rows))

    def list_location_references(
        self,
        *,
        active_only: bool | None = None,
    ) -> DesktopApiResult[tuple[DepartmentLocationReferenceDto, ...]]:
        rows = self._location_rows
        if active_only is not None:
            rows = [row for row in rows if row.is_active == active_only]
        return DesktopApiResult(ok=True, data=tuple(rows))

    def create_department(self, command) -> DesktopApiResult[DepartmentDto]:
        active_organization = self._runtime_api.get_runtime_context().data.active_organization
        department = DepartmentDto(
            id=f"dep-{len(self._rows) + 1}",
            organization_id=active_organization.id if active_organization is not None else "org-1",
            department_code=command.department_code,
            name=command.name,
            description=command.description,
            site_id=command.site_id,
            default_location_id=command.default_location_id,
            parent_department_id=command.parent_department_id,
            department_type=command.department_type,
            cost_center_code=command.cost_center_code,
            manager_employee_id=None,
            is_active=command.is_active,
            notes=command.notes,
            version=1,
        )
        self._rows.append(department)
        return DesktopApiResult(ok=True, data=department)

    def update_department(self, command) -> DesktopApiResult[DepartmentDto]:
        for index, row in enumerate(self._rows):
            if row.id != command.department_id:
                continue
            updated = replace(
                row,
                department_code=command.department_code or row.department_code,
                name=command.name or row.name,
                description=row.description if command.description is None else command.description,
                site_id=row.site_id if command.site_id is None else command.site_id,
                default_location_id=(
                    row.default_location_id
                    if command.default_location_id is None
                    else command.default_location_id
                ),
                parent_department_id=(
                    row.parent_department_id
                    if command.parent_department_id is None
                    else command.parent_department_id
                ),
                department_type=row.department_type if command.department_type is None else command.department_type,
                cost_center_code=(
                    row.cost_center_code
                    if command.cost_center_code is None
                    else command.cost_center_code
                ),
                is_active=row.is_active if command.is_active is None else command.is_active,
                notes=row.notes if command.notes is None else command.notes,
                version=row.version + 1,
            )
            self._rows[index] = updated
            return DesktopApiResult(ok=True, data=updated)
        return DesktopApiResult(
            ok=False,
            error=DesktopApiError(
                code="department_not_found",
                message=f"Department '{command.department_id}' was not found.",
                category="not_found",
            ),
        )


class _FakePlatformEmployeeApi:
    def __init__(self, rows: tuple[EmployeeDto, ...]) -> None:
        self._rows = list(rows)

    def list_employees(
        self,
        *,
        active_only: bool | None = None,
    ) -> DesktopApiResult[tuple[EmployeeDto, ...]]:
        rows = self._rows
        if active_only is not None:
            rows = [row for row in rows if row.is_active == active_only]
        return DesktopApiResult(ok=True, data=tuple(rows))

    def create_employee(self, command) -> DesktopApiResult[EmployeeDto]:
        employee = EmployeeDto(
            id=f"emp-{len(self._rows) + 1}",
            employee_code=command.employee_code,
            full_name=command.full_name,
            department_id=command.department_id,
            department=command.department,
            site_id=command.site_id,
            site_name=command.site_name,
            title=command.title,
            employment_type=command.employment_type,
            email=command.email,
            phone=command.phone,
            is_active=command.is_active,
            version=1,
        )
        self._rows.append(employee)
        return DesktopApiResult(ok=True, data=employee)

    def update_employee(self, command) -> DesktopApiResult[EmployeeDto]:
        for index, row in enumerate(self._rows):
            if row.id != command.employee_id:
                continue
            updated = replace(
                row,
                employee_code=command.employee_code or row.employee_code,
                full_name=command.full_name or row.full_name,
                department_id=row.department_id if command.department_id is None else command.department_id,
                department=row.department if command.department is None else command.department,
                site_id=row.site_id if command.site_id is None else command.site_id,
                site_name=row.site_name if command.site_name is None else command.site_name,
                title=row.title if command.title is None else command.title,
                employment_type=(
                    row.employment_type
                    if command.employment_type is None
                    else command.employment_type
                ),
                email=row.email if command.email is None else command.email,
                phone=row.phone if command.phone is None else command.phone,
                is_active=row.is_active if command.is_active is None else command.is_active,
                version=row.version + 1,
            )
            self._rows[index] = updated
            return DesktopApiResult(ok=True, data=updated)
        return DesktopApiResult(
            ok=False,
            error=DesktopApiError(
                code="employee_not_found",
                message=f"Employee '{command.employee_id}' was not found.",
                category="not_found",
            ),
        )


class _FakePlatformUserApi:
    def __init__(self, rows: tuple[UserDto, ...], roles: tuple[RoleDto, ...]) -> None:
        self._rows = list(rows)
        self._roles = roles

    def list_users(self) -> DesktopApiResult[tuple[UserDto, ...]]:
        return DesktopApiResult(ok=True, data=tuple(self._rows))

    def list_roles(self) -> DesktopApiResult[tuple[RoleDto, ...]]:
        return DesktopApiResult(ok=True, data=self._roles)

    def create_user(self, command) -> DesktopApiResult[UserDto]:
        if any(row.username == command.username for row in self._rows):
            return DesktopApiResult(
                ok=False,
                error=DesktopApiError(
                    code="user_exists",
                    message=f"User '{command.username}' already exists.",
                    category="conflict",
                ),
            )
        user = UserDto(
            id=f"user-{len(self._rows) + 1}",
            username=command.username,
            display_name=command.display_name,
            email=command.email,
            identity_provider=None,
            federated_subject=None,
            is_active=command.is_active,
            failed_login_attempts=0,
            locked_until=None,
            last_login_at=None,
            last_login_auth_method=None,
            last_login_device_label=None,
            session_expires_at=None,
            session_timeout_minutes_override=None,
            must_change_password=False,
            version=1,
            role_names=tuple(sorted(command.role_names)),
        )
        self._rows.append(user)
        return DesktopApiResult(ok=True, data=user)

    def update_user(self, command) -> DesktopApiResult[UserDto]:
        for index, row in enumerate(self._rows):
            if row.id != command.user_id:
                continue
            updated = replace(
                row,
                username=command.username or row.username,
                display_name=row.display_name if command.display_name is None else command.display_name,
                email=row.email if command.email is None else command.email,
                version=row.version + 1,
            )
            self._rows[index] = updated
            return DesktopApiResult(ok=True, data=updated)
        return DesktopApiResult(
            ok=False,
            error=DesktopApiError(
                code="user_not_found",
                message=f"User '{command.user_id}' was not found.",
                category="not_found",
            ),
        )

    def assign_role(self, user_id: str, role_name: str) -> DesktopApiResult[UserDto]:
        return self._update_roles(user_id, add=role_name)

    def revoke_role(self, user_id: str, role_name: str) -> DesktopApiResult[UserDto]:
        return self._update_roles(user_id, remove=role_name)

    def set_user_active(self, user_id: str, is_active: bool) -> DesktopApiResult[UserDto]:
        for index, row in enumerate(self._rows):
            if row.id != user_id:
                continue
            updated = replace(row, is_active=is_active, version=row.version + 1)
            self._rows[index] = updated
            return DesktopApiResult(ok=True, data=updated)
        return DesktopApiResult(
            ok=False,
            error=DesktopApiError(
                code="user_not_found",
                message=f"User '{user_id}' was not found.",
                category="not_found",
            ),
        )

    def reset_password(self, command) -> DesktopApiResult[UserDto]:
        for index, row in enumerate(self._rows):
            if row.id != command.user_id:
                continue
            updated = replace(row, must_change_password=False, version=row.version + 1)
            self._rows[index] = updated
            return DesktopApiResult(ok=True, data=updated)
        return DesktopApiResult(
            ok=False,
            error=DesktopApiError(
                code="user_not_found",
                message=f"User '{command.user_id}' was not found.",
                category="not_found",
            ),
        )

    def unlock_user_account(self, user_id: str) -> DesktopApiResult[UserDto]:
        for index, row in enumerate(self._rows):
            if row.id != user_id:
                continue
            updated = replace(row, locked_until=None, failed_login_attempts=0, version=row.version + 1)
            self._rows[index] = updated
            return DesktopApiResult(ok=True, data=updated)
        return DesktopApiResult(
            ok=False,
            error=DesktopApiError(
                code="user_not_found",
                message=f"User '{user_id}' was not found.",
                category="not_found",
            ),
        )

    def revoke_user_sessions(self, user_id: str, *, note: str = "") -> DesktopApiResult[UserDto]:
        for index, row in enumerate(self._rows):
            if row.id != user_id:
                continue
            updated = replace(row, session_expires_at=None, version=row.version + 1)
            self._rows[index] = updated
            return DesktopApiResult(ok=True, data=updated)
        return DesktopApiResult(
            ok=False,
            error=DesktopApiError(
                code="user_not_found",
                message=f"User '{user_id}' was not found.",
                category="not_found",
            ),
        )

    def _update_roles(
        self,
        user_id: str,
        *,
        add: str | None = None,
        remove: str | None = None,
    ) -> DesktopApiResult[UserDto]:
        for index, row in enumerate(self._rows):
            if row.id != user_id:
                continue
            role_names = set(row.role_names)
            if add:
                role_names.add(add)
            if remove:
                role_names.discard(remove)
            updated = replace(row, role_names=tuple(sorted(role_names)), version=row.version + 1)
            self._rows[index] = updated
            return DesktopApiResult(ok=True, data=updated)
        return DesktopApiResult(
            ok=False,
            error=DesktopApiError(
                code="user_not_found",
                message=f"User '{user_id}' was not found.",
                category="not_found",
            ),
        )


class _FakePlatformPartyApi:
    def __init__(self, *, runtime_api: _FakePlatformRuntimeApi, rows: tuple[PartyDto, ...]) -> None:
        self._runtime_api = runtime_api
        self._rows = list(rows)

    def get_context(self) -> DesktopApiResult[OrganizationDto]:
        return DesktopApiResult(ok=True, data=self._runtime_api.get_runtime_context().data.active_organization)

    def list_parties(
        self,
        *,
        active_only: bool | None = None,
    ) -> DesktopApiResult[tuple[PartyDto, ...]]:
        rows = self._rows
        if active_only is not None:
            rows = [row for row in rows if row.is_active == active_only]
        return DesktopApiResult(ok=True, data=tuple(rows))

    def create_party(self, command) -> DesktopApiResult[PartyDto]:
        active_organization = self._runtime_api.get_runtime_context().data.active_organization
        party = PartyDto(
            id=f"party-{len(self._rows) + 1}",
            organization_id=active_organization.id if active_organization is not None else "org-1",
            party_code=command.party_code,
            party_name=command.party_name,
            party_type=command.party_type,
            legal_name=command.legal_name,
            contact_name=command.contact_name,
            email=command.email or "",
            phone=command.phone or "",
            country=command.country,
            city=command.city,
            address_line_1=command.address_line_1,
            address_line_2=command.address_line_2,
            postal_code=command.postal_code,
            website=command.website,
            tax_registration_number=command.tax_registration_number,
            external_reference=command.external_reference,
            is_active=command.is_active,
            created_at=None,
            updated_at=None,
            notes=command.notes,
            version=1,
        )
        self._rows.append(party)
        return DesktopApiResult(ok=True, data=party)

    def update_party(self, command) -> DesktopApiResult[PartyDto]:
        for index, row in enumerate(self._rows):
            if row.id != command.party_id:
                continue
            updated = replace(
                row,
                party_code=row.party_code if command.party_code is None else command.party_code,
                party_name=row.party_name if command.party_name is None else command.party_name,
                party_type=row.party_type if command.party_type is None else command.party_type,
                legal_name=row.legal_name if command.legal_name is None else command.legal_name,
                contact_name=row.contact_name if command.contact_name is None else command.contact_name,
                email=row.email if command.email is None else command.email,
                phone=row.phone if command.phone is None else command.phone,
                country=row.country if command.country is None else command.country,
                city=row.city if command.city is None else command.city,
                address_line_1=row.address_line_1 if command.address_line_1 is None else command.address_line_1,
                address_line_2=row.address_line_2 if command.address_line_2 is None else command.address_line_2,
                postal_code=row.postal_code if command.postal_code is None else command.postal_code,
                website=row.website if command.website is None else command.website,
                tax_registration_number=(
                    row.tax_registration_number
                    if command.tax_registration_number is None
                    else command.tax_registration_number
                ),
                external_reference=(
                    row.external_reference
                    if command.external_reference is None
                    else command.external_reference
                ),
                is_active=row.is_active if command.is_active is None else command.is_active,
                notes=row.notes if command.notes is None else command.notes,
                version=row.version + 1,
            )
            self._rows[index] = updated
            return DesktopApiResult(ok=True, data=updated)
        return DesktopApiResult(
            ok=False,
            error=DesktopApiError(
                code="party_not_found",
                message=f"Party '{command.party_id}' was not found.",
                category="not_found",
            ),
        )


class _FakePlatformDocumentApi:
    def __init__(
        self,
        *,
        runtime_api: _FakePlatformRuntimeApi,
        rows: tuple[DocumentDto, ...],
        structure_rows: tuple[DocumentStructureDto, ...],
        link_rows: tuple[DocumentLinkDto, ...] = (),
    ) -> None:
        self._runtime_api = runtime_api
        self._rows = list(rows)
        self._structure_rows = list(structure_rows)
        self._link_rows = list(link_rows)

    def get_context(self) -> DesktopApiResult[OrganizationDto]:
        return DesktopApiResult(ok=True, data=self._runtime_api.get_runtime_context().data.active_organization)

    def list_documents(
        self,
        *,
        active_only: bool | None = None,
    ) -> DesktopApiResult[tuple[DocumentDto, ...]]:
        rows = self._rows
        if active_only is not None:
            rows = [row for row in rows if row.is_active == active_only]
        return DesktopApiResult(ok=True, data=tuple(rows))

    def list_document_structures(
        self,
        *,
        active_only: bool | None = None,
        object_scope: str | None = None,
    ) -> DesktopApiResult[tuple[DocumentStructureDto, ...]]:
        rows = self._structure_rows
        if active_only is not None:
            rows = [row for row in rows if row.is_active == active_only]
        if object_scope is not None:
            rows = [row for row in rows if row.object_scope == object_scope]
        return DesktopApiResult(ok=True, data=tuple(rows))

    def create_document(self, command) -> DesktopApiResult[DocumentDto]:
        active_organization = self._runtime_api.get_runtime_context().data.active_organization
        document = DocumentDto(
            id=f"doc-{len(self._rows) + 1}",
            organization_id=active_organization.id if active_organization is not None else "org-1",
            document_code=command.document_code,
            title=command.title,
            document_type=command.document_type,
            document_structure_id=command.document_structure_id,
            storage_kind=command.storage_kind,
            storage_uri=command.storage_uri,
            file_name=command.file_name,
            mime_type=command.mime_type,
            source_system=command.source_system,
            uploaded_at=command.uploaded_at,
            uploaded_by_user_id=command.uploaded_by_user_id,
            effective_date=command.effective_date,
            review_date=command.review_date,
            confidentiality_level=command.confidentiality_level,
            business_version_label=command.business_version_label,
            is_current=command.is_current,
            notes=command.notes,
            is_active=command.is_active,
            version=1,
        )
        self._rows.append(document)
        return DesktopApiResult(ok=True, data=document)

    def update_document(self, command) -> DesktopApiResult[DocumentDto]:
        for index, row in enumerate(self._rows):
            if row.id != command.document_id:
                continue
            updated = replace(
                row,
                document_code=row.document_code if command.document_code is None else command.document_code,
                title=row.title if command.title is None else command.title,
                document_type=row.document_type if command.document_type is None else command.document_type,
                document_structure_id=(
                    row.document_structure_id
                    if command.document_structure_id is None
                    else command.document_structure_id
                ),
                storage_kind=row.storage_kind if command.storage_kind is None else command.storage_kind,
                storage_uri=row.storage_uri if command.storage_uri is None else command.storage_uri,
                file_name=row.file_name if command.file_name is None else command.file_name,
                mime_type=row.mime_type if command.mime_type is None else command.mime_type,
                source_system=row.source_system if command.source_system is None else command.source_system,
                confidentiality_level=(
                    row.confidentiality_level
                    if command.confidentiality_level is None
                    else command.confidentiality_level
                ),
                business_version_label=(
                    row.business_version_label
                    if command.business_version_label is None
                    else command.business_version_label
                ),
                is_current=row.is_current if command.is_current is None else command.is_current,
                notes=row.notes if command.notes is None else command.notes,
                is_active=row.is_active if command.is_active is None else command.is_active,
                version=row.version + 1,
            )
            self._rows[index] = updated
            return DesktopApiResult(ok=True, data=updated)
        return DesktopApiResult(
            ok=False,
            error=DesktopApiError(
                code="document_not_found",
                message=f"Document '{command.document_id}' was not found.",
                category="not_found",
            ),
        )

    def create_document_structure(self, command) -> DesktopApiResult[DocumentStructureDto]:
        active_organization = self._runtime_api.get_runtime_context().data.active_organization
        structure = DocumentStructureDto(
            id=f"structure-{len(self._structure_rows) + 1}",
            organization_id=active_organization.id if active_organization is not None else "org-1",
            structure_code=command.structure_code,
            name=command.name,
            description=command.description,
            parent_structure_id=command.parent_structure_id,
            object_scope=command.object_scope,
            default_document_type=command.default_document_type,
            sort_order=command.sort_order,
            is_active=command.is_active,
            notes=command.notes,
            version=1,
        )
        self._structure_rows.append(structure)
        return DesktopApiResult(ok=True, data=structure)

    def update_document_structure(self, command) -> DesktopApiResult[DocumentStructureDto]:
        for index, row in enumerate(self._structure_rows):
            if row.id != command.structure_id:
                continue
            updated = replace(
                row,
                structure_code=row.structure_code if command.structure_code is None else command.structure_code,
                name=row.name if command.name is None else command.name,
                description=row.description if command.description is None else command.description,
                parent_structure_id=(
                    row.parent_structure_id
                    if command.parent_structure_id is None
                    else command.parent_structure_id
                ),
                object_scope=row.object_scope if command.object_scope is None else command.object_scope,
                default_document_type=(
                    row.default_document_type
                    if command.default_document_type is None
                    else command.default_document_type
                ),
                sort_order=row.sort_order if command.sort_order is None else command.sort_order,
                is_active=row.is_active if command.is_active is None else command.is_active,
                notes=row.notes if command.notes is None else command.notes,
                version=row.version + 1,
            )
            self._structure_rows[index] = updated
            return DesktopApiResult(ok=True, data=updated)
        return DesktopApiResult(
            ok=False,
            error=DesktopApiError(
                code="document_structure_not_found",
                message=f"Document structure '{command.structure_id}' was not found.",
                category="not_found",
            ),
        )

    def list_links(self, document_id: str) -> DesktopApiResult[tuple[DocumentLinkDto, ...]]:
        rows = [row for row in self._link_rows if row.document_id == document_id]
        return DesktopApiResult(ok=True, data=tuple(rows))

    def add_link(self, command) -> DesktopApiResult[DocumentLinkDto]:
        active_organization = self._runtime_api.get_runtime_context().data.active_organization
        link = DocumentLinkDto(
            id=f"link-{len(self._link_rows) + 1}",
            organization_id=active_organization.id if active_organization is not None else "org-1",
            document_id=command.document_id,
            module_code=command.module_code,
            entity_type=command.entity_type,
            entity_id=command.entity_id,
            link_role=command.link_role,
        )
        self._link_rows.append(link)
        return DesktopApiResult(ok=True, data=link)

    def remove_link(self, link_id: str) -> DesktopApiResult[None]:
        original_count = len(self._link_rows)
        self._link_rows = [row for row in self._link_rows if row.id != link_id]
        if len(self._link_rows) == original_count:
            return DesktopApiResult(
                ok=False,
                error=DesktopApiError(
                    code="document_link_not_found",
                    message=f"Document link '{link_id}' was not found.",
                    category="not_found",
                ),
            )
        return DesktopApiResult(ok=True, data=None)


class _FakePlatformAccessApi:
    def __init__(
        self,
        *,
        scope_types: tuple[ScopeTypeChoiceDto, ...],
        scope_targets: dict[str, tuple[ScopeTargetDto, ...]],
        grants: tuple[ScopedAccessGrantDto, ...],
    ) -> None:
        self._scope_types = scope_types
        self._scope_targets = dict(scope_targets)
        self._grants = list(grants)

    def list_scope_types(self) -> DesktopApiResult[tuple[ScopeTypeChoiceDto, ...]]:
        return DesktopApiResult(ok=True, data=self._scope_types)

    def list_scope_targets(self, scope_type: str) -> DesktopApiResult[tuple[ScopeTargetDto, ...]]:
        return DesktopApiResult(ok=True, data=self._scope_targets.get(scope_type, ()))

    def list_scope_role_choices(self, scope_type: str) -> DesktopApiResult[tuple[str, ...]]:
        if scope_type == "storeroom":
            return DesktopApiResult(ok=True, data=("viewer", "planner"))
        return DesktopApiResult(ok=True, data=("viewer", "manager"))

    def list_scope_grants(
        self,
        *,
        scope_type: str,
        scope_id: str,
    ) -> DesktopApiResult[tuple[ScopedAccessGrantDto, ...]]:
        rows = [
            row
            for row in self._grants
            if row.scope_type == scope_type and row.scope_id == scope_id
        ]
        return DesktopApiResult(ok=True, data=tuple(rows))

    def assign_scope_grant(self, command) -> DesktopApiResult[ScopedAccessGrantDto]:
        for index, row in enumerate(self._grants):
            if (
                row.scope_type == command.scope_type
                and row.scope_id == command.scope_id
                and row.user_id == command.user_id
            ):
                updated = replace(row, scope_role=command.scope_role)
                self._grants[index] = updated
                return DesktopApiResult(ok=True, data=updated)
        grant = ScopedAccessGrantDto(
            id=f"grant-{len(self._grants) + 1}",
            scope_type=command.scope_type,
            scope_id=command.scope_id,
            user_id=command.user_id,
            scope_role=command.scope_role,
            permission_codes=(f"{command.scope_type}.{command.scope_role}",),
            created_at=datetime(2026, 4, 24, 10, 0, 0),
        )
        self._grants.append(grant)
        return DesktopApiResult(ok=True, data=grant)

    def remove_scope_grant(self, command) -> DesktopApiResult[None]:
        original_count = len(self._grants)
        self._grants = [
            row
            for row in self._grants
            if not (
                row.scope_type == command.scope_type
                and row.scope_id == command.scope_id
                and row.user_id == command.user_id
            )
        ]
        if len(self._grants) == original_count:
            return DesktopApiResult(
                ok=False,
                error=DesktopApiError(
                    code="grant_not_found",
                    message="Scope grant was not found.",
                    category="not_found",
                ),
            )
        return DesktopApiResult(ok=True, data=None)


class _FakePlatformApprovalApi:
    def __init__(self, rows: tuple[ApprovalRequestDto, ...]) -> None:
        self._rows = list(rows)

    def list_requests(
        self,
        *,
        status=None,
        limit: int = 50,
    ) -> DesktopApiResult[tuple[ApprovalRequestDto, ...]]:
        rows = self._rows
        if status is not None:
            rows = [row for row in rows if row.status == status]
        return DesktopApiResult(ok=True, data=tuple(rows[:limit]))

    def approve_and_apply(self, command) -> DesktopApiResult[ApprovalRequestDto]:
        return self._update_status(command.request_id, ApprovalStatus.APPROVED, command.note)

    def reject(self, command) -> DesktopApiResult[ApprovalRequestDto]:
        return self._update_status(command.request_id, ApprovalStatus.REJECTED, command.note)

    def _update_status(self, request_id: str, status: ApprovalStatus, note: str | None) -> DesktopApiResult[ApprovalRequestDto]:
        for index, row in enumerate(self._rows):
            if row.id != request_id:
                continue
            updated = replace(row, status=status, decision_note=note)
            self._rows[index] = updated
            return DesktopApiResult(ok=True, data=updated)
        return DesktopApiResult(
            ok=False,
            error=DesktopApiError(
                code="request_not_found",
                message=f"Approval request '{request_id}' was not found.",
                category="not_found",
            ),
        )


class _FakePlatformAuditApi:
    def __init__(self, rows: tuple[AuditLogEntryDto, ...]) -> None:
        self._rows = rows

    def list_recent(self, *, limit: int = 25) -> DesktopApiResult[tuple[AuditLogEntryDto, ...]]:
        return DesktopApiResult(ok=True, data=self._rows[:limit])


class _FakePlatformSupportApi:
    def __init__(self) -> None:
        self._settings = SupportSettingsDto(
            update_channel="stable",
            update_auto_check=False,
            update_manifest_source="https://example.com/releases/manifest.json",
            theme_mode="light",
            governance_mode="off",
            app_version="1.0.0",
            support_email="support@example.com",
        )
        self._activity_by_trace: dict[str, list[SupportEventDto]] = {}
        self._incident_counter = 0

    def new_incident_id(self) -> str:
        self._incident_counter += 1
        return f"inc-support-{self._incident_counter}"

    def load_settings(self) -> DesktopApiResult[SupportSettingsDto]:
        return DesktopApiResult(ok=True, data=self._settings)

    def get_paths(self) -> DesktopApiResult[SupportPathsDto]:
        return DesktopApiResult(
            ok=True,
            data=SupportPathsDto(
                data_directory_path="C:/pm/data",
                data_directory_url="file:///C:/pm/data",
                logs_directory_path="C:/pm/data/logs",
                logs_directory_url="file:///C:/pm/data/logs",
                incidents_directory_path="C:/pm/data/incidents",
                incidents_directory_url="file:///C:/pm/data/incidents",
                events_file_path="C:/pm/data/logs/support-events.jsonl",
                events_file_url="file:///C:/pm/data/logs/support-events.jsonl",
            ),
        )

    def save_settings(self, command, *, trace_id: str | None = None) -> DesktopApiResult[SupportSettingsDto]:
        self._settings = replace(
            self._settings,
            update_channel=command.update_channel,
            update_auto_check=command.update_auto_check,
            update_manifest_source=command.update_manifest_source,
        )
        self._append_event(
            trace_id or "inc-support-1",
            "support.update.settings_saved",
            "Update settings saved.",
        )
        return DesktopApiResult(ok=True, data=self._settings)

    def check_for_updates(self, command, *, trace_id: str | None = None) -> DesktopApiResult[SupportUpdateStatusDto]:
        self.save_settings(command, trace_id=trace_id)
        trace = trace_id or "inc-support-1"
        dto = SupportUpdateStatusDto(
            status_label="Update Available",
            summary="Update available: 1.0.0 -> 1.2.0.",
            current_version="1.0.0",
            latest_version="1.2.0",
            channel=command.update_channel,
            update_available=True,
            can_open_download=True,
            download_url="https://example.com/downloads/pm-1.2.0.exe",
            notes="Improved QML workspace shell.",
            sha256="abc123",
        )
        self._append_event(trace, "support.update.available", dto.summary)
        return DesktopApiResult(ok=True, data=dto)

    def list_activity(
        self,
        *,
        trace_id: str | None = None,
        limit: int = 12,
    ) -> DesktopApiResult[tuple[SupportEventDto, ...]]:
        rows = self._activity_by_trace.get(trace_id or "", [])
        return DesktopApiResult(ok=True, data=tuple(rows[:limit]))

    def export_diagnostics(self, *, incident_id: str) -> DesktopApiResult[SupportBundleDto]:
        return self.export_diagnostics_to(
            incident_id=incident_id,
            output_path=f"C:/pm/data/pm_diagnostics_{incident_id}.zip",
        )

    def export_diagnostics_to(
        self,
        *,
        incident_id: str,
        output_path: str,
    ) -> DesktopApiResult[SupportBundleDto]:
        dto = SupportBundleDto(
            output_path=output_path,
            output_url="file:///" + output_path.replace("\\", "/"),
            files_added=4,
            warnings=("Database copy excluded from diagnostics bundle for security reasons.",),
        )
        self._append_event(incident_id, "support.diagnostics.exported", "Diagnostics bundle exported.")
        return DesktopApiResult(ok=True, data=dto)

    def create_incident_report(self, *, incident_id: str) -> DesktopApiResult[SupportBundleDto]:
        dto = SupportBundleDto(
            output_path=f"C:/pm/data/incidents/pm_incident_{incident_id}.zip",
            output_url=f"file:///C:/pm/data/incidents/pm_incident_{incident_id}.zip",
            files_added=5,
            warnings=(),
            support_email=self._settings.support_email,
        )
        self._append_event(incident_id, "support.incident.report_ready", "Incident report package is ready.")
        return DesktopApiResult(ok=True, data=dto)

    def install_available_update(self, command, *, trace_id: str | None = None) -> DesktopApiResult[SupportInstallLaunchDto]:
        trace = trace_id or "inc-support-1"
        self._append_event(trace, "support.update.handoff_started", "Update handoff launched; app will close.")
        return DesktopApiResult(
            ok=True,
            data=SupportInstallLaunchDto(
                latest_version="1.2.0",
                installer_path="C:/pm/data/updates/pm-1.2.0.exe",
                installer_url="file:///C:/pm/data/updates/pm-1.2.0.exe",
                handoff_script_path="C:/pm/data/updates/apply_update_1.ps1",
                handoff_script_url="file:///C:/pm/data/updates/apply_update_1.ps1",
            ),
        )

    def _append_event(self, trace_id: str, event_type: str, message: str) -> None:
        rows = self._activity_by_trace.setdefault(trace_id, [])
        rows.insert(
            0,
            SupportEventDto(
                timestamp_utc="2026-04-29T12:00:00+00:00",
                event_type=event_type,
                level="INFO",
                trace_id=trace_id,
                message=message,
                details_summary="",
            ),
        )
def _build_connected_platform_registry() -> SimpleNamespace:
    runtime_api = _FakePlatformRuntimeApi()
    site_rows = (
        SiteDto(
            id="site-1",
            organization_id="org-1",
            site_code="BER",
            name="Berlin Campus",
            description="Primary operating site",
            country="DE",
            region="Berlin",
            city="Berlin",
            address_line_1="Street 1",
            address_line_2="",
            postal_code="10115",
            timezone="Europe/Berlin",
            currency_code="EUR",
            site_type="office",
            status="active",
            default_calendar_id="cal-1",
            default_language="en",
            is_active=True,
            notes="",
            version=1,
        ),
        SiteDto(
            id="site-2",
            organization_id="org-1",
            site_code="DXB",
            name="Dubai Yard",
            description="Secondary site",
            country="AE",
            region="Dubai",
            city="Dubai",
            address_line_1="Street 2",
            address_line_2="",
            postal_code="00000",
            timezone="Asia/Dubai",
            currency_code="AED",
            site_type="yard",
            status="inactive",
            default_calendar_id="cal-2",
            default_language="en",
            is_active=False,
            notes="",
            version=1,
        ),
    )
    department_rows = (
        DepartmentDto(
            id="dep-1",
            organization_id="org-1",
            department_code="ENG",
            name="Engineering",
            description="Engineering",
            site_id="site-1",
            default_location_id=None,
            parent_department_id=None,
            department_type="functional",
            cost_center_code="CC-1",
            manager_employee_id=None,
            is_active=True,
            notes="",
            version=1,
        ),
        DepartmentDto(
            id="dep-2",
            organization_id="org-1",
            department_code="OPS",
            name="Operations",
            description="Operations",
            site_id="site-2",
            default_location_id=None,
            parent_department_id=None,
            department_type="functional",
            cost_center_code="CC-2",
            manager_employee_id=None,
            is_active=False,
            notes="",
            version=1,
        ),
    )
    location_rows = (
        DepartmentLocationReferenceDto(
            id="loc-1",
            organization_id="org-1",
            site_id="site-1",
            location_code="BLD-A",
            name="Building A",
            is_active=True,
        ),
        DepartmentLocationReferenceDto(
            id="loc-2",
            organization_id="org-1",
            site_id="site-2",
            location_code="YARD-1",
            name="Main Yard",
            is_active=True,
        ),
    )
    employee_rows = (
        EmployeeDto(
            id="emp-1",
            employee_code="E-001",
            full_name="Ada Lovelace",
            department_id="dep-1",
            department="Engineering",
            site_id="site-1",
            site_name="Berlin Campus",
            title="Engineer",
            employment_type="FULL_TIME",
            email="ada@example.com",
            phone=None,
            is_active=True,
            version=1,
        ),
        EmployeeDto(
            id="emp-2",
            employee_code="E-002",
            full_name="Grace Hopper",
            department_id="dep-2",
            department="Operations",
            site_id="site-2",
            site_name="Dubai Yard",
            title="Manager",
            employment_type="CONTRACTOR",
            email="grace@example.com",
            phone=None,
            is_active=False,
            version=1,
        ),
    )
    site_api = _FakePlatformSiteApi(runtime_api=runtime_api, rows=site_rows)
    department_api = _FakePlatformDepartmentApi(
        runtime_api=runtime_api,
        site_api=site_api,
        rows=department_rows,
        location_rows=location_rows,
    )
    employee_api = _FakePlatformEmployeeApi(employee_rows)
    role_rows = (
        RoleDto(
            id="role-1",
            name="admin",
            description="Platform administrators",
            is_system=True,
        ),
        RoleDto(
            id="role-2",
            name="viewer",
            description="Read-only observers",
            is_system=False,
        ),
    )
    user_rows = (
        UserDto(
            id="user-1",
            username="ada",
            display_name="Ada Lovelace",
            email="ada@example.com",
            identity_provider=None,
            federated_subject=None,
            is_active=True,
            failed_login_attempts=0,
            locked_until=None,
            last_login_at=None,
            last_login_auth_method=None,
            last_login_device_label=None,
            session_expires_at=None,
            session_timeout_minutes_override=None,
            must_change_password=False,
            version=1,
            role_names=("admin",),
        ),
        UserDto(
            id="user-2",
            username="grace",
            display_name="Grace Hopper",
            email="grace@example.com",
            identity_provider=None,
            federated_subject=None,
            is_active=False,
            failed_login_attempts=2,
            locked_until=datetime(2026, 4, 24, 9, 0, 0),
            last_login_at=None,
            last_login_auth_method=None,
            last_login_device_label=None,
            session_expires_at=datetime(2026, 4, 24, 12, 0, 0),
            session_timeout_minutes_override=None,
            must_change_password=True,
            version=1,
            role_names=("viewer",),
        ),
    )
    user_api = _FakePlatformUserApi(user_rows, role_rows)
    access_scope_types = (
        ScopeTypeChoiceDto(label="Project", value="project", enabled=True, supporting_text=""),
        ScopeTypeChoiceDto(label="Site", value="site", enabled=True, supporting_text=""),
        ScopeTypeChoiceDto(
            label="Storeroom",
            value="storeroom",
            enabled=False,
            supporting_text="Inventory & Procurement is disabled. Enable it before managing storeroom access.",
        ),
    )
    access_scope_targets = {
        "project": (
            ScopeTargetDto(
                id="project-1",
                label="Project Apollo",
                scope_type="project",
            ),
        ),
        "site": (
            ScopeTargetDto(
                id="site-1",
                label="BER - Berlin Campus",
                scope_type="site",
            ),
        ),
        "storeroom": (),
    }
    access_grants = (
        ScopedAccessGrantDto(
            id="grant-1",
            scope_type="project",
            scope_id="project-1",
            user_id="user-1",
            scope_role="manager",
            permission_codes=("project.manage", "project.read"),
            created_at=datetime(2026, 4, 24, 8, 15, 0),
        ),
        ScopedAccessGrantDto(
            id="grant-2",
            scope_type="site",
            scope_id="site-1",
            user_id="user-2",
            scope_role="viewer",
            permission_codes=("site.read",),
            created_at=datetime(2026, 4, 24, 8, 45, 0),
        ),
    )
    access_api = _FakePlatformAccessApi(
        scope_types=access_scope_types,
        scope_targets=access_scope_targets,
        grants=access_grants,
    )
    document_structure_rows = (
        DocumentStructureDto(
            id="structure-1",
            organization_id="org-1",
            structure_code="POL",
            name="Policies",
            description="Policy documents",
            parent_structure_id=None,
            object_scope="GENERAL",
            default_document_type="POLICY",
            sort_order=1,
            is_active=True,
            notes="",
            version=1,
        ),
        DocumentStructureDto(
            id="structure-2",
            organization_id="org-1",
            structure_code="PROC",
            name="Procedures",
            description="Procedure documents",
            parent_structure_id=None,
            object_scope="GENERAL",
            default_document_type="PROCEDURE",
            sort_order=2,
            is_active=True,
            notes="",
            version=1,
        ),
    )
    document_rows = (
        DocumentDto(
            id="doc-1",
            organization_id="org-1",
            document_code="DOC-001",
            title="Governance Charter",
            document_type="GENERAL",
            document_structure_id="structure-1",
            storage_kind="FILE_PATH",
            storage_uri="/docs/doc-1.pdf",
            file_name="doc-1.pdf",
            mime_type="application/pdf",
            source_system="desktop",
            uploaded_at=None,
            uploaded_by_user_id=None,
            effective_date=None,
            review_date=None,
            confidentiality_level="internal",
            business_version_label="1.0",
            is_current=True,
            notes="",
            is_active=True,
            version=1,
        ),
        DocumentDto(
            id="doc-2",
            organization_id="org-1",
            document_code="DOC-002",
            title="Archived Procedure",
            document_type="GENERAL",
            document_structure_id="structure-2",
            storage_kind="FILE_PATH",
            storage_uri="/docs/doc-2.pdf",
            file_name="doc-2.pdf",
            mime_type="application/pdf",
            source_system="desktop",
            uploaded_at=None,
            uploaded_by_user_id=None,
            effective_date=None,
            review_date=None,
            confidentiality_level="internal",
            business_version_label="0.9",
            is_current=False,
            notes="",
            is_active=True,
            version=1,
        ),
    )
    document_link_rows = (
        DocumentLinkDto(
            id="link-1",
            organization_id="org-1",
            document_id="doc-1",
            module_code="project_management",
            entity_type="task",
            entity_id="task-42",
            link_role="attachment",
        ),
        DocumentLinkDto(
            id="link-2",
            organization_id="org-1",
            document_id="doc-1",
            module_code="maintenance",
            entity_type="asset",
            entity_id="asset-7",
            link_role="reference",
        ),
    )
    document_api = _FakePlatformDocumentApi(
        runtime_api=runtime_api,
        rows=document_rows,
        structure_rows=document_structure_rows,
        link_rows=document_link_rows,
    )
    party_rows = (
        PartyDto(
            id="party-1",
            organization_id="org-1",
            party_code="SUP-001",
            party_name="Acme Supply",
            party_type="SUPPLIER",
            legal_name="Acme Supply Ltd",
            contact_name="John Doe",
            email="contact@acme.example",
            phone="123",
            country="DE",
            city="Berlin",
            address_line_1="Street 3",
            address_line_2="",
            postal_code="10115",
            website="https://acme.example",
            tax_registration_number="TAX-1",
            external_reference="EXT-1",
            is_active=True,
            created_at=None,
            updated_at=None,
            notes="",
            version=1,
        ),
        PartyDto(
            id="party-2",
            organization_id="org-1",
            party_code="CUS-001",
            party_name="Northwind",
            party_type="CUSTOMER",
            legal_name="Northwind GmbH",
            contact_name="Jane Doe",
            email="contact@northwind.example",
            phone="456",
            country="DE",
            city="Hamburg",
            address_line_1="Street 4",
            address_line_2="",
            postal_code="20095",
            website="https://northwind.example",
            tax_registration_number="TAX-2",
            external_reference="EXT-2",
            is_active=False,
            created_at=None,
            updated_at=None,
            notes="",
            version=1,
        ),
    )
    party_api = _FakePlatformPartyApi(runtime_api=runtime_api, rows=party_rows)
    approval_rows = (
        ApprovalRequestDto(
            id="approval-1",
            request_type="budget_change",
            entity_type="project",
            entity_id="project-1",
            project_id="project-1",
            status=ApprovalStatus.PENDING,
            module_label="Project Management",
            context_label="Project Apollo",
            display_label="Change Budget",
            requested_by_username="ada",
            requested_at=datetime(2026, 4, 24, 7, 30, 0),
        ),
        ApprovalRequestDto(
            id="approval-2",
            request_type="baseline_publish",
            entity_type="project_baseline",
            entity_id="baseline-1",
            project_id="project-1",
            status=ApprovalStatus.APPROVED,
            module_label="Project Management",
            context_label="Project Apollo",
            display_label="Publish Baseline",
            requested_by_username="grace",
            requested_at=datetime(2026, 4, 24, 8, 0, 0),
        ),
        ApprovalRequestDto(
            id="approval-3",
            request_type="scope_change",
            entity_type="task",
            entity_id="task-1",
            project_id="project-1",
            status=ApprovalStatus.REJECTED,
            module_label="Project Management",
            context_label="Project Apollo",
            display_label="Scope Change",
            requested_by_username="grace",
            requested_at=datetime(2026, 4, 24, 8, 30, 0),
        ),
    )
    audit_rows = (
        AuditLogEntryDto(
            id="audit-1",
            occurred_at=datetime(2026, 4, 24, 8, 0, 0),
            actor_user_id="user-1",
            actor_username="ada",
            action="approve",
            entity_type="project",
            entity_id="project-1",
            project_id="project-1",
            project_label="Project Apollo",
            entity_label="Project",
            details_label="request_type=budget_change",
        ),
        AuditLogEntryDto(
            id="audit-2",
            occurred_at=datetime(2026, 4, 24, 9, 0, 0),
            actor_user_id="user-2",
            actor_username="grace",
            action="reject",
            entity_type="task",
            entity_id="task-1",
            project_id="project-1",
            project_label="Project Apollo",
            entity_label="Task",
            details_label="request_type=scope_change",
        ),
    )

    return SimpleNamespace(
        platform_runtime=runtime_api,
        platform_site=site_api,
        platform_department=department_api,
        platform_employee=employee_api,
        platform_access=access_api,
        platform_user=user_api,
        platform_document=document_api,
        platform_party=party_api,
        platform_approval=_FakePlatformApprovalApi(approval_rows),
        platform_audit=_FakePlatformAuditApi(audit_rows),
        platform_support=_FakePlatformSupportApi(),
    )


def test_platform_runtime_presenter_uses_desktop_api_context() -> None:
    presenter = PlatformRuntimePresenter(_FakePlatformRuntimeApi())

    overview = presenter.build_overview()

    assert overview.title == "Enterprise Runtime"
    assert overview.subtitle == "TechAsh | 2 modules licensed"
    assert overview.status_label == "Connected"
    assert [(metric.label, metric.value) for metric in overview.metrics] == [
        ("Active organization", "TechAsh"),
        ("Enabled modules", "1"),
        ("Licensed modules", "2"),
        ("Available modules", "3"),
    ]


def test_platform_runtime_presenter_has_preview_state_without_api() -> None:
    presenter = PlatformRuntimePresenter()

    overview = presenter.build_overview()

    assert overview.status_label == "Preview"
    assert overview.metrics[0].supporting_text == "API not connected"


def test_platform_workspace_catalog_falls_back_to_direct_runtime_api() -> None:
    catalog = PlatformWorkspaceCatalog(
        _FakePlatformRuntimeApi(),
        desktop_api_registry=SimpleNamespace(),
    )

    overview = catalog.runtimeOverview()

    assert overview["statusLabel"] == "Connected"
    assert overview["metrics"][0]["value"] == "TechAsh"


def test_platform_workspace_catalog_exposes_qml_safe_maps() -> None:
    catalog = PlatformWorkspaceCatalog(_FakePlatformRuntimeApi())

    workspace = catalog.workspace("platform.admin")
    overview = catalog.runtimeOverview()

    assert workspace == {
        "routeId": "platform.admin",
        "title": "Admin Console",
        "summary": "Platform / Administration",
    }
    assert overview["statusLabel"] == "Connected"
    assert overview["metrics"][0] == {
        "label": "Active organization",
        "value": "TechAsh",
        "supportingText": "Current platform context",
    }


def test_platform_workspace_catalog_exposes_grouped_platform_overviews() -> None:
    catalog = PlatformWorkspaceCatalog(desktop_api_registry=_build_connected_platform_registry())

    admin = catalog.adminOverview()
    control = catalog.controlOverview()
    settings = catalog.settingsOverview()

    assert admin["statusLabel"] == "Connected"
    assert [(metric["label"], metric["value"]) for metric in admin["metrics"]] == [
        ("Organizations", "2"),
        ("Sites", "1"),
        ("Departments", "1"),
        ("Employees", "1"),
        ("Users", "1"),
        ("Documents", "1"),
    ]
    assert [section["title"] for section in admin["sections"]] == [
        "Runtime Context",
        "Identity And Workforce",
        "Master Data Coverage",
    ]
    assert admin["sections"][0]["rows"][0]["value"] == "TechAsh"
    assert admin["sections"][2]["rows"][0]["supportingText"] == "Berlin Campus, Dubai Yard"

    assert control["statusLabel"] == "Connected"
    assert [(metric["label"], metric["value"]) for metric in control["metrics"]] == [
        ("Pending approvals", "1"),
        ("Approved", "1"),
        ("Rejected", "1"),
        ("Audit entries", "2"),
    ]
    assert control["sections"][0]["rows"][0] == {
        "label": "Change Budget",
        "value": "Pending",
        "supportingText": "Project Apollo",
    }
    assert control["sections"][1]["rows"][0]["label"] == "approve"

    assert settings["statusLabel"] == "Connected"
    assert [(metric["label"], metric["value"]) for metric in settings["metrics"]] == [
        ("Licensed modules", "2"),
        ("Enabled modules", "1"),
        ("Planned modules", "1"),
        ("Organizations", "2"),
    ]
    assert [section["title"] for section in settings["sections"]] == [
        "Organization Profiles",
        "Module Catalog",
        "Platform Capabilities",
    ]
    assert settings["sections"][0]["rows"][0]["label"] == "TechAsh"
    assert settings["sections"][1]["rows"][0]["label"] == "Project Management"
    assert settings["sections"][2]["rows"][0]["supportingText"] == "Governed approval workflows"


def test_platform_workspace_catalog_exposes_control_and_settings_action_lists() -> None:
    catalog = PlatformWorkspaceCatalog(desktop_api_registry=_build_connected_platform_registry())

    approval_queue = catalog.approvalQueue()
    audit_feed = catalog.auditFeed()
    module_entitlements = catalog.moduleEntitlements()
    organization_profiles = catalog.organizationProfiles()

    assert approval_queue["title"] == "Approval Queue"
    assert approval_queue["items"][0]["title"] == "Change Budget"
    assert approval_queue["items"][0]["canPrimaryAction"] is True
    assert approval_queue["items"][0]["state"]["decisionNote"] == ""
    assert approval_queue["items"][1]["canPrimaryAction"] is False

    assert audit_feed["title"] == "Recent Audit Feed"
    assert audit_feed["items"][0]["statusLabel"] == "Project"

    assert module_entitlements["title"] == "Module Entitlements"
    assert module_entitlements["items"][0]["title"] == "Project Management"
    assert module_entitlements["items"][0]["canPrimaryAction"] is True
    assert module_entitlements["items"][0]["canTertiaryAction"] is True
    assert module_entitlements["items"][2]["canPrimaryAction"] is False
    assert module_entitlements["items"][2]["canTertiaryAction"] is False

    assert organization_profiles["title"] == "Organization Profiles"
    assert organization_profiles["items"][0]["title"] == "TechAsh"
    assert organization_profiles["items"][0]["statusLabel"] == "Active"


def test_platform_workspace_catalog_exposes_admin_action_lists() -> None:
    catalog = PlatformWorkspaceCatalog(desktop_api_registry=_build_connected_platform_registry())

    organizations = catalog.adminWorkspace.organizations
    sites = catalog.adminWorkspace.sites
    departments = catalog.adminWorkspace.departments
    employees = catalog.adminWorkspace.employees
    users = catalog.adminWorkspace.users
    parties = catalog.adminWorkspace.parties
    documents = catalog.adminWorkspace.documents
    selected_document = catalog.adminWorkspace.selectedDocument
    document_preview = catalog.adminWorkspace.documentPreview
    document_links = catalog.adminWorkspace.documentLinks
    document_structures = catalog.adminWorkspace.documentStructures
    access_workspace = catalog.adminAccessWorkspace

    assert organizations["title"] == "Organizations"
    assert organizations["items"][0]["title"] == "TechAsh"
    assert organizations["items"][1]["canSecondaryAction"] is True

    assert sites["title"] == "Sites"
    assert sites["items"][0]["title"] == "Berlin Campus"

    assert departments["title"] == "Departments"
    assert departments["items"][0]["supportingText"] == "Site: Berlin Campus | Location: No default location"

    assert employees["title"] == "Employees"
    assert employees["items"][0]["metaText"].startswith("Full Time")

    assert users["title"] == "Users"
    assert users["items"][0]["supportingText"] == "Admin"

    assert parties["title"] == "Parties"
    assert parties["items"][0]["subtitle"] == "SUP-001 | Supplier"

    assert documents["title"] == "Documents"
    assert documents["items"][0]["supportingText"] == "POL - Policies | Version 1.0 | Current"
    assert selected_document["title"] == "Governance Charter"
    assert selected_document["badges"][2]["value"] == "Local file missing"
    assert document_preview["statusLabel"] == "Local file missing"
    assert document_preview["canOpen"] is False
    assert document_links["title"] == "Linked Records"
    assert len(document_links["items"]) == 2
    assert document_links["items"][0]["statusLabel"] == "Attachment"
    assert document_structures["title"] == "Document Structures"
    assert document_structures["items"][0]["title"] == "Policies"

    assert len(catalog.adminWorkspace.organizationEditorOptions["moduleOptions"]) == 3
    assert len(catalog.adminWorkspace.departmentEditorOptions["siteOptions"]) == 1
    assert len(catalog.adminWorkspace.departmentEditorOptions["locationOptions"]) == 2
    assert len(catalog.adminWorkspace.employeeEditorOptions["departmentOptions"]) == 1
    assert len(catalog.adminWorkspace.userEditorOptions["roleOptions"]) == 2
    assert len(catalog.adminWorkspace.partyEditorOptions["typeOptions"]) >= 3
    assert len(catalog.adminWorkspace.documentEditorOptions["structureOptions"]) == 2
    assert len(catalog.adminWorkspace.documentStructureEditorOptions["parentOptions"]) == 2
    assert len(access_workspace.scopeTypeOptions) == 3
    assert access_workspace.scopeGrants["items"][0]["title"] == "Ada Lovelace"
    assert access_workspace.securityUsers["items"][1]["statusLabel"] == "Locked"


def test_platform_workspace_controllers_hold_common_state_fields() -> None:
    catalog = PlatformWorkspaceCatalog(desktop_api_registry=_build_connected_platform_registry())

    assert catalog.adminWorkspace.isLoading is False
    assert catalog.adminWorkspace.isBusy is False
    assert catalog.adminWorkspace.errorMessage == ""
    assert catalog.adminWorkspace.organizations["items"][0]["title"] == "TechAsh"
    assert catalog.adminWorkspace.users["items"][0]["title"] == "Ada Lovelace"
    assert catalog.adminAccessWorkspace.scopeHint.startswith("Assign scoped access")
    assert catalog.controlWorkspace.feedbackMessage == ""
    assert catalog.settingsWorkspace.emptyState == ""
    assert len(catalog.settingsWorkspace.lifecycleOptions) == 4
    assert catalog.controlWorkspace.approvalQueue["items"][0]["title"] == "Change Budget"
    assert catalog.settingsWorkspace.moduleEntitlements["items"][0]["title"] == "Project Management"


def test_platform_workspace_catalog_exposes_support_workspace() -> None:
    catalog = PlatformWorkspaceCatalog(desktop_api_registry=_build_connected_platform_registry())

    support_workspace = catalog.adminSupportWorkspace

    assert support_workspace.incidentId == "inc-support-1"
    assert support_workspace.supportSettings["updateChannel"] == "stable"
    assert support_workspace.supportPaths["logsDirectoryPath"] == "C:/pm/data/logs"
    assert support_workspace.updateStatus["statusLabel"] == "Ready"
    assert support_workspace.activityFeed["title"] == "Support Activity"
    assert support_workspace.bundleState["lastDiagnosticsPath"] == ""


def test_platform_workspace_catalog_runs_control_and_settings_actions() -> None:
    catalog = PlatformWorkspaceCatalog(desktop_api_registry=_build_connected_platform_registry())

    approve_result = catalog.approveRequestWithNote("approval-1", "Budget aligned with governance.")
    enable_result = catalog.toggleModuleEnabled("maintenance")
    lifecycle_result = catalog.changeModuleLifecycleStatus("project_management", "suspended")

    assert approve_result == {
        "ok": True,
        "category": "",
        "code": "",
        "message": "Approval request approved and applied.",
    }
    assert enable_result == {
        "ok": True,
        "category": "",
        "code": "",
        "message": "Module runtime state updated.",
    }
    assert lifecycle_result == {
        "ok": True,
        "category": "",
        "code": "",
        "message": "Module lifecycle status updated.",
    }

    approval_queue = catalog.approvalQueue()
    settings_overview = catalog.settingsOverview()
    module_entitlements = catalog.moduleEntitlements()
    project_management = {
        item["id"]: item
        for item in module_entitlements["items"]
    }["project_management"]
    maintenance = {
        item["id"]: item
        for item in module_entitlements["items"]
    }["maintenance"]

    assert approval_queue["items"][0]["statusLabel"] == "Approved"
    assert approval_queue["items"][0]["canPrimaryAction"] is False
    assert approval_queue["items"][0]["state"]["decisionNote"] == "Budget aligned with governance."
    assert "Decision note: Budget aligned with governance." in approval_queue["items"][0]["metaText"]
    assert settings_overview["metrics"][1]["value"] == "1"
    assert maintenance["subtitle"].endswith("Enabled")
    assert project_management["statusLabel"] == "Suspended"
    assert project_management["state"]["runtimeEnabled"] is False
    assert project_management["canSecondaryAction"] is False
    assert catalog.controlWorkspace.feedbackMessage == "Approval request approved and applied."
    assert catalog.settingsWorkspace.feedbackMessage == "Module lifecycle status updated."
    assert catalog.settingsWorkspace.errorMessage == ""


def test_platform_workspace_catalog_runs_support_actions() -> None:
    catalog = PlatformWorkspaceCatalog(desktop_api_registry=_build_connected_platform_registry())

    support_workspace = catalog.adminSupportWorkspace
    save_result = support_workspace.saveSettings(
        {
            "updateChannel": "beta",
            "updateAutoCheck": True,
            "updateManifestSource": "https://example.com/releases/beta-manifest.json",
        }
    )
    check_result = support_workspace.checkForUpdates(
        {
            "updateChannel": "beta",
            "updateAutoCheck": True,
            "updateManifestSource": "https://example.com/releases/beta-manifest.json",
        }
    )
    diagnostics_result = support_workspace.exportDiagnosticsTo("C:/pm/data/custom_support_diagnostics.zip")
    report_result = support_workspace.reportIncident()
    install_result = support_workspace.installAvailableUpdate(
        {
            "updateChannel": "beta",
            "updateAutoCheck": True,
            "updateManifestSource": "https://example.com/releases/beta-manifest.json",
        }
    )

    assert save_result == {
        "ok": True,
        "category": "",
        "code": "",
        "message": "Support settings saved.",
    }
    assert check_result == {
        "ok": True,
        "category": "",
        "code": "",
        "message": "Update check completed.",
    }
    assert diagnostics_result == {
        "ok": True,
        "category": "",
        "code": "",
        "message": "Diagnostics bundle created.",
    }
    assert report_result == {
        "ok": True,
        "category": "",
        "code": "",
        "message": "Incident report package created.",
    }
    assert install_result == {
        "ok": True,
        "category": "",
        "code": "",
        "message": "Update install handoff launched.",
    }

    assert support_workspace.supportSettings["updateChannel"] == "beta"
    assert support_workspace.supportSettings["updateAutoCheck"] is True
    assert support_workspace.updateStatus["statusLabel"] == "Update Available"
    assert support_workspace.updateStatus["latestVersion"] == "1.2.0"
    assert support_workspace.bundleState["lastDiagnosticsPath"] == "C:/pm/data/custom_support_diagnostics.zip"
    assert support_workspace.bundleState["lastIncidentReportPath"].endswith(".zip")
    assert support_workspace.bundleState["supportEmail"] == "support@example.com"
    assert support_workspace.activityFeed["items"][0]["title"] == "Update handoff launched; app will close."
    assert support_workspace.feedbackMessage == "Update install handoff launched."
    assert support_workspace.errorMessage == ""


def test_platform_workspace_catalog_runs_admin_actions() -> None:
    catalog = PlatformWorkspaceCatalog(desktop_api_registry=_build_connected_platform_registry())

    organization_result = catalog.adminWorkspace.createOrganization(
        {
            "organizationCode": "QML",
            "displayName": "QML Labs",
            "timezoneName": "Europe/Berlin",
            "baseCurrency": "EUR",
            "isActive": False,
            "initialModuleCodes": ["project_management"],
        }
    )
    activate_result = catalog.adminWorkspace.setActiveOrganization("org-2")
    site_result = catalog.adminWorkspace.createSite(
        {
            "siteCode": "HAM",
            "name": "Hamburg Hub",
            "description": "Logistics hub",
            "city": "Hamburg",
            "country": "DE",
            "timezoneName": "Europe/Berlin",
            "currencyCode": "EUR",
            "siteType": "office",
            "status": "active",
            "notes": "",
            "isActive": True,
        }
    )
    department_result = catalog.adminWorkspace.toggleDepartmentActive("dep-2")
    employee_result = catalog.adminWorkspace.createEmployee(
        {
            "employeeCode": "E-003",
            "fullName": "Katherine Johnson",
            "departmentId": "dep-1",
            "departmentName": "Engineering",
            "siteId": "site-1",
            "siteName": "Berlin Campus",
            "title": "Analyst",
            "employmentType": "FULL_TIME",
            "email": "katherine@example.com",
            "phone": "555-0100",
            "isActive": True,
        }
    )
    user_result = catalog.adminWorkspace.createUser(
        {
            "username": "katherine",
            "displayName": "Katherine Johnson",
            "email": "katherine@example.com",
            "password": "secret",
            "roleNames": ["viewer"],
            "isActive": True,
        }
    )
    party_result = catalog.adminWorkspace.createParty(
        {
            "partyCode": "VEN-100",
            "partyName": "Orbit Supply",
            "partyType": "VENDOR",
            "contactName": "Helen Morris",
            "email": "orbit@example.com",
            "country": "DE",
            "city": "Munich",
            "isActive": True,
        }
    )
    document_result = catalog.adminWorkspace.createDocument(
        {
            "documentCode": "DOC-003",
            "title": "Safety Policy",
            "documentType": "POLICY",
            "documentStructureId": "structure-1",
            "storageKind": "FILE_PATH",
            "storageUri": "/docs/doc-3.pdf",
            "fileName": "doc-3.pdf",
            "mimeType": "application/pdf",
            "sourceSystem": "desktop",
            "confidentialityLevel": "internal",
            "businessVersionLabel": "2.0",
            "isCurrent": True,
            "isActive": True,
        }
    )

    assert organization_result == {
        "ok": True,
        "category": "",
        "code": "",
        "message": "Organization created.",
    }
    assert activate_result == {
        "ok": True,
        "category": "",
        "code": "",
        "message": "Organization activated.",
    }
    assert site_result == {
        "ok": True,
        "category": "",
        "code": "",
        "message": "Site created.",
    }
    assert department_result == {
        "ok": True,
        "category": "",
        "code": "",
        "message": "Department active state updated.",
    }
    assert employee_result == {
        "ok": True,
        "category": "",
        "code": "",
        "message": "Employee created.",
    }
    assert user_result == {
        "ok": True,
        "category": "",
        "code": "",
        "message": "User created.",
    }
    assert party_result == {
        "ok": True,
        "category": "",
        "code": "",
        "message": "Party created.",
    }
    assert document_result == {
        "ok": True,
        "category": "",
        "code": "",
        "message": "Document created.",
    }

    organization_titles = [item["title"] for item in catalog.adminWorkspace.organizations["items"]]
    site_titles = [item["title"] for item in catalog.adminWorkspace.sites["items"]]
    employee_titles = [item["title"] for item in catalog.adminWorkspace.employees["items"]]
    user_titles = [item["title"] for item in catalog.adminWorkspace.users["items"]]
    party_titles = [item["title"] for item in catalog.adminWorkspace.parties["items"]]
    document_titles = [item["title"] for item in catalog.adminWorkspace.documents["items"]]
    department_by_id = {
        item["id"]: item
        for item in catalog.adminWorkspace.departments["items"]
    }

    assert "QML Labs" in organization_titles
    assert catalog.adminWorkspace.organizations["items"][1]["statusLabel"] == "Active"
    assert "Hamburg Hub" in site_titles
    assert department_by_id["dep-2"]["statusLabel"] == "Active"
    assert "Katherine Johnson" in employee_titles
    assert "Katherine Johnson" in user_titles
    assert "Orbit Supply" in party_titles
    assert "Safety Policy" in document_titles
    assert catalog.adminWorkspace.feedbackMessage == "Document created."


def test_platform_workspace_controllers_store_validation_errors() -> None:
    catalog = PlatformWorkspaceCatalog(desktop_api_registry=_build_connected_platform_registry())

    result = catalog.toggleModuleLicensed("inventory")

    assert result["ok"] is False
    assert result["category"] == "validation"
    assert "planned" in result["message"].lower()
    assert "planned" in catalog.settingsWorkspace.errorMessage.lower()


def test_platform_workspace_catalog_updates_extended_admin_actions() -> None:
    catalog = PlatformWorkspaceCatalog(desktop_api_registry=_build_connected_platform_registry())

    update_user_result = catalog.adminWorkspace.updateUser(
        {
            "userId": "user-2",
            "username": "grace",
            "displayName": "Grace Hopper",
            "email": "grace@example.com",
            "password": "updated-secret",
            "roleNames": ["admin"],
            "currentRoleNames": ["viewer"],
            "isActive": True,
            "currentIsActive": False,
        }
    )
    toggle_party_result = catalog.adminWorkspace.togglePartyActive("party-2")
    toggle_document_result = catalog.adminWorkspace.toggleDocumentActive("doc-2")

    assert update_user_result == {
        "ok": True,
        "category": "",
        "code": "",
        "message": "User updated.",
    }
    assert toggle_party_result == {
        "ok": True,
        "category": "",
        "code": "",
        "message": "Party active state updated.",
    }
    assert toggle_document_result == {
        "ok": True,
        "category": "",
        "code": "",
        "message": "Document active state updated.",
    }

    user_by_id = {item["id"]: item for item in catalog.adminWorkspace.users["items"]}
    party_by_id = {item["id"]: item for item in catalog.adminWorkspace.parties["items"]}
    document_by_id = {item["id"]: item for item in catalog.adminWorkspace.documents["items"]}

    assert user_by_id["user-2"]["statusLabel"] == "Locked"
    assert user_by_id["user-2"]["state"]["isActive"] is True
    assert user_by_id["user-2"]["supportingText"] == "Admin"
    assert party_by_id["party-2"]["statusLabel"] == "Active"
    assert document_by_id["doc-2"]["state"]["isActive"] is False
    assert catalog.adminWorkspace.feedbackMessage == "Document active state updated."


def test_platform_workspace_catalog_can_switch_document_focus() -> None:
    catalog = PlatformWorkspaceCatalog(desktop_api_registry=_build_connected_platform_registry())

    catalog.adminWorkspace.selectDocument("doc-2")

    assert catalog.adminWorkspace.selectedDocument["title"] == "Archived Procedure"
    assert catalog.adminWorkspace.selectedDocument["summary"].endswith("0 linked records")
    assert catalog.adminWorkspace.documentLinks["items"] == []
    assert catalog.adminWorkspace.documentLinks["emptyState"] == "No linked records yet."
    assert catalog.adminWorkspace.documentPreview["statusLabel"] == "Local file missing"


def test_platform_workspace_catalog_runs_document_management_actions() -> None:
    catalog = PlatformWorkspaceCatalog(desktop_api_registry=_build_connected_platform_registry())

    create_structure_result = catalog.adminWorkspace.createDocumentStructure(
        {
            "structureCode": "CERT",
            "name": "Certificates",
            "description": "Compliance certificates",
            "parentStructureId": "",
            "objectScope": "GENERAL",
            "defaultDocumentType": "CERTIFICATE",
            "sortOrder": 3,
            "notes": "",
            "isActive": True,
        }
    )
    update_structure_result = catalog.adminWorkspace.updateDocumentStructure(
        {
            "structureId": "structure-2",
            "expectedVersion": 1,
            "structureCode": "PROC",
            "name": "Operating Procedures",
            "description": "Procedure documents",
            "parentStructureId": "",
            "objectScope": "GENERAL",
            "defaultDocumentType": "PROCEDURE",
            "sortOrder": 2,
            "notes": "",
            "isActive": True,
        }
    )
    toggle_structure_result = catalog.adminWorkspace.toggleDocumentStructureActive("structure-2")
    catalog.adminWorkspace.selectDocument("doc-2")
    add_link_result = catalog.adminWorkspace.addDocumentLink(
        {
            "documentId": "doc-2",
            "moduleCode": "inventory_procurement",
            "entityType": "item",
            "entityId": "item-9",
            "linkRole": "reference",
        }
    )
    remove_link_result = catalog.adminWorkspace.removeDocumentLink(
        catalog.adminWorkspace.documentLinks["items"][0]["id"]
    )

    assert create_structure_result == {
        "ok": True,
        "category": "",
        "code": "",
        "message": "Document structure created.",
    }
    assert update_structure_result == {
        "ok": True,
        "category": "",
        "code": "",
        "message": "Document structure updated.",
    }
    assert toggle_structure_result == {
        "ok": True,
        "category": "",
        "code": "",
        "message": "Document structure active state updated.",
    }
    assert add_link_result == {
        "ok": True,
        "category": "",
        "code": "",
        "message": "Document link added.",
    }
    assert remove_link_result == {
        "ok": True,
        "category": "",
        "code": "",
        "message": "Document link removed.",
    }

    structure_titles = [item["title"] for item in catalog.adminWorkspace.documentStructures["items"]]
    structure_by_id = {
        item["id"]: item
        for item in catalog.adminWorkspace.documentStructures["items"]
    }

    assert "Certificates" in structure_titles
    assert structure_by_id["structure-2"]["title"] == "Operating Procedures"
    assert structure_by_id["structure-2"]["statusLabel"] == "Inactive"
    assert catalog.adminWorkspace.documentLinks["items"] == []
    assert catalog.adminWorkspace.feedbackMessage == "Document link removed."


def test_platform_workspace_catalog_runs_access_security_actions() -> None:
    catalog = PlatformWorkspaceCatalog(desktop_api_registry=_build_connected_platform_registry())

    catalog.adminAccessWorkspace.setScopeType("site")
    assign_result = catalog.adminAccessWorkspace.assignMembership()
    remove_result = catalog.adminAccessWorkspace.removeMembership("user-2")
    unlock_result = catalog.adminAccessWorkspace.unlockUser("user-2")
    revoke_result = catalog.adminAccessWorkspace.revokeSessions("user-2")

    assert assign_result == {
        "ok": True,
        "category": "",
        "code": "",
        "message": "Access grant assigned.",
    }
    assert remove_result == {
        "ok": True,
        "category": "",
        "code": "",
        "message": "Access grant removed.",
    }
    assert unlock_result == {
        "ok": True,
        "category": "",
        "code": "",
        "message": "User account unlocked.",
    }
    assert revoke_result == {
        "ok": True,
        "category": "",
        "code": "",
        "message": "User sessions revoked.",
    }

    grants = catalog.adminAccessWorkspace.scopeGrants
    security_users = {
        item["id"]: item
        for item in catalog.adminAccessWorkspace.securityUsers["items"]
    }

    assert [item["title"] for item in grants["items"]] == ["Ada Lovelace"]
    assert security_users["user-2"]["statusLabel"] == "Inactive"
    assert catalog.adminAccessWorkspace.feedbackMessage == "User sessions revoked."

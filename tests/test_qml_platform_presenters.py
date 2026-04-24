from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from types import SimpleNamespace

from src.api.desktop.platform.models import (
    ApprovalRequestDto,
    ApprovalStatus,
    AuditLogEntryDto,
    DepartmentDto,
    DesktopApiError,
    DesktopApiResult,
    DocumentDto,
    EmployeeDto,
    ModuleDto,
    ModuleEntitlementDto,
    OrganizationDto,
    PartyDto,
    PlatformCapabilityDto,
    PlatformRuntimeContextDto,
    SiteDto,
    UserDto,
)
from src.ui_qml.platform.context import PlatformWorkspaceCatalog
from src.ui_qml.platform.presenters import PlatformRuntimePresenter


def _organization(
    *,
    organization_id: str,
    code: str,
    display_name: str,
) -> OrganizationDto:
    return OrganizationDto(
        id=organization_id,
        organization_code=code,
        display_name=display_name,
        timezone_name="UTC",
        base_currency="EUR",
        is_active=True,
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
        self._organizations = (
            _organization(organization_id="org-1", code="ORG", display_name="TechAsh"),
            _organization(organization_id="org-2", code="OPS", display_name="Operations"),
        )
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
        self._runtime_context = PlatformRuntimeContextDto(
            context_label="Enterprise Runtime",
            shell_summary="2 modules licensed",
            active_organization=self._organizations[0],
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
        return DesktopApiResult(ok=True, data=self._organizations)

    def list_modules(self) -> DesktopApiResult[tuple[ModuleDto, ...]]:
        return DesktopApiResult(ok=True, data=self._modules)

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


def _result(rows):
    return DesktopApiResult(ok=True, data=tuple(rows))


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
            session_expires_at=None,
            session_timeout_minutes_override=None,
            must_change_password=True,
            version=1,
            role_names=("viewer",),
        ),
    )
    document_rows = (
        DocumentDto(
            id="doc-1",
            organization_id="org-1",
            document_code="DOC-001",
            title="Governance Charter",
            document_type="GENERAL",
            document_structure_id=None,
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
            document_structure_id=None,
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
        platform_site=SimpleNamespace(list_sites=lambda *, active_only=None: _result(site_rows)),
        platform_department=SimpleNamespace(
            list_departments=lambda *, active_only=None: _result(department_rows)
        ),
        platform_employee=SimpleNamespace(
            list_employees=lambda *, active_only=None: _result(employee_rows)
        ),
        platform_user=SimpleNamespace(list_users=lambda: _result(user_rows)),
        platform_document=SimpleNamespace(
            list_documents=lambda *, active_only=None: _result(document_rows)
        ),
        platform_party=SimpleNamespace(list_parties=lambda *, active_only=None: _result(party_rows)),
        platform_approval=_FakePlatformApprovalApi(approval_rows),
        platform_audit=_FakePlatformAuditApi(audit_rows),
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
    assert approval_queue["items"][1]["canPrimaryAction"] is False

    assert audit_feed["title"] == "Recent Audit Feed"
    assert audit_feed["items"][0]["statusLabel"] == "Project"

    assert module_entitlements["title"] == "Module Entitlements"
    assert module_entitlements["items"][0]["title"] == "Project Management"
    assert module_entitlements["items"][0]["canPrimaryAction"] is True
    assert module_entitlements["items"][2]["canPrimaryAction"] is False

    assert organization_profiles["title"] == "Organization Profiles"
    assert organization_profiles["items"][0]["title"] == "TechAsh"
    assert organization_profiles["items"][0]["statusLabel"] == "Active"


def test_platform_workspace_controllers_hold_common_state_fields() -> None:
    catalog = PlatformWorkspaceCatalog(desktop_api_registry=_build_connected_platform_registry())

    assert catalog.adminWorkspace.isLoading is False
    assert catalog.adminWorkspace.isBusy is False
    assert catalog.adminWorkspace.errorMessage == ""
    assert catalog.controlWorkspace.feedbackMessage == ""
    assert catalog.settingsWorkspace.emptyState == ""
    assert catalog.controlWorkspace.approvalQueue["items"][0]["title"] == "Change Budget"
    assert catalog.settingsWorkspace.moduleEntitlements["items"][0]["title"] == "Project Management"


def test_platform_workspace_catalog_runs_control_and_settings_actions() -> None:
    catalog = PlatformWorkspaceCatalog(desktop_api_registry=_build_connected_platform_registry())

    approve_result = catalog.approveRequest("approval-1")
    enable_result = catalog.toggleModuleEnabled("maintenance")
    planned_result = catalog.toggleModuleLicensed("inventory")

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
    assert planned_result["ok"] is False
    assert planned_result["category"] == "validation"
    assert "planned" in planned_result["message"].lower()

    approval_queue = catalog.approvalQueue()
    settings_overview = catalog.settingsOverview()
    module_entitlements = catalog.moduleEntitlements()

    assert approval_queue["items"][0]["statusLabel"] == "Approved"
    assert approval_queue["items"][0]["canPrimaryAction"] is False
    assert settings_overview["metrics"][1]["value"] == "2"
    assert module_entitlements["items"][1]["subtitle"].endswith("Enabled")
    assert catalog.controlWorkspace.feedbackMessage == "Approval request approved and applied."
    assert catalog.settingsWorkspace.feedbackMessage == "Module runtime state updated."
    assert catalog.settingsWorkspace.errorMessage == ""


def test_platform_workspace_controllers_store_validation_errors() -> None:
    catalog = PlatformWorkspaceCatalog(desktop_api_registry=_build_connected_platform_registry())

    result = catalog.toggleModuleLicensed("inventory")

    assert result["ok"] is False
    assert result["category"] == "validation"
    assert "planned" in result["message"].lower()
    assert "planned" in catalog.settingsWorkspace.errorMessage.lower()

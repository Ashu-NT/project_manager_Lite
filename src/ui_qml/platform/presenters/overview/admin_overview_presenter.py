from __future__ import annotations

from src.core.platform.api.desktop.approval.approval import PlatformApprovalDesktopApi
from src.core.platform.api.desktop.history.audit.audit_enterprise import PlatformEnterpriseAuditDesktopApi
from src.core.platform.api.desktop.history.audit.models.audit_entry import AuditEntryDto
from src.core.platform.api.desktop.master_data.department.department import PlatformDepartmentDesktopApi
from src.core.platform.api.desktop.master_data.documents.document import PlatformDocumentDesktopApi
from src.core.platform.api.desktop.master_data.employee.employee import PlatformEmployeeDesktopApi
from src.core.platform.api.desktop.master_data.party.party import PlatformPartyDesktopApi
from src.core.platform.api.desktop.master_data.site.site import PlatformSiteDesktopApi
from src.core.platform.api.desktop.platform_runtime.runtime import PlatformRuntimeDesktopApi
from src.core.platform.api.desktop.security.auth.user import PlatformUserDesktopApi
from src.core.platform.api.desktop.tenant.tenancy.tenant import PlatformTenantDesktopApi
from src.core.platform.domain.approval import ApprovalStatus
from src.ui_qml.platform.presenters.control.control_queue_presenter import PlatformControlQueuePresenter
from src.ui_qml.platform.view_models import (
    PlatformMetricViewModel,
    PlatformWorkspaceOverviewViewModel,
    PlatformWorkspaceRowViewModel,
    PlatformWorkspaceSectionViewModel,
)
from src.ui_qml.shared.models.activity_item import (
    ActivityItemViewModel,
    humanize_action,
    icon_key_for_entity_type,
    serialize_activity_items,
)

_SEVERITY_TONE: dict[str, str] = {
    "critical": "danger",
    "high": "danger",
    "medium": "warning",
    "low": "neutral",
}

_ENTITY_TYPE_LABEL: dict[str, str] = {
    "auth_session": "Auth Session",
    "user_account": "User Account",
    "organization": "Organization",
    "role": "Role",
    "permission": "Permission",
    "tenant": "Tenant",
    "approval": "Approval",
}


def _to_audit_preview_item(entry: AuditEntryDto) -> ActivityItemViewModel:
    severity = str(entry.severity or "").lower()
    return ActivityItemViewModel(
        id=entry.id,
        title=humanize_action(entry.operation),
        actor_display=entry.actor_username or entry.actor_id or "System",
        subject_display=_ENTITY_TYPE_LABEL.get(entry.entity_type, entry.entity_type.replace("_", " ").title()),
        occurred_at=entry.timestamp,
        occurred_at_label=entry.timestamp.strftime("%Y-%m-%d %H:%M UTC"),
        icon_key=icon_key_for_entity_type(entry.entity_type),
        tone=_SEVERITY_TONE.get(severity, "neutral"),
        status_label=entry.severity.capitalize() if severity in ("critical", "high") else "",
    )


class _HeadcountSummary:
    __slots__ = ("total", "active")

    def __init__(self, *, total: int, active: int) -> None:
        self.total = total
        self.active = active


class _SiteSummary:
    __slots__ = ("total", "active", "sample_names")

    def __init__(self, *, total: int, active: int, sample_names: tuple[str, ...]) -> None:
        self.total = total
        self.active = active
        self.sample_names = sample_names


class _DepartmentSummary:
    __slots__ = ("total", "active")

    def __init__(self, *, total: int, active: int) -> None:
        self.total = total
        self.active = active


class _PartySummary:
    __slots__ = ("total", "active")

    def __init__(self, *, total: int, active: int) -> None:
        self.total = total
        self.active = active


class _DocumentSummary:
    __slots__ = ("total", "current")

    def __init__(self, *, total: int, current: int) -> None:
        self.total = total
        self.current = current


class _UserSummary:
    __slots__ = ("total", "active", "locked")

    def __init__(self, *, total: int, active: int, locked: int) -> None:
        self.total = total
        self.active = active
        self.locked = locked


class PlatformAdminWorkspacePresenter:
    def __init__(
        self,
        *,
        runtime_api: PlatformRuntimeDesktopApi | None = None,
        site_api: PlatformSiteDesktopApi | None = None,
        department_api: PlatformDepartmentDesktopApi | None = None,
        employee_api: PlatformEmployeeDesktopApi | None = None,
        user_api: PlatformUserDesktopApi | None = None,
        document_api: PlatformDocumentDesktopApi | None = None,
        party_api: PlatformPartyDesktopApi | None = None,
        approval_api: PlatformApprovalDesktopApi | None = None,
        audit_api: PlatformEnterpriseAuditDesktopApi | None = None,
        tenant_api: PlatformTenantDesktopApi | None = None,
    ) -> None:
        self._runtime_api = runtime_api
        self._site_api = site_api
        self._department_api = department_api
        self._employee_api = employee_api
        self._user_api = user_api
        self._document_api = document_api
        self._party_api = party_api
        self._approval_api = approval_api
        self._audit_api = audit_api
        self._tenant_api = tenant_api
        self._queue_presenter = PlatformControlQueuePresenter(
            approval_api=approval_api,
            audit_api=audit_api,
        )

    def build_overview(self) -> PlatformWorkspaceOverviewViewModel:
        runtime_result = self._runtime_api.get_runtime_context() if self._runtime_api is not None else None
        if runtime_result is not None and (not runtime_result.ok or runtime_result.data is None):
            message = runtime_result.error.message if runtime_result.error is not None else "Unknown platform API error"
            return PlatformWorkspaceOverviewViewModel(
                title="Platform Overview",
                subtitle=message,
                status_label="Error",
            )

        runtime_context = runtime_result.data if runtime_result is not None else None
        if runtime_context is None:
            return PlatformWorkspaceOverviewViewModel(
                title="Platform Overview",
                subtitle="Platform desktop APIs are not connected in this QML preview.",
                status_label="Preview",
                metrics=(
                    PlatformMetricViewModel("Organizations", "0", "API not connected"),
                    PlatformMetricViewModel("Users", "0", "API not connected"),
                    PlatformMetricViewModel("Pending approvals", "0", "API not connected"),
                    PlatformMetricViewModel("Documents", "0", "API not connected"),
                ),
            )

        organization_count = self._organization_count(
            self._runtime_api.get_organization_count() if self._runtime_api is not None else None
        )
        site_summary = self._site_summary(
            self._site_api.get_site_rollup_summary() if self._site_api is not None else None
        )
        department_summary = self._department_summary(
            self._department_api.get_department_rollup_summary() if self._department_api is not None else None
        )
        headcount = self._headcount_summary(
            self._employee_api.get_headcount_summary() if self._employee_api is not None else None
        )
        user_summary = self._user_summary(
            self._user_api.get_user_rollup_summary() if self._user_api is not None else None
        )
        document_summary = self._document_summary(
            self._document_api.get_document_rollup_summary() if self._document_api is not None else None
        )
        document_structure_count = self._document_structure_count()
        party_summary = self._party_summary(
            self._party_api.get_party_rollup_summary() if self._party_api is not None else None
        )

        pending_approvals = self._queue_presenter.build_approval_queue(status=ApprovalStatus.PENDING)
        pending_approval_count = len(pending_approvals.items)
        approval_actions = {
            "title": "Approvals & Actions",
            "subtitle": "Governed changes awaiting a decision.",
            "emptyState": "No approvals are awaiting a decision.",
            "items": serialize_activity_items(
                self._queue_presenter.build_approval_activity_preview(status=ApprovalStatus.PENDING, limit=5)
            ),
        }
        recent_activity = self._recent_activity()
        active_tenant = self._active_tenant()

        organization_snapshot = PlatformWorkspaceSectionViewModel(
            title="Organization Snapshot",
            rows=(
                PlatformWorkspaceRowViewModel("Sites", str(site_summary.total), f"{site_summary.active} active"),
                PlatformWorkspaceRowViewModel(
                    "Departments", str(department_summary.total), f"{department_summary.active} active"
                ),
                PlatformWorkspaceRowViewModel("Employees", str(headcount.total), f"{headcount.active} active"),
                PlatformWorkspaceRowViewModel("Parties", str(party_summary.total), f"{party_summary.active} active"),
            ),
            empty_state="No organizational structure recorded yet.",
        )

        access_security = PlatformWorkspaceSectionViewModel(
            title="Access & Security",
            rows=(
                PlatformWorkspaceRowViewModel(
                    "User accounts", str(user_summary.total), f"{user_summary.active} active"
                ),
                PlatformWorkspaceRowViewModel(
                    "Locked accounts",
                    str(user_summary.locked),
                    "Requires attention" if user_summary.locked > 0 else "No locked accounts",
                ),
            ),
            empty_state="No user accounts recorded yet.",
        )

        module_tenant_rows = list(self._module_tenant_rows(runtime_context, active_tenant))
        module_tenant_status = PlatformWorkspaceSectionViewModel(
            title="Module & Tenant Status",
            rows=tuple(module_tenant_rows),
            empty_state="No module or tenant information available yet.",
        )

        documents_glance = (
            {
                "title": "Documents at a glance",
                "metrics": (
                    {"label": "Documents", "value": str(document_summary.total), "supportingText": ""},
                    {
                        "label": "Document Structures",
                        "value": str(document_structure_count),
                        "supportingText": "",
                    },
                ),
                "emptyState": "No documents recorded yet.",
            },
        )

        return PlatformWorkspaceOverviewViewModel(
            title="Platform Overview",
            subtitle="Manage shared administration, master data, and governance across the organization.",
            status_label="Connected",
            metrics=(
                PlatformMetricViewModel("Organizations", str(organization_count), "Across the platform"),
                PlatformMetricViewModel("Users", str(user_summary.active), "Active sign-in accounts"),
                PlatformMetricViewModel(
                    "Pending approvals", str(pending_approval_count), "Requests awaiting decision"
                ),
                PlatformMetricViewModel("Documents", str(document_summary.current), "Current controlled records"),
            ),
            sections=(organization_snapshot, access_security, module_tenant_status),
            breakdown_cards=documents_glance,
            recent_activity=recent_activity,
            approval_actions=approval_actions,
        )

    def _document_structure_count(self) -> int:
        if self._document_api is None:
            return 0
        result = self._document_api.list_document_structures()
        if not getattr(result, "ok", False) or getattr(result, "data", None) is None:
            return 0
        return len(result.data)

    def _recent_activity(self) -> tuple[dict, ...]:
        if self._audit_api is None:
            return ()
        entries = self._audit_api.list_for_overview(limit=5)
        return tuple(serialize_activity_items(_to_audit_preview_item(entry) for entry in entries))

    def _active_tenant(self) -> object | None:
        if self._tenant_api is None:
            return None
        result = self._tenant_api.get_active_tenant()
        if not getattr(result, "ok", False):
            return None
        return getattr(result, "data", None)

    @staticmethod
    def _module_tenant_rows(runtime_context, active_tenant) -> tuple[PlatformWorkspaceRowViewModel, ...]:
        rows: list[PlatformWorkspaceRowViewModel] = []
        if active_tenant is not None:
            rows.append(
                PlatformWorkspaceRowViewModel(
                    "Tenant",
                    str(getattr(active_tenant, "display_name", "") or ""),
                    str(getattr(active_tenant, "tenant_status", "") or "").replace("_", " ").title(),
                )
            )
        rows.append(
            PlatformWorkspaceRowViewModel(
                "Licensed modules", str(len(runtime_context.licensed_modules)), "Available under the current license"
            )
        )
        rows.append(
            PlatformWorkspaceRowViewModel(
                "Enabled modules", str(len(runtime_context.enabled_modules)), "Active in this runtime context"
            )
        )
        for entitlement in runtime_context.entitlements:
            if not entitlement.licensed:
                continue
            rows.append(
                PlatformWorkspaceRowViewModel(
                    entitlement.label,
                    entitlement.lifecycle_label,
                    "Needs attention" if entitlement.lifecycle_alert else "",
                )
            )
        return tuple(rows)

    @staticmethod
    def _headcount_summary(result: object | None) -> _HeadcountSummary:
        if result is None or not getattr(result, "ok", False) or getattr(result, "data", None) is None:
            return _HeadcountSummary(total=0, active=0)
        data = result.data
        return _HeadcountSummary(total=data.total, active=data.active)

    @staticmethod
    def _organization_count(result: object | None) -> int:
        if result is None or not getattr(result, "ok", False) or getattr(result, "data", None) is None:
            return 0
        return int(result.data)

    @staticmethod
    def _site_summary(result: object | None) -> _SiteSummary:
        if result is None or not getattr(result, "ok", False) or getattr(result, "data", None) is None:
            return _SiteSummary(total=0, active=0, sample_names=())
        data = result.data
        return _SiteSummary(total=data.total, active=data.active, sample_names=tuple(data.sample_names))

    @staticmethod
    def _department_summary(result: object | None) -> _DepartmentSummary:
        if result is None or not getattr(result, "ok", False) or getattr(result, "data", None) is None:
            return _DepartmentSummary(total=0, active=0)
        data = result.data
        return _DepartmentSummary(total=data.total, active=data.active)

    @staticmethod
    def _party_summary(result: object | None) -> _PartySummary:
        if result is None or not getattr(result, "ok", False) or getattr(result, "data", None) is None:
            return _PartySummary(total=0, active=0)
        data = result.data
        return _PartySummary(total=data.total, active=data.active)

    @staticmethod
    def _document_summary(result: object | None) -> _DocumentSummary:
        if result is None or not getattr(result, "ok", False) or getattr(result, "data", None) is None:
            return _DocumentSummary(total=0, current=0)
        data = result.data
        return _DocumentSummary(total=data.total, current=data.current)

    @staticmethod
    def _user_summary(result: object | None) -> _UserSummary:
        if result is None or not getattr(result, "ok", False) or getattr(result, "data", None) is None:
            return _UserSummary(total=0, active=0, locked=0)
        data = result.data
        return _UserSummary(total=data.total, active=data.active, locked=data.locked)


__all__ = ["PlatformAdminWorkspacePresenter"]

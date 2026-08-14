from __future__ import annotations

from src.core.platform.api.desktop.master_data.department.department import PlatformDepartmentDesktopApi
from src.core.platform.api.desktop.master_data.documents.document import PlatformDocumentDesktopApi
from src.core.platform.api.desktop.master_data.employee.employee import PlatformEmployeeDesktopApi
from src.core.platform.api.desktop.master_data.party.party import PlatformPartyDesktopApi
from src.core.platform.api.desktop.master_data.site.site import PlatformSiteDesktopApi
from src.core.platform.api.desktop.platform_runtime.runtime import PlatformRuntimeDesktopApi
from src.core.platform.api.desktop.security.auth.user import PlatformUserDesktopApi
from src.core.platform.api.desktop.history.audit.audit_enterprise import PlatformEnterpriseAuditDesktopApi
from src.ui_qml.platform.view_models import (
    PlatformMetricViewModel,
    PlatformWorkspaceOverviewViewModel,
    PlatformWorkspaceRowViewModel,
    PlatformWorkspaceSectionViewModel,
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
        audit_api: PlatformEnterpriseAuditDesktopApi | None = None,
    ) -> None:
        self._runtime_api = runtime_api
        self._site_api = site_api
        self._department_api = department_api
        self._employee_api = employee_api
        self._user_api = user_api
        self._document_api = document_api
        self._party_api = party_api
        self._audit_api = audit_api

    def build_overview(self) -> PlatformWorkspaceOverviewViewModel:
        runtime_result = self._runtime_api.get_runtime_context() if self._runtime_api is not None else None
        if runtime_result is not None and (not runtime_result.ok or runtime_result.data is None):
            message = runtime_result.error.message if runtime_result.error is not None else "Unknown platform API error"
            return PlatformWorkspaceOverviewViewModel(
                title="Admin Console",
                subtitle=message,
                status_label="Error",
            )

        runtime_context = runtime_result.data if runtime_result is not None else None
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
        users = self._tuple_data(self._user_api.list_users() if self._user_api is not None else None)
        document_summary = self._document_summary(
            self._document_api.get_document_rollup_summary() if self._document_api is not None else None
        )
        party_summary = self._party_summary(
            self._party_api.get_party_rollup_summary() if self._party_api is not None else None
        )

        if runtime_context is None:
            return PlatformWorkspaceOverviewViewModel(
                title="Admin Console",
                subtitle="Platform desktop APIs are not connected in this QML preview.",
                status_label="Preview",
                metrics=(
                    PlatformMetricViewModel("Organizations", "0", "API not connected"),
                    PlatformMetricViewModel("Sites", "0", "API not connected"),
                    PlatformMetricViewModel("Departments", "0", "API not connected"),
                    PlatformMetricViewModel("Employees", "0", "API not connected"),
                ),
            )

        active_user_count = sum(1 for user in users if user.is_active)
        locked_user_count = sum(1 for user in users if user.locked_until is not None)
        active_employee_count = headcount.active
        active_site_count = site_summary.active
        active_department_count = department_summary.active
        active_party_count = party_summary.active
        current_document_count = document_summary.current

        activity_feed_items: tuple[dict, ...] = ()
        if self._audit_api is not None:
            activity_feed_items = tuple(self._audit_api.list_for_overview(limit=50))

        return PlatformWorkspaceOverviewViewModel(
            title="Admin Console",
            subtitle=f"{runtime_context.context_label} | grouped platform administration in QML",
            status_label="Connected",
            activityFeed=activity_feed_items,
            metrics=(
                PlatformMetricViewModel("Organizations", str(organization_count), "Install profiles"),
                PlatformMetricViewModel("Sites", str(active_site_count), "Active operating sites"),
                PlatformMetricViewModel("Departments", str(active_department_count), "Active structures"),
                PlatformMetricViewModel("Employees", str(active_employee_count), "Active workforce records"),
                PlatformMetricViewModel("Users", str(active_user_count), "Active sign-in accounts"),
                PlatformMetricViewModel("Documents", str(current_document_count), "Current controlled records"),
            ),
            sections=(
                PlatformWorkspaceSectionViewModel(
                    title="Runtime Context",
                    rows=(
                        PlatformWorkspaceRowViewModel(
                            "Active organization",
                            runtime_context.active_organization.display_name if runtime_context.active_organization is not None else "None",
                            runtime_context.shell_summary,
                        ),
                        PlatformWorkspaceRowViewModel(
                            "Licensed modules",
                            str(len(runtime_context.licensed_modules)),
                            "Modules available to the current organization",
                        ),
                        PlatformWorkspaceRowViewModel(
                            "Enabled modules",
                            str(len(runtime_context.enabled_modules)),
                            "Modules currently active in the runtime context",
                        ),
                    ),
                ),
                PlatformWorkspaceSectionViewModel(
                    title="Identity And Workforce",
                    rows=(
                        PlatformWorkspaceRowViewModel(
                            "Users",
                            str(len(users)),
                            f"{locked_user_count} locked, {active_user_count} active",
                        ),
                        PlatformWorkspaceRowViewModel(
                            "Employees",
                            str(headcount.total),
                            f"{active_employee_count} active employee records",
                        ),
                        PlatformWorkspaceRowViewModel(
                            "Departments",
                            str(department_summary.total),
                            f"{active_department_count} active departments across the platform",
                        ),
                    ),
                ),
                PlatformWorkspaceSectionViewModel(
                    title="Master Data Coverage",
                    rows=(
                        PlatformWorkspaceRowViewModel(
                            "Sites",
                            str(site_summary.total),
                            ", ".join(site_summary.sample_names) or "No sites configured yet",
                        ),
                        PlatformWorkspaceRowViewModel(
                            "Parties",
                            str(party_summary.total),
                            f"{active_party_count} active supplier/customer/partner records",
                        ),
                        PlatformWorkspaceRowViewModel(
                            "Documents",
                            str(document_summary.total),
                            f"{current_document_count} marked current across controlled records",
                        ),
                    ),
                ),
            ),
        )

    @staticmethod
    def _tuple_data(result: object | None) -> tuple[object, ...]:
        if result is None or not getattr(result, "ok", False) or getattr(result, "data", None) is None:
            return ()
        return tuple(result.data)

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


__all__ = ["PlatformAdminWorkspacePresenter"]

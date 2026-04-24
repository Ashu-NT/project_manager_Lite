from __future__ import annotations

from src.api.desktop.platform import (
    PlatformDocumentDesktopApi,
    PlatformEmployeeDesktopApi,
    PlatformPartyDesktopApi,
    PlatformRuntimeDesktopApi,
    PlatformSiteDesktopApi,
    PlatformDepartmentDesktopApi,
    PlatformUserDesktopApi,
)
from src.ui_qml.platform.view_models import (
    PlatformMetricViewModel,
    PlatformWorkspaceOverviewViewModel,
    PlatformWorkspaceRowViewModel,
    PlatformWorkspaceSectionViewModel,
)


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
    ) -> None:
        self._runtime_api = runtime_api
        self._site_api = site_api
        self._department_api = department_api
        self._employee_api = employee_api
        self._user_api = user_api
        self._document_api = document_api
        self._party_api = party_api

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
        organizations = self._tuple_data(self._runtime_api.list_organizations(active_only=None) if self._runtime_api is not None else None)
        sites = self._tuple_data(self._site_api.list_sites(active_only=None) if self._site_api is not None else None)
        departments = self._tuple_data(
            self._department_api.list_departments(active_only=None) if self._department_api is not None else None
        )
        employees = self._tuple_data(self._employee_api.list_employees(active_only=None) if self._employee_api is not None else None)
        users = self._tuple_data(self._user_api.list_users() if self._user_api is not None else None)
        documents = self._tuple_data(
            self._document_api.list_documents(active_only=None) if self._document_api is not None else None
        )
        parties = self._tuple_data(self._party_api.list_parties(active_only=None) if self._party_api is not None else None)

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
        active_employee_count = sum(1 for employee in employees if employee.is_active)
        active_site_count = sum(1 for site in sites if site.is_active)
        active_department_count = sum(1 for department in departments if department.is_active)
        active_party_count = sum(1 for party in parties if party.is_active)
        current_document_count = sum(1 for document in documents if document.is_current)

        return PlatformWorkspaceOverviewViewModel(
            title="Admin Console",
            subtitle=f"{runtime_context.context_label} | grouped platform administration in QML",
            status_label="Connected",
            metrics=(
                PlatformMetricViewModel("Organizations", str(len(organizations)), "Install profiles"),
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
                            str(len(employees)),
                            f"{active_employee_count} active employee records",
                        ),
                        PlatformWorkspaceRowViewModel(
                            "Departments",
                            str(len(departments)),
                            f"{active_department_count} active departments across the platform",
                        ),
                    ),
                ),
                PlatformWorkspaceSectionViewModel(
                    title="Master Data Coverage",
                    rows=(
                        PlatformWorkspaceRowViewModel(
                            "Sites",
                            str(len(sites)),
                            ", ".join(site.name for site in sites[:3]) or "No sites configured yet",
                        ),
                        PlatformWorkspaceRowViewModel(
                            "Parties",
                            str(len(parties)),
                            f"{active_party_count} active supplier/customer/partner records",
                        ),
                        PlatformWorkspaceRowViewModel(
                            "Documents",
                            str(len(documents)),
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


__all__ = ["PlatformAdminWorkspacePresenter"]

from __future__ import annotations

import pytest

from src.core.modules.project_management.application.portfolio import PortfolioService
from src.core.modules.project_management.application.projects import ProjectService
from src.core.modules.project_management.application.resources import ResourceService
from src.core.modules.project_management.domain.projects.project import Project
from src.core.modules.project_management.domain.resources.resource import Resource
from src.core.platform.auth.domain.session import UserSessionContext, UserSessionPrincipal
from src.core.platform.calendar.application.enterprise_calendar_service import EnterpriseCalendarService
from src.core.platform.calendar.application.shift_pattern_service import ShiftPatternService
from src.core.platform.calendar.domain.enterprise_calendar import PlatformCalendar, ShiftPattern
from src.core.platform.common.exceptions import BusinessRuleError, NotFoundError
from src.core.platform.department.application.department_service import DepartmentService
from src.core.platform.department.domain import Department
from src.core.platform.documents.application.document_service import DocumentService
from src.core.platform.documents.domain import Document
from src.core.platform.org.domain import Organization
from src.core.platform.party.application.party_service import PartyService
from src.core.platform.party.domain import Party
from src.core.platform.site.application.site_service import SiteService
from src.core.platform.site.domain import Site
from src.core.platform.tenancy import TenantContextService


class _TenantRepo:
    def get(self, tenant_id: str):
        return None

    def get_default(self):
        return None


class _OrgRepo:
    def __init__(self) -> None:
        self.rows = {
            "org-a": Organization(
                id="org-a",
                organization_code="ORGA",
                display_name="Organization A",
            ),
            "org-b": Organization(
                id="org-b",
                organization_code="ORGB",
                display_name="Organization B",
            ),
        }

    def get(self, organization_id: str):
        return self.rows.get(organization_id)

    def get_active(self):
        return self.rows["org-a"]


class _ProjectRepo:
    def __init__(self) -> None:
        self.rows = [
            Project(id="project-a", name="A Project", organization_id="org-a"),
            Project(id="project-b", name="B Project", organization_id="org-b"),
        ]
        self.list_calls: int = 0
        self._tenant_context_service = None

    def get(self, project_id: str):
        row = next((r for r in self.rows if r.id == project_id), None)
        if row is None:
            return None
        if self._tenant_context_service is not None:
            try:
                org_id = self._tenant_context_service.get_active_organization_id()
                if org_id and getattr(row, "organization_id", None) != org_id:
                    return None
            except Exception:
                pass
        return row

    def list(self):
        self.list_calls += 1
        if self._tenant_context_service is not None:
            try:
                org_id = self._tenant_context_service.get_active_organization_id()
                if org_id:
                    return [r for r in self.rows if r.organization_id == org_id]
            except Exception:
                pass
        return list(self.rows)

    def list_all(self):
        return list(self.rows)


class _ResourceRepo:
    def __init__(self) -> None:
        self.rows = [
            Resource(id="resource-a", name="A Resource", organization_id="org-a"),
            Resource(id="resource-b", name="B Resource", organization_id="org-b"),
        ]
        self.list_calls: int = 0
        self._tenant_context_service = None

    def get(self, resource_id: str):
        row = next((r for r in self.rows if r.id == resource_id), None)
        if row is None:
            return None
        if self._tenant_context_service is not None:
            try:
                org_id = self._tenant_context_service.get_active_organization_id()
                if org_id and getattr(row, "organization_id", None) != org_id:
                    return None
            except Exception:
                pass
        return row

    def list(self):
        self.list_calls += 1
        if self._tenant_context_service is not None:
            try:
                org_id = self._tenant_context_service.get_active_organization_id()
                if org_id:
                    return [r for r in self.rows if getattr(r, "organization_id", None) == org_id]
            except Exception:
                pass
        return list(self.rows)

    def list_all(self):
        return list(self.rows)


class _PlatformScopedRepo:
    def __init__(self, rows: list[object]) -> None:
        self.rows = rows
        self.list_for_organization_calls: list[str] = []

    def get(self, row_id: str):
        return next((row for row in self.rows if getattr(row, "id", "") == row_id), None)

    def get_by_code(self, organization_id: str, code: str):
        for row in self.rows:
            row_code = (
                getattr(row, "site_code", None)
                or getattr(row, "department_code", None)
                or getattr(row, "party_code", None)
                or getattr(row, "document_code", None)
                or getattr(row, "code", None)
            )
            if getattr(row, "organization_id", None) == organization_id and row_code == code:
                return row
        return None

    def list_for_organization(
        self,
        organization_id: str,
        *,
        active_only: bool | None = None,
        calendar_type: str | None = None,
    ):
        self.list_for_organization_calls.append(organization_id)
        rows = [row for row in self.rows if getattr(row, "organization_id", None) == organization_id]
        if calendar_type is not None:
            rows = [row for row in rows if getattr(row, "calendar_type", None) == calendar_type]
        if active_only is None:
            return rows
        return [row for row in rows if bool(getattr(row, "is_active", True)) is bool(active_only)]


def _tenant_context(
    active_organization_id: str,
    *,
    permissions: frozenset[str] | None = None,
) -> tuple[UserSessionContext, TenantContextService]:
    session = UserSessionContext()
    session.set_principal(
        UserSessionPrincipal(
            user_id="user-1",
            username="planner",
            display_name="Planner",
            role_names=frozenset(),
            permissions=permissions
            or frozenset({"project.read", "resource.read", "organization.access"}),
            scoped_access={
                "organization": {
                    active_organization_id: frozenset({"organization.access"}),
                },
            },
        )
    )
    session.set_active_organization_id(active_organization_id)
    return session, TenantContextService(
        tenant_repo=_TenantRepo(),
        organization_repo=_OrgRepo(),
        user_session=session,
    )


def test_project_service_lists_only_active_tenant_projects() -> None:
    user_session, tenant_context = _tenant_context("org-a")
    project_repo = _ProjectRepo()
    project_repo._tenant_context_service = tenant_context
    service = ProjectService(
        session=object(),
        project_repo=project_repo,
        task_repo=object(),
        dependency_repo=object(),
        assignment_repo=object(),
        time_entry_repo=None,
        cost_repo=object(),
        user_session=user_session,
        tenant_context_service=tenant_context,
    )

    rows = service.list_projects()

    assert [row.id for row in rows] == ["project-a"]
    assert project_repo.list_calls == 1
    assert service.get_project("project-b") is None


def test_portfolio_service_requires_tenant_context_service() -> None:
    with pytest.raises(BusinessRuleError, match="PortfolioService requires TenantContextService"):
        PortfolioService(
            session=object(),
            intake_repo=object(),
            dependency_repo=object(),
            scoring_template_repo=object(),
            scenario_repo=object(),
            audit_repo=object(),
            project_repo=object(),
            resource_repo=object(),
            reporting_service=object(),
            tenant_context_service=None,
        )


def test_resource_service_lists_only_active_tenant_resources() -> None:
    user_session, tenant_context = _tenant_context("org-b")
    resource_repo = _ResourceRepo()
    resource_repo._tenant_context_service = tenant_context
    service = ResourceService(
        session=object(),
        resource_repo=resource_repo,
        assignment_repo=object(),
        user_session=user_session,
        tenant_context_service=tenant_context,
    )

    rows = service.list_resources()

    assert [row.id for row in rows] == ["resource-b"]
    assert resource_repo.list_calls == 1

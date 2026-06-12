from __future__ import annotations

from src.core.modules.project_management.application.projects import ProjectService
from src.core.modules.project_management.application.resources import ResourceService
from src.core.modules.project_management.domain.projects.project import Project
from src.core.modules.project_management.domain.resources.resource import Resource
from src.core.platform.auth.domain.session import UserSessionContext, UserSessionPrincipal
from src.core.platform.calendar.application.enterprise_calendar_service import EnterpriseCalendarService
from src.core.platform.calendar.application.shift_pattern_service import ShiftPatternService
from src.core.platform.calendar.domain.enterprise_calendar import PlatformCalendar, ShiftPattern
from src.core.platform.common.exceptions import NotFoundError
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
        calendar_repo=object(),
        cost_repo=object(),
        user_session=user_session,
        tenant_context_service=tenant_context,
    )

    rows = service.list_projects()

    assert [row.id for row in rows] == ["project-a"]
    assert project_repo.list_calls == 1
    assert service.get_project("project-b") is None


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


def test_platform_master_data_services_use_runtime_tenant_context() -> None:
    user_session, tenant_context = _tenant_context(
        "org-b",
        permissions=frozenset(
            {
                "organization.access",
                "site.read",
                "department.read",
                "party.read",
                "settings.manage",
                "task.read",
            }
        ),
    )
    org_repo = _OrgRepo()
    site_repo = _PlatformScopedRepo(
        [
            Site(id="site-a", organization_id="org-a", site_code="SITE-A", name="A Site"),
            Site(id="site-b", organization_id="org-b", site_code="SITE-B", name="B Site"),
        ]
    )
    department_repo = _PlatformScopedRepo(
        [
            Department(id="department-a", organization_id="org-a", department_code="DEPT-A", name="A Department"),
            Department(id="department-b", organization_id="org-b", department_code="DEPT-B", name="B Department"),
        ]
    )
    party_repo = _PlatformScopedRepo(
        [
            Party(id="party-a", organization_id="org-a", party_code="PARTY-A", party_name="A Party"),
            Party(id="party-b", organization_id="org-b", party_code="PARTY-B", party_name="B Party"),
        ]
    )
    document_repo = _PlatformScopedRepo(
        [
            Document(id="document-a", organization_id="org-a", document_code="DOC-A", title="A Document"),
            Document(id="document-b", organization_id="org-b", document_code="DOC-B", title="B Document"),
        ]
    )
    calendar_repo = _PlatformScopedRepo(
        [
            PlatformCalendar(
                id="calendar-a",
                organization_id="org-a",
                code="CAL-A",
                name="A Calendar",
                calendar_type="GLOBAL",
            ),
            PlatformCalendar(
                id="calendar-b",
                organization_id="org-b",
                code="CAL-B",
                name="B Calendar",
                calendar_type="GLOBAL",
            ),
        ]
    )
    shift_pattern_repo = _PlatformScopedRepo(
        [
            ShiftPattern(
                id="pattern-a",
                organization_id="org-a",
                code="PAT-A",
                name="A Shift",
                pattern_type="FIXED",
            ),
            ShiftPattern(
                id="pattern-b",
                organization_id="org-b",
                code="PAT-B",
                name="B Shift",
                pattern_type="FIXED",
            ),
        ]
    )

    site_service = SiteService(
        session=object(),
        site_repo=site_repo,
        organization_repo=org_repo,
        user_session=user_session,
        tenant_context_service=tenant_context,
    )
    department_service = DepartmentService(
        session=object(),
        department_repo=department_repo,
        organization_repo=org_repo,
        user_session=user_session,
        tenant_context_service=tenant_context,
    )
    party_service = PartyService(
        session=object(),
        party_repo=party_repo,
        organization_repo=org_repo,
        user_session=user_session,
        tenant_context_service=tenant_context,
    )
    document_service = DocumentService(
        session=object(),
        document_repo=document_repo,
        link_repo=object(),
        structure_repo=object(),
        organization_repo=org_repo,
        user_session=user_session,
        tenant_context_service=tenant_context,
    )
    calendar_service = EnterpriseCalendarService(
        session=object(),
        calendar_repo=calendar_repo,
        assignment_repo=object(),
        organization_repo=org_repo,
        user_session=user_session,
        tenant_context_service=tenant_context,
    )
    shift_pattern_service = ShiftPatternService(
        session=object(),
        pattern_repo=shift_pattern_repo,
        organization_repo=org_repo,
        user_session=user_session,
        tenant_context_service=tenant_context,
    )

    assert [row.id for row in site_service.list_sites(active_only=None)] == ["site-b"]
    assert [row.id for row in department_service.list_departments(active_only=None)] == ["department-b"]
    assert [row.id for row in party_service.list_parties(active_only=None)] == ["party-b"]
    assert [row.id for row in document_service.list_documents(active_only=None)] == ["document-b"]
    assert [row.id for row in calendar_service.list_calendars(active_only=None)] == ["calendar-b"]
    assert [row.id for row in shift_pattern_service.list_shift_patterns(active_only=None)] == ["pattern-b"]
    try:
        calendar_service.get_calendar("calendar-a")
    except NotFoundError:
        pass
    else:  # pragma: no cover - defensive clarity
        raise AssertionError("Cross-tenant calendar access should be denied")
    try:
        shift_pattern_service.get_shift_pattern("pattern-a")
    except NotFoundError:
        pass
    else:  # pragma: no cover - defensive clarity
        raise AssertionError("Cross-tenant shift pattern access should be denied")
    assert site_repo.list_for_organization_calls == ["org-b"]
    assert department_repo.list_for_organization_calls == ["org-b"]
    assert party_repo.list_for_organization_calls == ["org-b"]
    assert document_repo.list_for_organization_calls == ["org-b"]
    assert calendar_repo.list_for_organization_calls == ["org-b"]
    assert shift_pattern_repo.list_for_organization_calls == ["org-b"]

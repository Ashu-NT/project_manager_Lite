from __future__ import annotations

from src.core.platform.common.exceptions import NotFoundError, ValidationError
from src.core.platform.application.master_data.department.department_service import DepartmentService
from src.core.platform.domain.master_data.department import Department
from src.core.platform.application.master_data.employee.employee_service import EmployeeService
from src.core.platform.domain.master_data.employee import Employee, EmploymentType
from src.core.platform.domain.master_data.org import Organization
from src.core.platform.domain.master_data.site import Site
from src.infra.time.system_clock import SystemClock


class _FakeSession:
    def __init__(self) -> None:
        self.commit_calls = 0

    def commit(self) -> None:
        self.commit_calls += 1

    def rollback(self) -> None:
        return None


class _FakeTenantContext:
    def __init__(self, organization: Organization) -> None:
        self._organization = organization

    def get_active_organization(self) -> Organization:
        return self._organization

    def require_active_organization_id(self, *, operation_label: str) -> str:
        return self._organization.id

    def require_active_tenant_id(self, *, operation_label: str) -> str:
        return self._organization.tenant_id


class _FakeEnterpriseAuditService:
    def record(self, **kwargs) -> None:
        return None


class _FakeDepartmentRepo:
    def __init__(self) -> None:
        self._rows: dict[str, Department] = {}

    def add(self, department: Department) -> None:
        self._rows[department.id] = department

    def update(self, department: Department) -> None:
        if department.id not in self._rows:
            raise NotFoundError("Department not found.", code="DEPARTMENT_NOT_FOUND")
        department.version += 1
        self._rows[department.id] = department

    def get(self, department_id: str) -> Department | None:
        return self._rows.get(department_id)

    def get_by_code(self, organization_id: str, department_code: str) -> Department | None:
        for row in self._rows.values():
            if row.organization_id == organization_id and row.department_code == department_code:
                return row
        return None

    def list_for_organization(
        self,
        organization_id: str,
        *,
        active_only: bool | None = None,
    ) -> list[Department]:
        rows = [row for row in self._rows.values() if row.organization_id == organization_id]
        if active_only is not None:
            rows = [row for row in rows if row.is_active is bool(active_only)]
        return sorted(rows, key=lambda row: row.name)


class _FakeEmployeeRepo:
    def __init__(self) -> None:
        self._rows: dict[str, Employee] = {}

    def add(self, employee: Employee) -> None:
        self._rows[employee.id] = employee

    def update(self, employee: Employee) -> None:
        if employee.id not in self._rows:
            raise NotFoundError("Employee not found.", code="EMPLOYEE_NOT_FOUND")
        employee.version += 1
        self._rows[employee.id] = employee

    def get(self, employee_id: str) -> Employee | None:
        return self._rows.get(employee_id)

    def get_for_organization(self, employee_id: str, organization_id: str) -> Employee | None:
        employee = self._rows.get(employee_id)
        if employee is None or employee.organization_id != organization_id:
            return None
        return employee

    def get_by_code_for_organization(self, employee_code: str, organization_id: str) -> Employee | None:
        for row in self._rows.values():
            if row.organization_id == organization_id and row.employee_code == employee_code:
                return row
        return None

    def list_for_organization(
        self,
        organization_id: str,
        *,
        active_only: bool | None = None,
    ) -> list[Employee]:
        rows = [row for row in self._rows.values() if row.organization_id == organization_id]
        if active_only is not None:
            rows = [row for row in rows if row.is_active is bool(active_only)]
        return sorted(rows, key=lambda row: row.full_name)


class _FakeSiteRepo:
    def __init__(self) -> None:
        self._rows: dict[str, Site] = {}

    def add(self, site: Site) -> None:
        self._rows[site.id] = site

    def get(self, site_id: str) -> Site | None:
        return self._rows.get(site_id)

    def list_for_organization(
        self,
        organization_id: str,
        *,
        active_only: bool | None = None,
    ) -> list[Site]:
        rows = [row for row in self._rows.values() if row.organization_id == organization_id]
        if active_only is not None:
            rows = [row for row in rows if row.is_active is bool(active_only)]
        return sorted(rows, key=lambda row: row.name)


class _FakeLinkedEmployeeResourceRepo:
    def list_by_employee(self, employee_id: str) -> list[object]:
        return []

    def update(self, resource: object) -> None:
        return None


class _FakeEmployeeUnitOfWork:
    def __init__(self, *, session, employees, resources, sites, departments, enterprise_audit_service, context):
        self._session = session
        self.employees = employees
        self.resources = resources
        self.sites = sites
        self.departments = departments
        self._enterprise_audit_service = enterprise_audit_service
        self.context = context
        self._committed = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None and not self._committed:
            self._session.rollback()
        return None

    def record_event(self, event) -> None:
        return None

    def commit(self) -> None:
        self._session.commit()
        self._committed = True


class _FakeEmployeeUnitOfWorkFactory:
    def __init__(self, *, session, employees, resources, sites, departments, enterprise_audit_service):
        self._session = session
        self._employees = employees
        self._resources = resources
        self._sites = sites
        self._departments = departments
        self._enterprise_audit_service = enterprise_audit_service

    def create(self, *, context):
        return _FakeEmployeeUnitOfWork(
            session=self._session,
            employees=self._employees,
            resources=self._resources,
            sites=self._sites,
            departments=self._departments,
            enterprise_audit_service=self._enterprise_audit_service,
            context=context,
        )


class _FakeDepartmentUnitOfWork:
    def __init__(self, *, session, departments, sites, employees, enterprise_audit_service, context):
        self._session = session
        self.departments = departments
        self.sites = sites
        self.employees = employees
        self._enterprise_audit_service = enterprise_audit_service
        self.context = context
        self._committed = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None and not self._committed:
            self._session.rollback()
        return None

    def record_event(self, event) -> None:
        return None

    def commit(self) -> None:
        self._session.commit()
        self._committed = True


class _FakeDepartmentUnitOfWorkFactory:
    def __init__(self, *, session, departments, sites, employees, enterprise_audit_service):
        self._session = session
        self._departments = departments
        self._sites = sites
        self._employees = employees
        self._enterprise_audit_service = enterprise_audit_service

    def create(self, *, context):
        return _FakeDepartmentUnitOfWork(
            session=self._session,
            departments=self._departments,
            sites=self._sites,
            employees=self._employees,
            enterprise_audit_service=self._enterprise_audit_service,
            context=context,
        )


def _make_organization() -> Organization:
    return Organization.create(
        organization_code="default",
        display_name="Default Organization",
        timezone_name="UTC",
        base_currency="EUR",
        tenant_id="tenant-1",
    )


def test_department_dto_normalizes_and_validates_fields():
    department = Department.create(
        organization_id="  org-1  ",
        department_code="  ops  ",
        name="  Operations  ",
        description="  Core team  ",
        site_id="  site-1  ",
        default_location_id="  loc-1  ",
        parent_department_id="  parent-1  ",
        department_type="  operations  ",
        cost_center_code="  cc-100  ",
        manager_employee_id="  emp-1  ",
        notes="  Note  ",
    )

    assert department.organization_id == "org-1"
    assert department.department_code == "OPS"
    assert department.name == "Operations"
    assert department.description == "Core team"
    assert department.site_id == "site-1"
    assert department.default_location_id == "loc-1"
    assert department.parent_department_id == "parent-1"
    assert department.department_type == "operations"
    assert department.cost_center_code == "CC-100"
    assert department.manager_employee_id == "emp-1"
    assert department.notes == "Note"
    assert department.created_at is not None
    assert department.updated_at is not None

    try:
        Department.create(
            organization_id=" ",
            department_code="OPS",
            name="Valid",
        )
    except ValidationError as exc:
        assert exc.code == "DEPARTMENT_ORGANIZATION_REQUIRED"
    else:
        raise AssertionError("Expected department organization validation error.")


def test_department_service_uses_entity_validation(monkeypatch):
    monkeypatch.setattr(
        "src.core.platform.application.master_data.department.department_commands.require_permission",
        lambda *args, **kwargs: None,
    )

    organization = _make_organization()
    site_repo = _FakeSiteRepo()
    site = Site.create(
        organization_id=organization.id,
        site_code="hq",
        name="Headquarters",
    )
    site_repo.add(site)

    session = _FakeSession()
    department_repo = _FakeDepartmentRepo()
    employee_repo = _FakeEmployeeRepo()
    enterprise_audit_service = _FakeEnterpriseAuditService()
    service = DepartmentService(
        session=session,
        department_repo=department_repo,
        organization_repo=object(),
        site_repo=site_repo,
        employee_repo=employee_repo,
        user_session=object(),
        enterprise_audit_service=enterprise_audit_service,
        tenant_context_service=_FakeTenantContext(organization),
        uow_factory=_FakeDepartmentUnitOfWorkFactory(
            session=session,
            departments=department_repo,
            sites=site_repo,
            employees=employee_repo,
            enterprise_audit_service=enterprise_audit_service,
        ),
    )

    created = service.create_department(
        department_code=" ops ",
        display_name="  Operations  ",
        description="  Core team  ",
        site_id=f"  {site.id}  ",
        department_type="  operations  ",
        cost_center_code="  cc-100  ",
        notes="  Note  ",
    )

    assert created.department_code == "OPS"
    assert created.name == "Operations"
    assert created.description == "Core team"
    assert created.site_id == site.id
    assert created.department_type == "operations"
    assert created.cost_center_code == "CC-100"
    assert created.notes == "Note"

    updated = service.update_department(
        created.id,
        department_code=" ops-2 ",
        display_name="  Field Operations  ",
        cost_center_code=" cc-200 ",
        expected_version=created.version,
    )

    assert updated.department_code == "OPS-2"
    assert updated.name == "Field Operations"
    assert updated.cost_center_code == "CC-200"

    try:
        service.create_department(department_code=" ops-2 ", name="Duplicate")
    except ValidationError as exc:
        assert exc.code == "DEPARTMENT_CODE_EXISTS"
    else:
        raise AssertionError("Expected duplicate department code validation error.")


def test_employee_dto_normalizes_and_validates_fields():
    employee = Employee.create(
        employee_code="  emp-1  ",
        full_name="  Alice Admin  ",
        organization_id="  org-1  ",
        department_id="  dept-1  ",
        department="  PMO  ",
        site_id="  site-1  ",
        site_name="  Headquarters  ",
        title="  Planner  ",
        employment_type="part_time",
        email="  ALICE@EXAMPLE.COM  ",
        phone="  +49-555-0101  ",
    )

    assert employee.employee_code == "EMP-1"
    assert employee.full_name == "Alice Admin"
    assert employee.organization_id == "org-1"
    assert employee.department_id == "dept-1"
    assert employee.department == "PMO"
    assert employee.site_id == "site-1"
    assert employee.site_name == "Headquarters"
    assert employee.title == "Planner"
    assert employee.employment_type is EmploymentType.PART_TIME
    assert employee.email == "alice@example.com"
    assert employee.phone == "+49-555-0101"

    try:
        Employee.create(
            employee_code=" ",
            full_name="Valid",
        )
    except ValidationError as exc:
        assert exc.code == "EMPLOYEE_CODE_REQUIRED"
    else:
        raise AssertionError("Expected employee code validation error.")

    try:
        Employee.create(
            employee_code="EMP-1",
            full_name="Valid",
            employment_type="invalid",
        )
    except ValidationError as exc:
        assert exc.code == "EMPLOYEE_TYPE_INVALID"
    else:
        raise AssertionError("Expected employment-type validation error.")


def test_employee_service_uses_entity_validation_and_final_state(monkeypatch):
    monkeypatch.setattr(
        "src.core.platform.application.master_data.employee.employee_service.require_permission",
        lambda *args, **kwargs: None,
    )

    organization = _make_organization()
    department_repo = _FakeDepartmentRepo()
    site_repo = _FakeSiteRepo()
    employee_repo = _FakeEmployeeRepo()

    site = Site.create(
        organization_id=organization.id,
        site_code="hq",
        name="Headquarters",
    )
    next_site = Site.create(
        organization_id=organization.id,
        site_code="ber",
        name="Berlin Hub",
    )
    site_repo.add(site)
    site_repo.add(next_site)

    department = Department.create(
        organization_id=organization.id,
        department_code="pmo",
        name="PMO",
        site_id=site.id,
    )
    next_department = Department.create(
        organization_id=organization.id,
        department_code="pln",
        name="Planning",
        site_id=next_site.id,
    )
    department_repo.add(department)
    department_repo.add(next_department)

    session = _FakeSession()
    resource_repo = _FakeLinkedEmployeeResourceRepo()
    enterprise_audit_service = _FakeEnterpriseAuditService()
    service = EmployeeService(
        session=session,
        employee_repo=employee_repo,
        resource_repo=resource_repo,
        site_repo=site_repo,
        department_repo=department_repo,
        organization_repo=object(),
        tenant_context_service=_FakeTenantContext(organization),
        user_session=object(),
        enterprise_audit_service=enterprise_audit_service,
        uow_factory=_FakeEmployeeUnitOfWorkFactory(
            session=session,
            employees=employee_repo,
            resources=resource_repo,
            sites=site_repo,
            departments=department_repo,
            enterprise_audit_service=enterprise_audit_service,
        ),
        clock=SystemClock(),
    )

    created = service.create_employee(
        employee_code=" emp-1 ",
        full_name="  Alice Admin  ",
        department_id=f"  {department.id}  ",
        department="  PMO  ",
        site_id=f"  {site.id}  ",
        site_name="  Headquarters  ",
        title="  Planner  ",
        employment_type="part_time",
        email="  ALICE@EXAMPLE.COM  ",
        phone="  +234-555  ",
    )

    assert created.employee_code == "EMP-1"
    assert created.full_name == "Alice Admin"
    assert created.department_id == department.id
    assert created.department == "PMO"
    assert created.site_id == site.id
    assert created.site_name == "Headquarters"
    assert created.title == "Planner"
    assert created.employment_type is EmploymentType.PART_TIME
    assert created.email == "alice@example.com"
    assert created.phone == "+234-555"

    updated = service.update_employee(
        created.id,
        employee_code=" emp-2 ",
        full_name="  Alice Smith  ",
        department_id=next_department.id,
        site_id=next_site.id,
        title="  Senior Planner  ",
        employment_type="temporary",
        email="",
        phone="  +49-555-0101  ",
        expected_version=created.version,
    )

    assert updated.employee_code == "EMP-2"
    assert updated.full_name == "Alice Smith"
    assert updated.department_id == next_department.id
    assert updated.department == "Planning"
    assert updated.site_id == next_site.id
    assert updated.site_name == "Berlin Hub"
    assert updated.title == "Senior Planner"
    assert updated.employment_type is EmploymentType.TEMPORARY
    assert updated.email is None
    assert updated.phone == "+49-555-0101"

    try:
        service.create_employee(employee_code=" emp-2 ", full_name="Duplicate")
    except ValidationError as exc:
        assert exc.code == "EMPLOYEE_CODE_EXISTS"
    else:
        raise AssertionError("Expected duplicate employee code validation error.")

"""P18A: Project Resource transaction + event-pipeline convergence.

Covers: canonical ResourceUnitOfWork ownership, atomic audit, typed
ResourceMasterChanged/ResourceCapabilityChanged dispatch through the shared
transactional/post-commit pipeline (never a bespoke Signal[T]), pre-release no-op
discipline, cross-org integrity, and the Employee-driven Resource sync path.

The legacy `resources_changed` Signal these events used to also emit alongside
(temporary, P18A §7) is deleted as of P18B -- see test_p18b_resource_view_invalidation.py
for the typed ViewInvalidation cutover that replaced it.
"""

from __future__ import annotations

from datetime import date

import pytest

from src.core.modules.project_management.application.resources.resource_capability_events import (
    ResourceCapabilityChangeType,
    ResourceCapabilityChanged,
)
from src.core.modules.project_management.application.resources.resource_master_events import (
    ResourceMasterChangeType,
    ResourceMasterChanged,
)
from src.core.modules.project_management.domain.enums import CostType, WorkerType
from src.core.modules.project_management.infrastructure.persistence.orm.resource import ResourceORM
from src.core.modules.project_management.infrastructure.persistence.uow.resources.resource_unit_of_work import (
    SqlAlchemyResourceUnitOfWork,
)
from src.core.platform.application.history.audit.enterprise_audit_service import EnterpriseAuditService
from src.core.platform.common.exceptions import (
    BusinessRuleError,
    ConcurrencyError,
    NotFoundError,
    ValidationError,
)

_COUNTER = {"n": 0}


def _unique(prefix: str) -> str:
    _COUNTER["n"] += 1
    return f"{prefix}-{_COUNTER['n']}"


def _spy_master_events(services):
    captured = []
    services["resource_service"]._uow_factory._post_commit_bus.subscribe(
        ResourceMasterChanged, lambda event, context: captured.append(event)
    )
    return captured


def _spy_capability_events(services):
    captured = []
    services["resource_service"]._uow_factory._post_commit_bus.subscribe(
        ResourceCapabilityChanged, lambda event, context: captured.append(event)
    )
    return captured


# ---------------------------------------------------------------------------
# Resource Master
# ---------------------------------------------------------------------------


def test_create_resource_produces_one_typed_event(services):
    master_events = _spy_master_events(services)

    resource = services["resource_service"].create_resource(name=_unique("Create"))

    assert resource.version == 1
    assert len(master_events) == 1
    assert master_events[0].resource_id == resource.id
    assert master_events[0].version == 1
    assert master_events[0].change_type == ResourceMasterChangeType.CREATED
    assert master_events[0].tenant_id and master_events[0].organization_id


def test_real_update_produces_one_typed_event_and_bumps_version(services):
    service = services["resource_service"]
    resource = service.create_resource(name=_unique("Update"), role="Old Role")
    master_events = _spy_master_events(services)

    updated = service.update_resource(
        resource_id=resource.id, expected_version=resource.version, name=resource.name,
        code=resource.code, kind=resource.kind, role="New Role", hourly_rate=resource.hourly_rate,
        cost_type=resource.cost_type, currency_code=resource.currency_code,
        capacity_percent=resource.capacity_percent, address=resource.address, contact=resource.contact,
        worker_type=resource.worker_type, employee_id=None, department_id=None, site_id=None,
    )

    assert updated.role == "New Role"
    assert updated.version == resource.version + 1
    assert len(master_events) == 1
    assert master_events[0].change_type == ResourceMasterChangeType.UPDATED
    assert master_events[0].version == updated.version


def test_no_op_update_produces_zero_writes_zero_events(services):
    service = services["resource_service"]
    resource = service.create_resource(name=_unique("Noop"), role="Same Role")
    master_events = _spy_master_events(services)

    result = service.update_resource(
        resource_id=resource.id, expected_version=resource.version, name=resource.name,
        code=resource.code, kind=resource.kind, role=resource.role, hourly_rate=resource.hourly_rate,
        cost_type=resource.cost_type, currency_code=resource.currency_code,
        capacity_percent=resource.capacity_percent, address=resource.address, contact=resource.contact,
        worker_type=resource.worker_type, employee_id=None, department_id=None, site_id=None,
    )

    assert result.version == resource.version  # no synthetic bump
    assert master_events == []


def test_deactivate_and_reactivate_produce_typed_events(services):
    service = services["resource_service"]
    resource = service.create_resource(name=_unique("Lifecycle"))
    master_events = _spy_master_events(services)

    deactivated = service.deactivate_resource(resource_id=resource.id, expected_version=resource.version)
    assert deactivated.is_active is False
    assert master_events[-1].change_type == ResourceMasterChangeType.DEACTIVATED

    reactivated = service.reactivate_resource(
        resource_id=deactivated.id, expected_version=deactivated.version
    )
    assert reactivated.is_active is True
    assert master_events[-1].change_type == ResourceMasterChangeType.REACTIVATED
    assert len(master_events) == 2


def test_deactivate_already_inactive_is_rejected_not_silently_written(services):
    service = services["resource_service"]
    resource = service.create_resource(name=_unique("AlreadyInactive"))
    deactivated = service.deactivate_resource(resource_id=resource.id, expected_version=resource.version)
    master_events = _spy_master_events(services)

    with pytest.raises(BusinessRuleError):
        service.deactivate_resource(resource_id=deactivated.id, expected_version=deactivated.version)

    assert master_events == []


def test_activity_feed_entry_rides_the_same_transaction_as_the_mutation(services):
    """Regression: activity-feed staging must ride the SAME fresh UoW Session as the mutation
    itself. A separately-scoped ActivityService bound to the old process-lifetime shared Session
    would stage an entry this UoW's own commit() never persists."""
    service = services["resource_service"]
    resource = service.create_resource(name=_unique("ActivityAtomic"))

    activity = service._activity_service.list_recent(
        limit=50, entity_type="resource", entity_id=resource.id
    )
    assert any(entry.action == "resource.created" for entry in activity)

    skill = service.add_resource_skill(resource.id, "PY", "Python")
    activity_after_skill = service._activity_service.list_recent(
        limit=50, entity_type="resource", entity_id=resource.id
    )
    assert any(entry.action == "resource.skill.added" for entry in activity_after_skill)


def test_purge_produces_typed_event_and_deletes_row(services):
    service = services["resource_service"]
    resource = service.create_resource(name=_unique("Purge"))
    master_events = _spy_master_events(services)

    service.purge_resource(resource_id=resource.id, expected_version=resource.version)

    assert master_events[-1].change_type == ResourceMasterChangeType.PURGED
    with pytest.raises(NotFoundError):
        service.get_resource(resource.id)


def test_stale_version_update_raises_and_produces_zero_events(services):
    service = services["resource_service"]
    resource = service.create_resource(name=_unique("Stale"))
    master_events = _spy_master_events(services)

    with pytest.raises(ConcurrencyError):
        service.update_resource(
            resource_id=resource.id, expected_version=resource.version + 99, name="X",
            code=resource.code, kind=resource.kind, role="X", hourly_rate=resource.hourly_rate,
            cost_type=resource.cost_type, currency_code=resource.currency_code,
            capacity_percent=resource.capacity_percent, address="", contact="",
            worker_type=resource.worker_type, employee_id=None, department_id=None, site_id=None,
        )

    assert master_events == []


def test_audit_failure_rolls_back_and_produces_zero_events(services, monkeypatch):
    service = services["resource_service"]
    master_events = _spy_master_events(services)

    def _fail(self, **kwargs):
        raise RuntimeError("simulated audit failure")

    monkeypatch.setattr(EnterpriseAuditService, "record", _fail)
    with pytest.raises(RuntimeError, match="simulated audit failure"):
        service.create_resource(name=_unique("AuditFail"))
    monkeypatch.undo()

    assert master_events == []
    assert service.list_resources() == []


def test_commit_failure_rolls_back_and_produces_zero_events(services, monkeypatch):
    service = services["resource_service"]
    master_events = _spy_master_events(services)

    def _fail_commit(self):
        raise RuntimeError("simulated commit failure")

    monkeypatch.setattr(SqlAlchemyResourceUnitOfWork, "commit", _fail_commit)
    with pytest.raises(RuntimeError, match="simulated commit failure"):
        service.create_resource(name=_unique("CommitFail"))
    monkeypatch.undo()

    assert master_events == []


def test_cross_org_resource_is_not_visible_or_mutable_from_another_organization(services):
    session = services["session"]
    organization_service = services["organization_service"]
    default_org = services["tenant_context_service"].get_active_organization()
    other_org = organization_service.create_organization(
        organization_code=_unique("OTHERORG"), display_name="Other Org",
        timezone_name="UTC", base_currency="USD", is_enabled=False,
    )
    other_tenant_id = getattr(other_org, "tenant_id", None) or default_org.tenant_id
    other_resource = ResourceORM(
        id=_unique("other-resource"), tenant_id=other_tenant_id, organization_id=other_org.id,
        name="Other Org Resource", role="Planner", hourly_rate=90.0, is_active=True,
        capacity_percent=100.0, cost_type=CostType.LABOR, worker_type=WorkerType.EXTERNAL, version=1,
    )
    session.add(other_resource)
    session.commit()

    service = services["resource_service"]
    assert service._resource_repo.get(other_resource.id) is None  # active-org-scoped read
    with pytest.raises(NotFoundError):
        service.update_resource(
            resource_id=other_resource.id, expected_version=1, name="Hijacked",
            code="", kind="PERSON", role="", hourly_rate=0, cost_type=CostType.LABOR,
            currency_code=None, capacity_percent=100.0, address="", contact="",
            worker_type=WorkerType.EXTERNAL, employee_id=None, department_id=None, site_id=None,
        )


# ---------------------------------------------------------------------------
# Resource Capability (skills / certifications)
# ---------------------------------------------------------------------------


def test_add_update_remove_skill_each_produce_one_typed_capability_event(services):
    service = services["resource_service"]
    resource = service.create_resource(name=_unique("SkillOwner"))
    capability_events = _spy_capability_events(services)

    skill = service.add_resource_skill(resource.id, "PY", "Python", proficiency="advanced")
    assert capability_events[-1].change_type == ResourceCapabilityChangeType.ADDED
    assert capability_events[-1].child_type == "ResourceSkill"

    updated = service.update_resource_skill(
        skill_id=skill.id, expected_version=skill.version, skill_code="PY",
        skill_name="Python 3", proficiency="expert", notes="",
    )
    assert capability_events[-1].change_type == ResourceCapabilityChangeType.UPDATED
    assert updated.version == skill.version + 1

    service.remove_resource_skill(updated.id, expected_version=updated.version)
    assert capability_events[-1].change_type == ResourceCapabilityChangeType.REMOVED
    assert len(capability_events) == 3


def test_add_update_remove_certification_each_produce_one_typed_capability_event(services):
    service = services["resource_service"]
    resource = service.create_resource(name=_unique("CertOwner"))
    capability_events = _spy_capability_events(services)

    cert = service.add_resource_certification(
        resource.id, "SAFETY-1", "Safety Certification",
        issued_date=date.today(), expiry_date=None,
    )
    assert capability_events[-1].change_type == ResourceCapabilityChangeType.ADDED
    assert capability_events[-1].child_type == "ResourceCertification"

    updated = service.update_resource_certification(
        cert_id=cert.id, expected_version=cert.version, certification_code="SAFETY-1",
        certification_name="Safety Certification II",
    )
    assert capability_events[-1].change_type == ResourceCapabilityChangeType.UPDATED

    service.remove_resource_certification(updated.id, expected_version=updated.version)
    assert capability_events[-1].change_type == ResourceCapabilityChangeType.REMOVED
    assert len(capability_events) == 3


def test_duplicate_skill_code_is_rejected_before_any_write(services):
    service = services["resource_service"]
    resource = service.create_resource(name=_unique("DupSkill"))
    service.add_resource_skill(resource.id, "PY", "Python")
    capability_events = _spy_capability_events(services)

    with pytest.raises(ValidationError):
        service.add_resource_skill(resource.id, "PY", "Python Duplicate")

    assert capability_events == []


def test_no_op_skill_update_produces_zero_writes_zero_events(services):
    service = services["resource_service"]
    resource = service.create_resource(name=_unique("NoopSkill"))
    skill = service.add_resource_skill(resource.id, "PY", "Python", proficiency="advanced", notes="x")
    capability_events = _spy_capability_events(services)

    result = service.update_resource_skill(
        skill_id=skill.id, expected_version=skill.version, skill_code="PY",
        skill_name="Python", proficiency="advanced", notes="x",
    )

    assert result.version == skill.version
    assert capability_events == []


def test_skill_belongs_to_cross_org_resource_is_not_mutable(services):
    session = services["session"]
    organization_service = services["organization_service"]
    default_org = services["tenant_context_service"].get_active_organization()
    other_org = organization_service.create_organization(
        organization_code=_unique("SKILLORG"), display_name="Skill Other Org",
        timezone_name="UTC", base_currency="USD", is_enabled=False,
    )
    other_tenant_id = getattr(other_org, "tenant_id", None) or default_org.tenant_id
    other_resource = ResourceORM(
        id=_unique("skill-other-resource"), tenant_id=other_tenant_id, organization_id=other_org.id,
        name="Other Org Resource", role="Planner", hourly_rate=90.0, is_active=True,
        capacity_percent=100.0, cost_type=CostType.LABOR, worker_type=WorkerType.EXTERNAL, version=1,
    )
    session.add(other_resource)
    session.commit()

    service = services["resource_service"]
    with pytest.raises(NotFoundError):
        service.add_resource_skill(other_resource.id, "PY", "Python")


def test_capability_audit_failure_rolls_back_and_produces_zero_events(services, monkeypatch):
    service = services["resource_service"]
    resource = service.create_resource(name=_unique("CapAuditFail"))
    capability_events = _spy_capability_events(services)

    def _fail(self, **kwargs):
        raise RuntimeError("simulated audit failure")

    monkeypatch.setattr(EnterpriseAuditService, "record", _fail)
    with pytest.raises(RuntimeError, match="simulated audit failure"):
        service.add_resource_skill(resource.id, "PY", "Python")
    monkeypatch.undo()

    assert capability_events == []


def test_capability_commit_failure_rolls_back_and_produces_zero_events(services, monkeypatch):
    service = services["resource_service"]
    resource = service.create_resource(name=_unique("CapCommitFail"))
    capability_events = _spy_capability_events(services)

    def _fail_commit(self):
        raise RuntimeError("simulated commit failure")

    monkeypatch.setattr(SqlAlchemyResourceUnitOfWork, "commit", _fail_commit)
    with pytest.raises(RuntimeError, match="simulated commit failure"):
        service.add_resource_skill(resource.id, "PY", "Python")
    monkeypatch.undo()

    assert capability_events == []


# ---------------------------------------------------------------------------
# Event pipeline / transaction architecture guards
# ---------------------------------------------------------------------------


def test_bespoke_signal_transport_is_gone_from_event_modules():
    import inspect

    from src.core.modules.project_management.application.resources import (
        resource_capability_events,
        resource_master_events,
    )

    for module in (resource_master_events, resource_capability_events):
        source = inspect.getsource(module)
        assert "Signal(" not in source
        assert "from src.core.shared.events.signal import Signal" not in source


def test_resource_events_are_plain_frozen_dataclasses_not_qt_signals():
    import dataclasses

    assert dataclasses.is_dataclass(ResourceMasterChanged)
    assert dataclasses.is_dataclass(ResourceCapabilityChanged)


def test_two_independent_operations_use_two_independent_sessions(services):
    service = services["resource_service"]
    sessions_seen = []
    original_create = service._uow_factory.create

    def _spy_create(*, context):
        uow = original_create(context=context)
        sessions_seen.append(uow._session)
        return uow

    service._uow_factory.create = _spy_create
    service.create_resource(name=_unique("SessA"))
    service.create_resource(name=_unique("SessB"))

    assert len(sessions_seen) == 2
    assert sessions_seen[0] is not sessions_seen[1]
    assert sessions_seen[0].bind is sessions_seen[1].bind  # same engine, independent sessions


def test_repos_and_audit_share_one_session_within_one_operation(services):
    from src.core.modules.project_management.infrastructure.persistence.uow.resources.resource_unit_of_work import (
        SqlAlchemyResourceUnitOfWorkFactory,
    )

    factory = services["resource_service"]._uow_factory
    assert isinstance(factory, SqlAlchemyResourceUnitOfWorkFactory)
    from src.core.shared.events.domain_event_context import DomainEventContext

    uow = factory.create(context=DomainEventContext(correlation_id="test", causation_id=None))
    try:
        assert uow.resources.session is uow._session
        assert uow.skills.session is uow._session
        assert uow.certifications.session is uow._session
        assert uow._enterprise_audit_service._session is uow._session
    finally:
        uow._rollback_and_close()


def test_no_platform_to_business_module_concrete_infrastructure_import_added():
    """P18A §9: the Employee-driven Resource sync path must not import PM's concrete
    ResourceMasterChanged event class into Platform code -- proven by the same AST-based
    architecture guard this ADR already uses (test_platform_does_not_import_business_modules.py),
    re-run here narrowly against the two files this phase touched."""
    import ast

    from src.tests.path_rewrites import REPO_ROOT

    for relative in (
        "src/core/platform/application/master_data/employee/employee_service.py",
        "src/core/platform/application/master_data/employee/employee_support.py",
        "src/core/platform/contract/interface/master_data/employee/contracts.py",
    ):
        path = REPO_ROOT / relative
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                assert not node.module.startswith("src.core.modules"), (
                    f"{relative}:{node.lineno} imports {node.module}"
                )


# ---------------------------------------------------------------------------
# Employee-driven Resource synchronization path (P18A §8)
# ---------------------------------------------------------------------------


def test_employee_update_produces_real_resource_mutation_and_typed_event(services):
    employee_service = services["employee_service"]
    resource_service = services["resource_service"]
    employee = employee_service.create_employee(
        employee_code=_unique("EMP"), full_name="Alex Doe", title="Engineer"
    )
    resource = resource_service.create_resource(
        name="placeholder", worker_type=WorkerType.EMPLOYEE, employee_id=employee.id
    )
    master_events = _spy_master_events(services)

    updated_employee = employee_service.update_employee(
        employee.id, full_name="Alex Updated", title="Senior Engineer"
    )

    assert updated_employee.full_name == "Alex Updated"
    refreshed = resource_service.get_resource(resource.id)
    assert refreshed.name == "Alex Updated"  # real Resource row mutation, not just staleness
    assert refreshed.role == "Senior Engineer"
    assert refreshed.version == resource.version + 1
    assert len(master_events) == 1
    assert master_events[0].resource_id == resource.id
    assert master_events[0].version == refreshed.version
    assert master_events[0].change_type == ResourceMasterChangeType.UPDATED


def test_employee_update_with_no_linked_employee_resource_produces_zero_resource_events(services):
    employee_service = services["employee_service"]
    employee = employee_service.create_employee(
        employee_code=_unique("EMP"), full_name="No Resource Person"
    )
    master_events = _spy_master_events(services)

    employee_service.update_employee(employee.id, full_name="No Resource Person 2")

    assert master_events == []


def test_employee_update_and_resource_mutation_are_one_atomic_transaction(services, monkeypatch):
    """If the Employee mutation's own commit fails, the linked Resource row must not have been
    persisted either -- proving the sync rides inside Employee's own UnitOfWork, not a second,
    independently-committed transaction."""
    from src.core.platform.infrastructure.persistence.uow.employee_unit_of_work import (
        SqlAlchemyEmployeeUnitOfWork,
    )

    employee_service = services["employee_service"]
    resource_service = services["resource_service"]
    employee = employee_service.create_employee(
        employee_code=_unique("EMP"), full_name="Atomic Test", title="Engineer"
    )
    resource = resource_service.create_resource(
        name="placeholder", worker_type=WorkerType.EMPLOYEE, employee_id=employee.id
    )
    master_events = _spy_master_events(services)

    def _fail_commit(self):
        raise RuntimeError("simulated employee commit failure")

    monkeypatch.setattr(SqlAlchemyEmployeeUnitOfWork, "commit", _fail_commit)
    with pytest.raises(RuntimeError, match="simulated employee commit failure"):
        employee_service.update_employee(employee.id, full_name="Should Not Persist", title="Should Not Persist")
    monkeypatch.undo()

    refreshed = resource_service.get_resource(resource.id)
    assert refreshed.name != "Should Not Persist"
    assert master_events == []

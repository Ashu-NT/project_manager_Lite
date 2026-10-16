from __future__ import annotations

from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from src.core.modules.project_management.api.desktop.portfolio.api import (
    ProjectManagementPortfolioDesktopApi,
)
from src.core.modules.project_management.api.desktop.register.api import (
    ProjectManagementRegisterDesktopApi,
)
from src.core.modules.project_management.api.desktop.scheduling.api import (
    ProjectManagementSchedulingDesktopApi,
)
from src.core.modules.project_management.application.portfolio.commands import (
    PortfolioDependencyCommandHandler,
    PortfolioIntakeCommandHandler,
    PortfolioScenarioCommandHandler,
    PortfolioTemplateCommandHandler,
)
from src.core.modules.project_management.application.portfolio.dto.commands.intake import (
    PortfolioIntakeCreateCommand,
    PortfolioIntakeUpdateCommand,
)
from src.core.modules.project_management.application.portfolio.dto.commands.project_dependencies import (
    PortfolioDependencyCreateCommand,
    PortfolioDependencyRemoveCommand,
)
from src.core.modules.project_management.application.portfolio.dto.commands.scenarios import (
    PortfolioScenarioCreateCommand,
    PortfolioScenarioUpdateCommand,
)
from src.core.modules.project_management.application.portfolio.dto.commands.scoring_templates import (
    PortfolioTemplateActivateCommand,
    PortfolioTemplateCreateCommand,
)
from src.core.modules.project_management.application.portfolio.mappers.intake import (
    map_intake_response,
)
from src.core.modules.project_management.application.risk.commands.register_lifecycle import (
    RegisterLifecycleHandler,
)
from src.core.modules.project_management.application.risk.dto.commands.register_entries import (
    RegisterEntryBulkStatusCommand,
    RegisterEntryCreateCommand,
    RegisterEntryDeleteCommand,
    RegisterEntryUpdateCommand,
)
from src.core.modules.project_management.application.scheduling.baselines.commands.lifecycle import (
    BaselineCommandHandler,
)
from src.core.modules.project_management.application.scheduling.dto.commands.baselines import (
    SchedulingBaselineApproveCommand,
    SchedulingBaselineCreateCommand,
    SchedulingBaselineDeleteCommand,
    SchedulingBaselineRejectCommand,
    SchedulingBaselineSubmitCommand,
)
from src.core.modules.project_management.application.scheduling.dto.commands.dependencies import (
    SchedulingDependencyCreateCommand,
    SchedulingDependencyUpdateCommand,
)
from src.core.modules.project_management.application.tasks.dto.commands.task_dependencies import (
    TaskDependencyCreateCommand,
    TaskDependencyUpdateCommand,
)
from src.core.modules.project_management.domain.portfolio import (
    PortfolioIntakeStatus,
    PortfolioScoringTemplate,
)
from src.core.modules.project_management.domain.risk.register import RegisterEntryStatus
from src.core.modules.project_management.domain.scheduling.baseline import (
    BaselineStatus,
    ProjectBaseline,
)
from src.core.platform.common.exceptions import (
    BusinessRuleError,
    ConcurrencyError,
    NotFoundError,
)


@pytest.fixture
def harness(monkeypatch):
    modules = [
        "portfolio.commands.portfolio_dependencies",
        "portfolio.commands.portfolio_intake",
        "portfolio.commands.portfolio_scenarios",
        "portfolio.commands.portfolio_templates",
        "risk.commands.register_lifecycle",
        "scheduling.baselines.commands.lifecycle",
    ]
    for module in modules:
        prefix = f"src.core.modules.project_management.application.{module}"
        monkeypatch.setattr(f"{prefix}.require_permission", MagicMock())
        monkeypatch.setattr(f"{prefix}.require_project_permission", MagicMock(), raising=False)
        monkeypatch.setattr(f"{prefix}.record_activity", MagicMock())
        monkeypatch.setattr(f"{prefix}.record_audit_entry", MagicMock(), raising=False)
    uow = MagicMock()
    uow.__enter__.return_value = uow
    uow.dependencies.list.return_value = []
    uow.scoring_templates.list.return_value = []
    uow.entries.list_entries.return_value = []
    factory = MagicMock()
    factory.create.return_value = uow
    scope = SimpleNamespace(tenant_id="tenant", organization_id="org")
    context = MagicMock()
    context.require_active_scope_ids.return_value = scope
    policy = MagicMock()
    policy.organization_id.return_value = "org"
    policy.scope.return_value = scope
    policy.accessible_projects.return_value = [SimpleNamespace(id="p1", name="One"), SimpleNamespace(id="p2", name="Two")]
    policy.validate_project_ids.side_effect = lambda ids: sorted(set(ids))
    policy.validate_intake_ids.side_effect = lambda ids: sorted(set(ids))
    template = PortfolioScoringTemplate.create(organization_id="org", name="Balanced")
    policy.resolve_scoring_template.return_value = template
    return SimpleNamespace(uow=uow, factory=factory, policy=policy, context=context, repo=MagicMock())


def test_portfolio_create_commands_preserve_decimal_zero_and_scope(harness):
    h = harness
    intake = PortfolioIntakeCommandHandler(intake_repo=h.repo, policy=h.policy, uow_factory=h.factory)
    item = intake.create_intake_item(PortfolioIntakeCreateCommand("Intake", "Sponsor", requested_budget=Decimal("0.00"), status="approved"))
    assert item.requested_budget == Decimal("0.00")
    assert item.status == PortfolioIntakeStatus.APPROVED
    h.uow.intake.add.assert_called_once()
    persisted = h.uow.intake.add.call_args.args[0]
    assert map_intake_response(persisted) == item
    assert type(persisted) is not type(item)
    scenarios = PortfolioScenarioCommandHandler(scenario_repo=h.repo, policy=h.policy, uow_factory=h.factory)
    scenario = scenarios.create_scenario(PortfolioScenarioCreateCommand("Zero", Decimal(0), 0, ("p2", "p1")))
    assert scenario.budget_limit == Decimal(0)
    assert scenario.capacity_limit_percent == 0
    assert scenario.project_ids == ["p1", "p2"]
    h.policy.validate_project_ids.assert_called_once_with(["p1", "p2"])
    assert h.uow.commit.call_count == 2
    assert h.uow.record_event.call_count == 2


def test_portfolio_updates_distinguish_omitted_null_and_zero(harness):
    h = harness
    commands = PortfolioScenarioCommandHandler(scenario_repo=h.repo, policy=h.policy, uow_factory=h.factory)
    original = commands.create_scenario(PortfolioScenarioCreateCommand("Original", Decimal("12.34"), 50))
    h.repo.get.return_value = original
    assert commands.update_scenario(PortfolioScenarioUpdateCommand(original.id, notes="changed")).budget_limit == Decimal("12.34")
    cleared = commands.update_scenario(PortfolioScenarioUpdateCommand(original.id, budget_limit=None, capacity_limit_percent=None))
    assert cleared.budget_limit is None and cleared.capacity_limit_percent is None
    zero = commands.update_scenario(PortfolioScenarioUpdateCommand(original.id, budget_limit=Decimal(0), capacity_limit_percent=0))
    assert zero.budget_limit == Decimal(0) and zero.capacity_limit_percent == 0
    intake = PortfolioIntakeCommandHandler(intake_repo=h.repo, policy=h.policy, uow_factory=h.factory)
    item = intake.create_intake_item(PortfolioIntakeCreateCommand("Intake", "Sponsor", target_start_date=date(2026, 1, 2)))
    h.repo.get.return_value = item
    assert intake.update_intake_item(PortfolioIntakeUpdateCommand(item.id)).target_start_date == date(2026, 1, 2)
    assert intake.update_intake_item(PortfolioIntakeUpdateCommand(item.id, target_start_date=None)).target_start_date is None


def test_portfolio_dependency_and_template_commands_use_operation_uows(harness):
    h = harness
    dependencies = PortfolioDependencyCommandHandler(dependency_repo=h.repo, policy=h.policy, uow_factory=h.factory)
    dependency = dependencies.create_project_dependency(PortfolioDependencyCreateCommand("p1", "p2", summary="Delivery"))
    h.repo.get.return_value = dependency
    dependencies.remove_project_dependency(PortfolioDependencyRemoveCommand(dependency.id))
    h.uow.dependencies.delete.assert_called_once_with(dependency.id)
    templates = PortfolioTemplateCommandHandler(scoring_template_repo=h.repo, policy=h.policy, uow_factory=h.factory)
    template = templates.create_scoring_template(PortfolioTemplateCreateCommand("New", activate=False))
    h.repo.get.return_value = h.uow.scoring_templates.add.call_args.args[0]
    activated = templates.activate_scoring_template(PortfolioTemplateActivateCommand(template.id))
    assert activated.is_active
    assert h.factory.create.call_count == 4
    assert h.uow.commit.call_count == 4


def _register(h):
    return RegisterLifecycleHandler(project_repo=h.repo, register_repo=h.repo, user_session=None, tenant_context_service=h.context, uow_factory=h.factory)


def test_register_command_consumption_checks_scope_versions_and_bulk_uow(harness):
    h = harness
    commands = _register(h)
    entry = commands.create_entry(RegisterEntryCreateCommand("p1", title="Risk", severity="critical", code="RISK-1"))
    h.repo.get.return_value = h.uow.entries.add.call_args.args[0]
    with pytest.raises(ConcurrencyError, match="changed"):
        commands.update_entry(RegisterEntryUpdateCommand(entry.id, "p1", title="Risk", expected_version=entry.version + 1))
    with pytest.raises(NotFoundError):
        commands.update_entry(RegisterEntryUpdateCommand(entry.id, "p2", title="Risk"))
    updated = commands.update_entry(RegisterEntryUpdateCommand(entry.id, "p1", title="Updated", expected_version=entry.version))
    assert updated.title == "Updated"
    before = h.factory.create.call_count
    entries = commands.bulk_set_entry_status(RegisterEntryBulkStatusCommand((entry.id, entry.id), "closed"))
    assert all(item.status == RegisterEntryStatus.CLOSED for item in entries)
    assert h.factory.create.call_count == before + 1
    commands.delete_entry(RegisterEntryDeleteCommand(entry.id))
    h.uow.entries.delete.assert_called_once_with(entry.id)


def test_module_guard_runs_before_consuming_command(harness):
    commands = _register(harness)
    commands._module_catalog_service = MagicMock()
    commands._module_catalog_service.get_entitlement.return_value = SimpleNamespace(runtime_enabled=False, label="PM", lifecycle_status="inactive")
    with pytest.raises(BusinessRuleError, match="not enabled"):
        commands.create_entry(RegisterEntryCreateCommand("p1", title="Risk"))
    harness.factory.create.assert_not_called()


def test_baseline_commands_preserve_valuation_date_lifecycle_and_uow(harness, monkeypatch):
    h = harness
    commands = BaselineCommandHandler(MagicMock(), h.repo, MagicMock(), MagicMock(), h.repo, MagicMock(), MagicMock(), tenant_context_service=h.context, uow_factory=lambda: h.uow)
    baseline = ProjectBaseline.create("p1", "Freeze")
    apply = MagicMock(return_value=baseline)
    monkeypatch.setattr(commands, "_apply_baseline_creation_decision", apply)
    valuation_date = date(2026, 2, 3)
    assert commands.create_baseline(SchedulingBaselineCreateCommand("p1", "Freeze", valuation_date)) is baseline
    apply.assert_called_once_with(project_id="p1", name="Freeze", rate_as_of=valuation_date)
    h.repo.get_baseline.return_value = baseline
    h.repo.get_approved_baseline.return_value = None
    commands.submit_baseline(SchedulingBaselineSubmitCommand(baseline.id, "Planner", "Ready"))
    assert baseline.status == BaselineStatus.SUBMITTED
    commands.approve_baseline(SchedulingBaselineApproveCommand(baseline.id, "Approver", "Accepted"))
    assert baseline.status == BaselineStatus.APPROVED
    commands.delete_baseline(SchedulingBaselineDeleteCommand(baseline.id))
    h.repo.delete_baseline.assert_called_once_with(baseline.id)
    other = ProjectBaseline.create("p1", "Rejected")
    other.submit(submitted_by="Planner")
    h.repo.get_baseline.return_value = other
    commands.reject_baseline(SchedulingBaselineRejectCommand(other.id, "Rework"))
    assert other.status == BaselineStatus.REJECTED
    assert h.uow.commit.call_count == 5
    assert h.uow.record_event.call_count == 5


@pytest.mark.parametrize(("method", "command", "handler_slot", "serializer"), [
    ("create_intake_item", PortfolioIntakeCreateCommand("Intake", "Sponsor"), "portfolio_intake_commands", None),
    ("update_intake_item_status", PortfolioIntakeUpdateCommand("i1", status="APPROVED"), "portfolio_intake_commands", None),
    ("create_scenario", PortfolioScenarioCreateCommand("Scenario"), "portfolio_scenario_commands", "serialize_scenario"),
    ("create_scoring_template", PortfolioTemplateCreateCommand("Template"), "portfolio_template_commands", None),
    ("activate_scoring_template", PortfolioTemplateActivateCommand("t1"), "portfolio_template_commands", None),
])
def test_portfolio_desktop_passes_same_command_to_injected_handler(monkeypatch, method, command, handler_slot, serializer):
    handler = MagicMock()
    serialize = MagicMock(return_value="serialized")
    if serializer:
        monkeypatch.setattr(f"src.core.modules.project_management.api.desktop.portfolio.api.{serializer}", serialize)
    api = ProjectManagementPortfolioDesktopApi(**{handler_slot: handler})
    handler_method = "update_intake_item" if method == "update_intake_item_status" else method
    result = getattr(api, method)(command)
    if serializer:
        assert result == "serialized"
        serialize.assert_called_once_with(getattr(handler, handler_method).return_value)
    else:
        assert result is getattr(handler, handler_method).return_value
    getattr(handler, handler_method).assert_called_once_with(command)


@pytest.mark.parametrize(("method", "command"), [
    ("create_entry", RegisterEntryCreateCommand("p1", title="Risk")),
    ("update_entry", RegisterEntryUpdateCommand("e1", "p1", title="Risk")),
])
def test_register_desktop_passes_same_command(monkeypatch, method, command):
    handler = MagicMock()
    monkeypatch.setattr("src.core.modules.project_management.api.desktop.register.api.serialize_entry", lambda entry, **kwargs: entry)
    api = ProjectManagementRegisterDesktopApi(register_lifecycle_commands=handler)
    assert getattr(api, method)(command) is getattr(handler, method).return_value
    getattr(handler, method).assert_called_once_with(command)


@pytest.mark.parametrize(("method", "command"), [
    ("create_baseline", SchedulingBaselineCreateCommand("p1")),
    ("submit_baseline", SchedulingBaselineSubmitCommand("b1")),
    ("approve_baseline", SchedulingBaselineApproveCommand("b1")),
    ("reject_baseline", SchedulingBaselineRejectCommand("b1")),
    ("delete_baseline", SchedulingBaselineDeleteCommand("b1")),
])
def test_scheduling_desktop_passes_same_baseline_command(method, command):
    handler = MagicMock()
    handler.create_baseline.return_value = ProjectBaseline.create("p1", "Freeze")
    api = ProjectManagementSchedulingDesktopApi(baseline_commands=handler)
    getattr(api, method)(command)
    getattr(handler, method).assert_called_once_with(command)


def test_scheduling_dependency_adapter_passes_task_commands_and_expected_version(monkeypatch):
    handler = MagicMock()
    query = MagicMock()
    query.get_task.return_value = None
    monkeypatch.setattr("src.core.modules.project_management.api.desktop.scheduling.api.serialize_dependency", lambda dependency, **kwargs: dependency)
    api = ProjectManagementSchedulingDesktopApi(task_dependency_commands=handler, task_detail_query=query)
    create = SchedulingDependencyCreateCommand("t1", "t2", "SUCCESSOR", lag_days=0)
    api.create_dependency(create)
    handler.add_dependency.assert_called_once_with(create)
    assert handler.add_dependency.call_args.args[0] is create
    assert isinstance(create, TaskDependencyCreateCommand)
    assert create.linked_task_id == create.related_activity_id == "t2"
    update = SchedulingDependencyUpdateCommand("d1", lag_days=0, expected_version=7)
    api.update_dependency(update, current_task_id="t1")
    handler.update_dependency.assert_called_once_with(update)
    assert handler.update_dependency.call_args.args[0] is update
    assert isinstance(update, TaskDependencyUpdateCommand)

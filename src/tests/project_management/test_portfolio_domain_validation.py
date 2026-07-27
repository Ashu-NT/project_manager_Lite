from __future__ import annotations

from datetime import date
from types import SimpleNamespace

import pytest

from src.core.modules.project_management.application.portfolio.commands.portfolio_intake import (
    PortfolioIntakeCommandMixin,
)
from src.core.modules.project_management.application.portfolio.commands.portfolio_dependencies import (
    PortfolioDependencyCommandMixin,
)
from src.core.modules.project_management.application.portfolio.commands.portfolio_scenarios import (
    PortfolioScenarioCommandMixin,
)
from src.core.modules.project_management.application.portfolio.commands.portfolio_templates import (
    PortfolioTemplateCommandMixin,
)
from src.core.modules.project_management.application.portfolio.utils.portfolio_support import (
    PortfolioSupportMixin,
)
from src.core.modules.project_management.domain.portfolio import (
    PortfolioIntakeItem,
    PortfolioIntakeStatus,
    PortfolioProjectDependency,
    PortfolioScenario,
    PortfolioScoringTemplate,
)
from src.core.modules.project_management.domain.enums import DependencyType
from src.core.platform.common.exceptions import NotFoundError, ValidationError


class _FakeSession:
    def commit(self) -> None:
        return None

    def rollback(self) -> None:
        return None


class _FakeTenantContext:
    def __init__(self, organization_id: str = "org-1") -> None:
        self.organization_id = organization_id

    def require_active_organization_id(self, *, operation_label: str) -> str:
        return self.organization_id


class _FakeProjectRepo:
    def __init__(self, project_ids: list[str] | None = None) -> None:
        self._projects = {
            project_id: SimpleNamespace(id=project_id, name=f"Project {project_id}")
            for project_id in (project_ids or ["proj-1", "proj-2"])
        }

    def list(self):
        return list(self._projects.values())


class _FakeIntakeRepo:
    def __init__(self) -> None:
        self._items: dict[str, PortfolioIntakeItem] = {}

    def add(self, item: PortfolioIntakeItem) -> None:
        self._items[item.id] = item

    def get(self, item_id: str) -> PortfolioIntakeItem | None:
        return self._items.get(item_id)

    def update(self, item: PortfolioIntakeItem) -> None:
        if item.id not in self._items:
            raise NotFoundError("Portfolio intake item not found.", code="PORTFOLIO_INTAKE_NOT_FOUND")
        item.version += 1
        self._items[item.id] = item

    def list(self) -> list[PortfolioIntakeItem]:
        return list(self._items.values())

    def delete(self, item_id: str) -> None:
        self._items.pop(item_id, None)


class _FakeScenarioRepo:
    def __init__(self) -> None:
        self._scenarios: dict[str, PortfolioScenario] = {}

    def add(self, scenario: PortfolioScenario) -> None:
        self._scenarios[scenario.id] = scenario

    def get(self, scenario_id: str) -> PortfolioScenario | None:
        return self._scenarios.get(scenario_id)

    def update(self, scenario: PortfolioScenario) -> None:
        if scenario.id not in self._scenarios:
            raise NotFoundError("Portfolio scenario not found.", code="PORTFOLIO_SCENARIO_NOT_FOUND")
        self._scenarios[scenario.id] = scenario

    def list(self) -> list[PortfolioScenario]:
        return list(self._scenarios.values())

    def delete(self, scenario_id: str) -> None:
        self._scenarios.pop(scenario_id, None)


class _FakeTemplateRepo:
    def __init__(self) -> None:
        self._templates: dict[str, PortfolioScoringTemplate] = {}

    def add(self, template: PortfolioScoringTemplate) -> None:
        self._templates[template.id] = template

    def get(self, template_id: str) -> PortfolioScoringTemplate | None:
        return self._templates.get(template_id)

    def update(self, template: PortfolioScoringTemplate) -> None:
        if template.id not in self._templates:
            raise NotFoundError(
                "Portfolio scoring template not found.",
                code="PORTFOLIO_TEMPLATE_NOT_FOUND",
            )
        self._templates[template.id] = template

    def list(self) -> list[PortfolioScoringTemplate]:
        return list(self._templates.values())


class _FakeDependencyRepo:
    def __init__(self) -> None:
        self._dependencies: dict[str, PortfolioProjectDependency] = {}

    def add(self, dependency: PortfolioProjectDependency) -> None:
        self._dependencies[dependency.id] = dependency

    def get(self, dependency_id: str) -> PortfolioProjectDependency | None:
        return self._dependencies.get(dependency_id)

    def list(self) -> list[PortfolioProjectDependency]:
        return list(self._dependencies.values())

    def delete(self, dependency_id: str) -> None:
        self._dependencies.pop(dependency_id, None)


class _PortfolioHarness(
    PortfolioIntakeCommandMixin,
    PortfolioDependencyCommandMixin,
    PortfolioScenarioCommandMixin,
    PortfolioSupportMixin,
    PortfolioTemplateCommandMixin,
):
    DEFAULT_TEMPLATE_NAME = "Balanced PMO"
    DEFAULT_TEMPLATE_SUMMARY = (
        "Balanced template for strategic fit, value, urgency, and delivery risk."
    )

    def __init__(self, *, project_ids: list[str] | None = None) -> None:
        self._session = _FakeSession()
        self._intake_repo = _FakeIntakeRepo()
        self._scenario_repo = _FakeScenarioRepo()
        self._scoring_template_repo = _FakeTemplateRepo()
        self._dependency_repo = _FakeDependencyRepo()
        self._project_repo = _FakeProjectRepo(project_ids=project_ids)
        self._tenant_context_service = _FakeTenantContext()
        self._user_session = object()


def _make_service(
    monkeypatch: pytest.MonkeyPatch,
    *,
    project_ids: list[str] | None = None,
) -> _PortfolioHarness:
    monkeypatch.setattr(
        "src.core.modules.project_management.application.portfolio.commands.portfolio_intake.require_permission",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        "src.core.modules.project_management.application.portfolio.commands.portfolio_scenarios.require_permission",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        "src.core.modules.project_management.application.portfolio.commands.portfolio_templates.require_permission",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        "src.core.modules.project_management.application.portfolio.commands.portfolio_dependencies.require_permission",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        "src.core.modules.project_management.application.portfolio.utils.portfolio_support.filter_project_rows",
        lambda projects, *_args, **_kwargs: list(projects),
    )
    return _PortfolioHarness(project_ids=project_ids)


def test_portfolio_entities_normalize_local_fields():
    intake = PortfolioIntakeItem.create(
        organization_id="  org-1  ",
        title="  New Initiative  ",
        sponsor_name="  PMO  ",
        summary="  Lift operational resilience.  ",
        requested_budget="1250.5",
        requested_capacity_percent="30",
        target_start_date=date(2026, 7, 1),
        strategic_score="5",
        value_score="4",
        urgency_score="3",
        risk_score="2",
        scoring_template_id="  tpl-1  ",
        scoring_template_name="  Value First  ",
        strategic_weight="4",
        value_weight="3",
        urgency_weight="2",
        risk_weight="1",
        status="review",
    )

    assert intake.organization_id == "org-1"
    assert intake.title == "New Initiative"
    assert intake.sponsor_name == "PMO"
    assert intake.summary == "Lift operational resilience."
    assert intake.requested_budget == pytest.approx(1250.5)
    assert intake.requested_capacity_percent == pytest.approx(30.0)
    assert intake.target_start_date == date(2026, 7, 1)
    assert intake.strategic_score == 5
    assert intake.value_score == 4
    assert intake.urgency_score == 3
    assert intake.risk_score == 2
    assert intake.scoring_template_id == "tpl-1"
    assert intake.scoring_template_name == "Value First"
    assert intake.status == PortfolioIntakeStatus.REVIEW

    scenario = PortfolioScenario.create(
        organization_id="  org-1  ",
        name="  Option A  ",
        budget_limit="5000",
        capacity_limit_percent="65",
        project_ids=[" proj-2 ", "proj-1", "proj-1"],
        intake_item_ids=[" intake-2 ", "intake-1", "intake-1"],
        notes="  Sequence work in two waves.  ",
    )

    assert scenario.organization_id == "org-1"
    assert scenario.name == "Option A"
    assert scenario.budget_limit == pytest.approx(5000.0)
    assert scenario.capacity_limit_percent == pytest.approx(65.0)
    assert scenario.project_ids == ["proj-1", "proj-2"]
    assert scenario.intake_item_ids == ["intake-1", "intake-2"]
    assert scenario.notes == "Sequence work in two waves."

    template = PortfolioScoringTemplate.create(
        organization_id="  org-1  ",
        name="  Value First  ",
        summary="  Bias toward commercial return.  ",
        strategic_weight="1",
        value_weight="5",
        urgency_weight="1",
        risk_weight="0",
        is_active=True,
    )

    assert template.organization_id == "org-1"
    assert template.name == "Value First"
    assert template.summary == "Bias toward commercial return."
    assert template.weight_summary == "Strategic x1, Value x5, Urgency x1, Risk x0"
    assert template.is_active is True


def test_portfolio_entities_reject_invalid_local_fields():
    with pytest.raises(ValidationError) as exc_org:
        PortfolioIntakeItem.create(
            organization_id=" ",
            title="Valid",
            sponsor_name="PMO",
        )
    assert exc_org.value.code == "PORTFOLIO_INTAKE_ORGANIZATION_REQUIRED"

    with pytest.raises(ValidationError) as exc_status:
        PortfolioIntakeItem.create(
            organization_id="org-1",
            title="Valid",
            sponsor_name="PMO",
            status="bad-status",
        )
    assert exc_status.value.code == "PORTFOLIO_INTAKE_STATUS_INVALID"

    with pytest.raises(ValidationError) as exc_score:
        PortfolioIntakeItem.create(
            organization_id="org-1",
            title="Valid",
            sponsor_name="PMO",
            strategic_score=6,
        )
    assert exc_score.value.code == "PORTFOLIO_INTAKE_STRATEGIC_SCORE_INVALID"

    with pytest.raises(ValidationError) as exc_budget:
        PortfolioScenario.create(
            organization_id="org-1",
            name="Scenario",
            budget_limit=-1,
        )
    assert exc_budget.value.code == "PORTFOLIO_SCENARIO_BUDGET_INVALID"

    with pytest.raises(ValidationError) as exc_mix:
        PortfolioScoringTemplate.create(
            organization_id="org-1",
            name="Broken",
            strategic_weight=0,
            value_weight=0,
            urgency_weight=0,
            risk_weight=9,
        )
    assert exc_mix.value.code == "PORTFOLIO_TEMPLATE_EMPTY"

    with pytest.raises(ValidationError) as exc_dependency_type:
        PortfolioProjectDependency.create(
            predecessor_project_id="proj-1",
            successor_project_id="proj-2",
            dependency_type="bad",
        )
    assert exc_dependency_type.value.code == "PORTFOLIO_DEPENDENCY_TYPE_INVALID"

    with pytest.raises(ValidationError) as exc_dependency_pair:
        PortfolioProjectDependency.create(
            predecessor_project_id="proj-1",
            successor_project_id="proj-1",
        )
    assert exc_dependency_pair.value.code == "PORTFOLIO_DEPENDENCY_SAME_PROJECT"


def test_portfolio_dependency_entity_normalizes_local_fields():
    dependency = PortfolioProjectDependency.create(
        predecessor_project_id="  proj-1  ",
        successor_project_id="  proj-2  ",
        dependency_type="fs",
        summary="  Alpha must finish before Beta starts.  ",
    )

    assert dependency.predecessor_project_id == "proj-1"
    assert dependency.successor_project_id == "proj-2"
    assert dependency.dependency_type == DependencyType.FINISH_TO_START
    assert dependency.summary == "Alpha must finish before Beta starts."


def test_portfolio_intake_service_update_validates_final_state(monkeypatch: pytest.MonkeyPatch):
    service = _make_service(monkeypatch)

    created = service.create_intake_item(
        title="  ERP Modernization  ",
        sponsor_name="  PMO  ",
        requested_budget=1200.0,
        strategic_score=4,
        value_score=3,
        urgency_score=2,
        risk_score=1,
    )
    risk_template = service.create_scoring_template(
        name="  Risk First  ",
        strategic_weight=1,
        value_weight=1,
        urgency_weight=1,
        risk_weight=4,
        activate=False,
    )

    updated = service.update_intake_item(
        created.id,
        title="  ERP Modernization Phase 2  ",
        sponsor_name="  Strategy Office  ",
        summary="  Expand to regional rollout.  ",
        requested_budget="2500",
        requested_capacity_percent="42",
        strategic_score="5",
        value_score="4",
        urgency_score="3",
        risk_score="2",
        scoring_template_id=risk_template.id,
        status="approved",
    )

    assert updated.title == "ERP Modernization Phase 2"
    assert updated.sponsor_name == "Strategy Office"
    assert updated.summary == "Expand to regional rollout."
    assert updated.requested_budget == pytest.approx(2500.0)
    assert updated.requested_capacity_percent == pytest.approx(42.0)
    assert updated.scoring_template_id == risk_template.id
    assert updated.scoring_template_name == "Risk First"
    assert updated.risk_weight == 4
    assert updated.status == PortfolioIntakeStatus.APPROVED
    assert updated.version == 2

    with pytest.raises(ValidationError) as exc:
        service.update_intake_item(created.id, title=" ")
    assert exc.value.code == "PORTFOLIO_INTAKE_TITLE_REQUIRED"


def test_portfolio_scenario_service_normalizes_ids_and_enforces_scope(
    monkeypatch: pytest.MonkeyPatch,
):
    service = _make_service(monkeypatch, project_ids=["proj-1", "proj-2"])

    intake = service.create_intake_item(
        title="Portfolio Intake",
        sponsor_name="PMO",
    )
    scenario = service.create_scenario(
        name="  Selective Plan  ",
        budget_limit="900",
        capacity_limit_percent="70",
        project_ids=[" proj-2 ", "proj-1", "proj-1"],
        intake_item_ids=[f" {intake.id} ", intake.id],
        notes="  Focus on delivery confidence.  ",
    )

    assert scenario.name == "Selective Plan"
    assert scenario.project_ids == ["proj-1", "proj-2"]
    assert scenario.intake_item_ids == [intake.id]
    assert scenario.notes == "Focus on delivery confidence."

    updated = service.update_scenario(
        scenario.id,
        budget_limit=None,
        capacity_limit_percent="55",
        project_ids=[" proj-2 ", "proj-2"],
        notes="  Rephase into a single wave.  ",
    )

    assert updated.budget_limit is None
    assert updated.capacity_limit_percent == pytest.approx(55.0)
    assert updated.project_ids == ["proj-2"]
    assert updated.notes == "Rephase into a single wave."

    with pytest.raises(ValidationError) as exc:
        service.update_scenario(scenario.id, project_ids=["proj-unknown"])
    assert exc.value.code == "PORTFOLIO_PROJECT_SCOPE_INVALID"


def test_portfolio_dependency_service_keeps_scope_and_duplicate_rules_in_service(
    monkeypatch: pytest.MonkeyPatch,
):
    service = _make_service(monkeypatch, project_ids=["proj-1", "proj-2"])

    created = service.create_project_dependency(
        predecessor_project_id="  proj-1  ",
        successor_project_id="  proj-2  ",
        dependency_type="fs",
        summary="  Alpha gates Beta launch.  ",
    )

    assert created.predecessor_project_id == "proj-1"
    assert created.successor_project_id == "proj-2"
    assert created.dependency_type == DependencyType.FINISH_TO_START
    assert created.summary == "Alpha gates Beta launch."

    with pytest.raises(ValidationError) as exc_duplicate:
        service.create_project_dependency(
            predecessor_project_id="proj-1",
            successor_project_id="proj-2",
            dependency_type="FS",
        )
    assert exc_duplicate.value.code == "PORTFOLIO_DEPENDENCY_DUPLICATE"

    with pytest.raises(ValidationError) as exc_scope:
        service.create_project_dependency(
            predecessor_project_id="proj-1",
            successor_project_id="proj-9",
        )
    assert exc_scope.value.code == "PORTFOLIO_DEPENDENCY_PROJECT_REQUIRED"


def test_portfolio_template_service_keeps_duplicate_check_in_service(
    monkeypatch: pytest.MonkeyPatch,
):
    service = _make_service(monkeypatch)

    created = service.create_scoring_template(
        name="  Value First  ",
        summary="  Push value ahead of urgency.  ",
        strategic_weight=1,
        value_weight=5,
        urgency_weight=1,
        risk_weight=0,
        activate=True,
    )

    assert created.name == "Value First"
    assert created.organization_id == "org-1"
    assert created.is_active is True

    activated = service.activate_scoring_template(created.id)
    assert activated.id == created.id
    assert activated.is_active is True

    with pytest.raises(ValidationError) as exc_duplicate:
        service.create_scoring_template(name="value first")
    assert exc_duplicate.value.code == "PORTFOLIO_TEMPLATE_DUPLICATE"

    with pytest.raises(ValidationError) as exc_mix:
        service.create_scoring_template(
            name="Zero Delivery Mix",
            strategic_weight=0,
            value_weight=0,
            urgency_weight=0,
            risk_weight=4,
        )
    assert exc_mix.value.code == "PORTFOLIO_TEMPLATE_EMPTY"

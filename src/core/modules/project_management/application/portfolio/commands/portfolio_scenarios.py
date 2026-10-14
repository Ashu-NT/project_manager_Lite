from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from typing import Any, cast

from src.core.modules.project_management.application.common.module_guard import (
    ProjectManagementModuleGuardMixin,
)
from src.core.modules.project_management.application.portfolio.portfolio_events import (
    PortfolioScenarioChanged,
    PortfolioScenarioChangeType,
)
from src.core.modules.project_management.application.portfolio.utils.portfolio_policy import (
    PortfolioPolicy,
    new_portfolio_context,
    utc_now,
)
from src.core.modules.project_management.contracts.repositories.portfolio.portfolio import (
    PortfolioScenarioRepository,
)
from src.core.modules.project_management.contracts.uow.portfolio.portfolio_unit_of_work import (
    PortfolioUnitOfWorkFactory,
)
from src.core.modules.project_management.domain.portfolio import PortfolioScenario
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)
from src.core.platform.common.exceptions import NotFoundError
from src.core.shared.activity import record_activity
from src.core.shared.audit import record_audit_entry

_SCENARIO_UNSET = object()


class PortfolioScenarioCommandHandler(ProjectManagementModuleGuardMixin):
    """Governed scenario writes (create/update) with project/intake scope validation."""

    def __init__(
        self,
        *,
        scenario_repo: PortfolioScenarioRepository,
        policy: PortfolioPolicy,
        uow_factory: PortfolioUnitOfWorkFactory,
        user_session=None,
        module_catalog_service=None,
    ) -> None:
        self._scenario_repo = scenario_repo
        self._policy = policy
        self._uow_factory = uow_factory
        self._user_session = user_session
        self._module_catalog_service = module_catalog_service

    def create_scenario(
        self,
        *,
        name: str,
        budget_limit: Decimal | int | str | None = None,
        capacity_limit_percent: float | None = None,
        project_ids: list[str] | None = None,
        intake_item_ids: list[str] | None = None,
        notes: str = "",
    ) -> PortfolioScenario:
        require_permission(self._user_session, "portfolio.manage", operation_label="create portfolio scenario")
        organization_id = self._policy.organization_id(operation_label="create portfolio scenario")
        scope = self._policy.scope(operation_label="create portfolio scenario")
        scenario = PortfolioScenario.create(
            organization_id=organization_id,
            name=name,
            budget_limit=budget_limit,
            capacity_limit_percent=capacity_limit_percent,
            project_ids=project_ids or [],
            intake_item_ids=intake_item_ids or [],
            notes=notes,
        )
        scenario = replace(
            scenario,
            project_ids=self._policy.validate_project_ids(scenario.project_ids),
            intake_item_ids=self._policy.validate_intake_ids(scenario.intake_item_ids),
        )
        with self._uow_factory.create(context=new_portfolio_context()) as uow:
            uow.scenarios.add(scenario)
            record_audit_entry(
                uow,
                operation="create",
                entity_type="portfolio_scenario",
                entity_id=scenario.id,
                module="project_management",
                organization_id=scope.organization_id,
                category="MASTER_DATA",
                severity="low",
                after_data={"name": scenario.name},
                metadata={"action": "portfolio.scenario.create"},
                commit=False,
                fail_closed=True,
            )
            record_activity(
                uow,
                action="portfolio.scenario.create",
                entity_type="portfolio_scenario",
                entity_id=scenario.id,
                module="project_management",
                organization_id=scope.organization_id,
                details={"name": scenario.name},
                commit=False,
            )
            uow.record_event(
                PortfolioScenarioChanged(
                    tenant_id=scope.tenant_id,
                    organization_id=scope.organization_id,
                    scenario_id=scenario.id,
                    change_type=PortfolioScenarioChangeType.CREATED,
                    occurred_at=utc_now(),
                )
            )
            uow.commit()
        return scenario

    def update_scenario(
        self,
        scenario_id: str,
        *,
        name: str | None = None,
        budget_limit: Decimal | int | str | None | object = _SCENARIO_UNSET,
        capacity_limit_percent: float | str | None | object = _SCENARIO_UNSET,
        project_ids: list[str] | None = None,
        intake_item_ids: list[str] | None = None,
        notes: str | None = None,
    ) -> PortfolioScenario:
        require_permission(self._user_session, "portfolio.manage", operation_label="update portfolio scenario")
        self._policy.organization_id(operation_label="update portfolio scenario")
        scope = self._policy.scope(operation_label="update portfolio scenario")
        scenario = self._scenario_repo.get(scenario_id)
        if scenario is None:
            raise NotFoundError("Portfolio scenario not found.", code="PORTFOLIO_SCENARIO_NOT_FOUND")
        candidate = replace(
            scenario,
            name=scenario.name if name is None else name,
            budget_limit=(
                scenario.budget_limit
                if budget_limit is _SCENARIO_UNSET
                else cast(Any, budget_limit)
            ),
            capacity_limit_percent=(
                scenario.capacity_limit_percent
                if capacity_limit_percent is _SCENARIO_UNSET
                else cast(Any, capacity_limit_percent)
            ),
            project_ids=(
                scenario.project_ids
                if project_ids is None
                else project_ids
            ),
            intake_item_ids=(
                scenario.intake_item_ids
                if intake_item_ids is None
                else intake_item_ids
            ),
            notes=scenario.notes if notes is None else notes,
            updated_at=utc_now(),
        )
        if project_ids is not None:
            candidate = replace(
                candidate,
                project_ids=self._policy.validate_project_ids(candidate.project_ids),
            )
        if intake_item_ids is not None:
            candidate = replace(
                candidate,
                intake_item_ids=self._policy.validate_intake_ids(candidate.intake_item_ids),
            )
        with self._uow_factory.create(context=new_portfolio_context()) as uow:
            uow.scenarios.update(candidate)
            record_audit_entry(
                uow,
                operation="update",
                entity_type="portfolio_scenario",
                entity_id=candidate.id,
                module="project_management",
                organization_id=scope.organization_id,
                category="MASTER_DATA",
                severity="low",
                metadata={"action": "portfolio.scenario.update"},
                commit=False,
                fail_closed=True,
            )
            record_activity(
                uow,
                action="portfolio.scenario.update",
                entity_type="portfolio_scenario",
                entity_id=candidate.id,
                module="project_management",
                organization_id=scope.organization_id,
                details={"name": candidate.name},
                commit=False,
            )
            uow.record_event(
                PortfolioScenarioChanged(
                    tenant_id=scope.tenant_id,
                    organization_id=scope.organization_id,
                    scenario_id=candidate.id,
                    change_type=PortfolioScenarioChangeType.UPDATED,
                    occurred_at=utc_now(),
                )
            )
            uow.commit()
        return candidate


__all__ = ["PortfolioScenarioCommandHandler"]

from __future__ import annotations

from dataclasses import replace
from datetime import date
from typing import Any, cast

from sqlalchemy.exc import IntegrityError

from src.core.modules.project_management.application.common.module_guard import (
    ProjectManagementModuleGuardMixin,
)
from src.core.modules.project_management.application.portfolio._command_values import (
    PORTFOLIO_UNSET as _INTAKE_UNSET,
)
from src.core.modules.project_management.application.portfolio.dto.commands.intake import (
    PortfolioIntakeCreateCommand,
    PortfolioIntakeUpdateCommand,
)
from src.core.modules.project_management.application.portfolio.portfolio_events import (
    PortfolioIntakeItemChanged,
    PortfolioIntakeItemChangeType,
)
from src.core.modules.project_management.application.portfolio.utils.portfolio_policy import (
    PortfolioPolicy,
    new_portfolio_context,
    utc_now,
)
from src.core.modules.project_management.contracts.repositories.portfolio.portfolio import (
    PortfolioIntakeRepository,
)
from src.core.modules.project_management.contracts.uow.portfolio.portfolio_unit_of_work import (
    PortfolioUnitOfWorkFactory,
)
from src.core.modules.project_management.domain.portfolio import (
    PortfolioIntakeItem,
    PortfolioIntakeStatus,
)
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)
from src.core.platform.common.exceptions import ConcurrencyError, NotFoundError
from src.core.shared.activity import record_activity
from src.core.shared.audit import record_audit_entry


class PortfolioIntakeCommandHandler(ProjectManagementModuleGuardMixin):
    """Governed intake writes (create/update); one UoW per operation."""

    def __init__(
        self,
        *,
        intake_repo: PortfolioIntakeRepository,
        policy: PortfolioPolicy,
        uow_factory: PortfolioUnitOfWorkFactory,
        user_session=None,
        module_catalog_service=None,
    ) -> None:
        self._intake_repo = intake_repo
        self._policy = policy
        self._uow_factory = uow_factory
        self._user_session = user_session
        self._module_catalog_service = module_catalog_service

    def create_intake_item(self, command: PortfolioIntakeCreateCommand) -> PortfolioIntakeItem:
        title = command.title
        sponsor_name = command.sponsor_name
        summary = command.summary
        requested_budget = command.requested_budget
        requested_capacity_percent = command.requested_capacity_percent
        target_start_date = command.target_start_date
        strategic_score = command.strategic_score
        value_score = command.value_score
        urgency_score = command.urgency_score
        risk_score = command.risk_score
        scoring_template_id = command.scoring_template_id
        status = command.status if isinstance(command.status, PortfolioIntakeStatus) else PortfolioIntakeStatus(str(command.status or PortfolioIntakeStatus.PROPOSED.value).strip().upper())
        require_permission(self._user_session, "portfolio.manage", operation_label="create portfolio intake")
        organization_id = self._policy.organization_id(operation_label="create portfolio intake")
        scope = self._policy.scope(operation_label="create portfolio intake")
        try:
            with self._uow_factory.create(context=new_portfolio_context()) as uow:
                events: list = []
                scoring_template = self._policy.resolve_scoring_template(
                    scoring_template_id, uow=uow, events=events
                )
                item = PortfolioIntakeItem.create(
                    organization_id=organization_id,
                    title=title,
                    sponsor_name=sponsor_name,
                    summary=summary,
                    requested_budget=requested_budget,
                    requested_capacity_percent=requested_capacity_percent,
                    target_start_date=target_start_date,
                    strategic_score=strategic_score,
                    value_score=value_score,
                    urgency_score=urgency_score,
                    risk_score=risk_score,
                    scoring_template_id=scoring_template.id,
                    scoring_template_name=scoring_template.name,
                    strategic_weight=scoring_template.strategic_weight,
                    value_weight=scoring_template.value_weight,
                    urgency_weight=scoring_template.urgency_weight,
                    risk_weight=scoring_template.risk_weight,
                    status=status,
                )
                uow.intake.add(item)
                record_audit_entry(
                    uow,
                    operation="create",
                    entity_type="portfolio_intake_item",
                    entity_id=item.id,
                    module="project_management",
                    organization_id=scope.organization_id,
                    category="MASTER_DATA",
                    severity="low",
                    after_data={"title": item.title},
                    metadata={"action": "portfolio.intake.create"},
                    commit=False,
                    fail_closed=True,
                )
                record_activity(
                    uow,
                    action="portfolio.intake.create",
                    entity_type="portfolio_intake_item",
                    entity_id=item.id,
                    module="project_management",
                    organization_id=scope.organization_id,
                    details={"title": item.title},
                    commit=False,
                )
                events.append(
                    PortfolioIntakeItemChanged(
                        tenant_id=scope.tenant_id,
                        organization_id=scope.organization_id,
                        intake_item_id=item.id,
                        change_type=PortfolioIntakeItemChangeType.CREATED,
                        occurred_at=utc_now(),
                    )
                )
                for event in events:
                    uow.record_event(event)
                uow.commit()
        except IntegrityError as exc:
            raise ConcurrencyError(
                "The active scoring template changed concurrently. Please retry.",
                code="PORTFOLIO_TEMPLATE_ACTIVATION_CONFLICT",
            ) from exc
        return item

    def update_intake_item(self, command: PortfolioIntakeUpdateCommand) -> PortfolioIntakeItem:
        item_id = command.item_id
        title = command.title
        sponsor_name = command.sponsor_name
        summary = command.summary
        requested_budget = command.requested_budget
        requested_capacity_percent = command.requested_capacity_percent
        target_start_date = command.target_start_date
        strategic_score = command.strategic_score
        value_score = command.value_score
        urgency_score = command.urgency_score
        risk_score = command.risk_score
        status = command.status
        scoring_template_id = command.scoring_template_id
        require_permission(self._user_session, "portfolio.manage", operation_label="update portfolio intake")
        self._policy.organization_id(operation_label="update portfolio intake")
        scope = self._policy.scope(operation_label="update portfolio intake")
        item = self._intake_repo.get(item_id)
        if item is None:
            raise NotFoundError("Portfolio intake item not found.", code="PORTFOLIO_INTAKE_NOT_FOUND")
        candidate = replace(
            item,
            title=item.title if title is None else title,
            sponsor_name=item.sponsor_name if sponsor_name is None else sponsor_name,
            summary=item.summary if summary is None else summary,
            requested_budget=(
                item.requested_budget
                if requested_budget is None
                else cast(Any, requested_budget)
            ),
            requested_capacity_percent=(
                item.requested_capacity_percent
                if requested_capacity_percent is None
                else cast(Any, requested_capacity_percent)
            ),
            target_start_date=(
                item.target_start_date
                if target_start_date is _INTAKE_UNSET
                else cast(date | None, target_start_date)
            ),
            strategic_score=(
                item.strategic_score
                if strategic_score is None
                else cast(Any, strategic_score)
            ),
            value_score=(
                item.value_score
                if value_score is None
                else cast(Any, value_score)
            ),
            urgency_score=(
                item.urgency_score
                if urgency_score is None
                else cast(Any, urgency_score)
            ),
            risk_score=(
                item.risk_score
                if risk_score is None
                else cast(Any, risk_score)
            ),
            status=item.status if status is None else cast(Any, status),
            updated_at=utc_now(),
        )
        with self._uow_factory.create(context=new_portfolio_context()) as uow:
            events: list = []
            if scoring_template_id is not None:
                scoring_template = uow.scoring_templates.get(scoring_template_id)
                if scoring_template is None:
                    raise NotFoundError(
                        "Portfolio scoring template not found.",
                        code="PORTFOLIO_TEMPLATE_NOT_FOUND",
                    )
                candidate = self._policy.apply_scoring_template(candidate, scoring_template)
            uow.intake.update(candidate)
            record_activity(
                uow,
                action="portfolio.intake.update",
                entity_type="portfolio_intake_item",
                entity_id=candidate.id,
                module="project_management",
                organization_id=scope.organization_id,
                details={"title": candidate.title},
                commit=False,
            )
            events.append(
                PortfolioIntakeItemChanged(
                    tenant_id=scope.tenant_id,
                    organization_id=scope.organization_id,
                    intake_item_id=candidate.id,
                    change_type=PortfolioIntakeItemChangeType.UPDATED,
                    occurred_at=utc_now(),
                )
            )
            for event in events:
                uow.record_event(event)
            uow.commit()
        return candidate


__all__ = ["PortfolioIntakeCommandHandler"]

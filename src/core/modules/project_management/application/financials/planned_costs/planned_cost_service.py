from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.core.modules.project_management.access.scope_permissions import require_project_permission
from src.core.modules.project_management.application.common.clock import Clock
from src.core.modules.project_management.application.common.module_guard import (
    ProjectManagementModuleGuardMixin,
)
from src.core.modules.project_management.contracts.repositories.finance.configuration.financial_configuration import (
    ProjectCostCodeRepository,
    ProjectFinancialProfileRepository,
)
from src.core.modules.project_management.contracts.repositories.finance.planned_costs.planned_cost import (
    ProjectPlannedCostVersionRepository,
)
from src.core.modules.project_management.contracts.repositories.projects.project import (
    ProjectRepository,
    ProjectResourceRepository,
)
from src.core.modules.project_management.contracts.repositories.finance.rate_cards.rate_resolution import (
    LaborRateResolver,
)
from src.core.modules.project_management.contracts.repositories.tasks.task import (
    AssignmentRepository,
    TaskRepository,
)
from src.core.modules.project_management.domain.financials.planned_cost import (
    PLANNED_HOURS_FULLY_ALLOCATED,
    PLANNED_HOURS_OVERALLOCATED,
    PLANNED_HOURS_PARTIALLY_ALLOCATED,
    PROJECT_RESOURCE_ENVELOPE_MISSING,
    ProjectPlannedCostLine,
    ProjectPlannedCostVersion,
    ResourceAllocationDiagnostic,
)
from src.core.modules.project_management.domain.financials.rate_cards import RateType
from src.core.modules.project_management.application.financials.planned_costs.planned_cost_events import (
    PlannedCostSnapshotCalculated,
)
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)
from src.core.platform.application.tenant.tenancy.tenant_context import (
    TenantContext,
    TenantContextService,
)
from src.core.platform.common.exceptions import (
    BusinessRuleError,
    ConcurrencyError,
    NotFoundError,
)
from src.core.shared.audit import record_audit_entry

_REVISION_CONSTRAINT = "uq_pf_planned_cost_versions_project_revision"


@dataclass(frozen=True, slots=True)
class PlannedCostCalculationResult:
    """Return value of ``calculate_snapshot`` — the persisted version plus
    the transient, computed-at-calculation-time allocation diagnostics
    (not persisted; see ``ResourceAllocationDiagnostic``)."""

    version: ProjectPlannedCostVersion
    diagnostics: tuple[ResourceAllocationDiagnostic, ...]


class PlannedCostService(ProjectManagementModuleGuardMixin):
    def __init__(
        self,
        *,
        session: Session,
        planned_cost_repo: ProjectPlannedCostVersionRepository,
        project_repo: ProjectRepository,
        financial_profile_repo: ProjectFinancialProfileRepository,
        cost_code_repo: ProjectCostCodeRepository,
        task_repo: TaskRepository,
        assignment_repo: AssignmentRepository,
        project_resource_repo: ProjectResourceRepository,
        rate_resolver: LaborRateResolver,
        clock: Clock,
        user_session=None,
        enterprise_audit_service=None,
        module_catalog_service=None,
        tenant_context_service: TenantContextService | None = None,
        record_event: Callable[[object], None] | None = None,
    ) -> None:
        self._session = session
        self._planned_cost_repo = planned_cost_repo
        self._project_repo = project_repo
        self._financial_profile_repo = financial_profile_repo
        self._cost_code_repo = cost_code_repo
        self._task_repo = task_repo
        self._assignment_repo = assignment_repo
        self._project_resource_repo = project_resource_repo
        self._rate_resolver = rate_resolver
        self._clock = clock
        self._user_session = user_session
        self._enterprise_audit_service = enterprise_audit_service
        self._module_catalog_service = module_catalog_service
        self._tenant_context_service = tenant_context_service
        self._record_event = record_event

    def _emit_snapshot_event(
        self, version: ProjectPlannedCostVersion, *, occurred_at: datetime
    ) -> None:
        if self._record_event is None:
            return
        self._record_event(
            PlannedCostSnapshotCalculated(
                tenant_id=version.tenant_id,
                organization_id=version.organization_id,
                project_id=version.project_id,
                planned_cost_version_id=version.id,
                occurred_at=occurred_at,
            )
        )

    # -- Reads ----------------------------------------------------------

    def get_current_snapshot(self, project_id: str) -> ProjectPlannedCostVersion | None:
        require_permission(self._user_session, "finance.read", operation_label="view planned-cost snapshot")
        require_project_permission(
            self._user_session, project_id, "finance.read", operation_label="view planned-cost snapshot"
        )
        return self._planned_cost_repo.get_current_for_project(project_id)

    def list_versions(self, project_id: str) -> list[ProjectPlannedCostVersion]:
        require_permission(
            self._user_session, "finance.read", operation_label="list planned-cost snapshots"
        )
        require_project_permission(
            self._user_session, project_id, "finance.read", operation_label="list planned-cost snapshots"
        )
        return self._planned_cost_repo.list_for_project(project_id)

    def get_version(self, version_id: str) -> ProjectPlannedCostVersion:
        require_permission(self._user_session, "finance.read", operation_label="view planned-cost snapshot")
        version = self._require_version(version_id)
        require_project_permission(
            self._user_session, version.project_id, "finance.read", operation_label="view planned-cost snapshot"
        )
        return version

    def list_lines(self, version_id: str) -> list[ProjectPlannedCostLine]:
        require_permission(
            self._user_session, "finance.read", operation_label="list planned-cost lines"
        )
        version = self._require_version(version_id)
        require_project_permission(
            self._user_session, version.project_id, "finance.read", operation_label="list planned-cost lines"
        )
        return self._planned_cost_repo.list_lines(version_id)

    def get_totals_by_cost_code(self, version_id: str) -> dict[str, Decimal]:
        totals: dict[str, Decimal] = {}
        for line in self.list_lines(version_id):
            totals[line.cost_code_id] = totals.get(line.cost_code_id, Decimal("0")) + line.amount
        return totals

    def get_totals_by_task(self, version_id: str) -> dict[str, Decimal]:
        totals: dict[str, Decimal] = {}
        for line in self.list_lines(version_id):
            totals[line.task_id] = totals.get(line.task_id, Decimal("0")) + line.amount
        return totals

    # -- Calculation ------------------------------------------------------

    def calculate_snapshot(
        self, project_id: str, *, calculated_by: str, as_of: date | None = None
    ) -> PlannedCostCalculationResult:
        require_permission(
            self._user_session, "plannedcost.manage", operation_label="calculate planned-cost snapshot"
        )
        require_project_permission(
            self._user_session, project_id, "plannedcost.manage",
            operation_label="calculate planned-cost snapshot",
        )
        context = self._require_context("calculate planned-cost snapshot")
        if self._project_repo.get(project_id) is None:
            raise NotFoundError("Project not found.", code="PROJECT_NOT_FOUND")

        profile = self._financial_profile_repo.get_by_project(project_id)
        if profile is None:
            raise NotFoundError(
                "Project financial profile not found; configure the project's "
                "finance settings before calculating planned cost.",
                code="PLANNED_COST_PROFILE_NOT_FOUND",
            )
        if not profile.default_cost_code_id:
            raise BusinessRuleError(
                "Project has no default cost code configured; planned-cost "
                "lines need a cost-code dimension to calculate. (Tactical "
                "limitation: every line in this slice uses this one project-"
                "wide default — see the plan doc's cost-code section.)",
                code="PLANNED_COST_NO_DEFAULT_COST_CODE",
            )
        resolved_as_of = as_of or self._clock.today()
        cost_code = self._cost_code_repo.get(profile.default_cost_code_id)
        if cost_code is None or not cost_code.is_effective_on(resolved_as_of):
            raise BusinessRuleError(
                "Project's default cost code is inactive or not effective for this date.",
                code="PLANNED_COST_DEFAULT_COST_CODE_INACTIVE",
            )

        task_ids = [t.id for t in self._task_repo.list_by_project(project_id)]
        assignments = self._assignment_repo.list_by_tasks(task_ids) if task_ids else []
        assignments_by_resource: dict[str, list] = {}
        for assignment in assignments:
            assignments_by_resource.setdefault(assignment.resource_id, []).append(assignment)

        envelopes = [
            pr
            for pr in self._project_resource_repo.list_by_project(project_id)
            if Decimal(str(pr.planned_hours)) > 0
        ]
        envelope_by_resource = {pr.resource_id: pr for pr in envelopes}

        diagnostics: list[ResourceAllocationDiagnostic] = []
        eligible: list[tuple] = []
        partially_allocated_count = 0

        for resource_id, envelope in envelope_by_resource.items():
            own = assignments_by_resource.get(resource_id, [])
            allocated_total = sum((a.allocated_planned_hours for a in own), Decimal("0"))
            envelope_hours = Decimal(str(envelope.planned_hours))
            if allocated_total > envelope_hours:
                reason = PLANNED_HOURS_OVERALLOCATED
                unallocated = Decimal("0")
            elif allocated_total == envelope_hours:
                reason = PLANNED_HOURS_FULLY_ALLOCATED
                unallocated = Decimal("0")
            else:
                reason = PLANNED_HOURS_PARTIALLY_ALLOCATED
                unallocated = envelope_hours - allocated_total
                partially_allocated_count += 1
            diagnostics.append(
                ResourceAllocationDiagnostic(
                    project_resource_id=envelope.id,
                    resource_id=resource_id,
                    envelope_hours=envelope_hours,
                    allocated_hours=allocated_total,
                    unallocated_hours=unallocated,
                    reason_code=reason,
                )
            )
            for assignment in own:
                if assignment.allocated_planned_hours > 0:
                    eligible.append((assignment, envelope))

        for resource_id, own in assignments_by_resource.items():
            if resource_id in envelope_by_resource:
                continue
            allocated_total = sum((a.allocated_planned_hours for a in own), Decimal("0"))
            if allocated_total <= 0:
                continue
            # Allocated hours exist but no ProjectResource envelope covers
            # this resource on this project — no line is produced (there is
            # no project_resource_id to attach), only a diagnostic.
            diagnostics.append(
                ResourceAllocationDiagnostic(
                    project_resource_id="",
                    resource_id=resource_id,
                    envelope_hours=Decimal("0"),
                    allocated_hours=allocated_total,
                    unallocated_hours=Decimal("0"),
                    reason_code=PROJECT_RESOURCE_ENVELOPE_MISSING,
                )
            )

        resource_ids = tuple(sorted({assignment.resource_id for assignment, _ in eligible}))
        batch = None
        if resource_ids:
            batch = self._rate_resolver.resolve_many(
                tenant_id=context.tenant_id,
                organization_id=context.organization_id,
                project_id=project_id,
                resource_ids=resource_ids,
                rate_type=RateType.COST,
                as_of=resolved_as_of,
                unit="HOUR",
            )

        now = self._clock.now()
        previous = self._planned_cost_repo.get_current_for_project(project_id)
        revision = (previous.revision + 1) if previous is not None else 1
        version = ProjectPlannedCostVersion.create(
            tenant_id=context.tenant_id,
            organization_id=context.organization_id,
            project_id=project_id,
            revision=revision,
            currency_code=profile.currency_code,
            as_of=resolved_as_of,
            calculated_by=calculated_by,
            calculated_at=now,
        )

        lines: list[ProjectPlannedCostLine] = []
        unresolved_rate_count = 0
        for assignment, envelope in eligible:
            snapshot = batch.snapshot_for(assignment.resource_id) if batch is not None else None
            if snapshot is None:
                unresolved_rate_count += 1
                continue
            rate_amount = snapshot.monetary_rate.money.amount
            rate_currency = snapshot.monetary_rate.money.currency.code
            if rate_currency != profile.currency_code:
                # No cross-currency conversion infrastructure exists yet
                # system-wide (the audit doc defers ExchangeRate/FX until
                # Phase C) — a resolved rate in a different currency than
                # the snapshot's single reporting currency is excluded, not
                # silently mixed or force-relabeled.
                unresolved_rate_count += 1
                continue
            planned_hours = Decimal(assignment.allocated_planned_hours)
            amount = planned_hours * rate_amount
            lines.append(
                ProjectPlannedCostLine.create(
                    tenant_id=context.tenant_id,
                    organization_id=context.organization_id,
                    version_id=version.id,
                    project_id=project_id,
                    task_id=assignment.task_id,
                    resource_id=assignment.resource_id,
                    project_resource_id=envelope.id,
                    cost_code_id=profile.default_cost_code_id,
                    source_assignment_id=assignment.id,
                    planned_hours=planned_hours,
                    rate_amount=rate_amount,
                    amount=amount,
                    currency_code=rate_currency,
                    rate_card_id=snapshot.rate_card_id,
                    rate_line_id=snapshot.rate_line_id,
                    rate_card_version=snapshot.rate_card_version,
                    created_at=now,
                )
            )

        version.rates_complete = unresolved_rate_count == 0
        version.allocations_complete = not any(
            diagnostic.reason_code in (PLANNED_HOURS_OVERALLOCATED, PROJECT_RESOURCE_ENVELOPE_MISSING)
            or diagnostic.reason_code == PLANNED_HOURS_PARTIALLY_ALLOCATED
            for diagnostic in diagnostics
        )
        # Always True this slice: the initial default-cost-code gate above
        # makes per-line cost-code resolution all-or-nothing today. Kept as
        # a real, settable field for a future per-task cost-code source.
        version.cost_codes_complete = True
        version.unresolved_rate_count = unresolved_rate_count
        version.partially_allocated_resource_count = partially_allocated_count
        version.unclassified_line_count = 0

        try:
            with self._session.begin_nested():
                if previous is not None:
                    previous_expected_version = previous.row_version
                    previous.supersede(superseded_by=calculated_by, superseded_at=now)
                    self._planned_cost_repo.update(
                        previous, expected_row_version=previous_expected_version
                    )
                    self._planned_cost_repo.flush()
                self._planned_cost_repo.add(version)
                self._planned_cost_repo.flush()
                if lines:
                    self._planned_cost_repo.add_lines(lines)
                    self._planned_cost_repo.flush()
        except IntegrityError as exc:
            message = self._integrity_message(exc)
            if _REVISION_CONSTRAINT in message or "revision" in message:
                raise ConcurrencyError(
                    "Another planned-cost snapshot was calculated for this "
                    "project concurrently. Refresh and try again.",
                    code="PLANNED_COST_REVISION_CONFLICT",
                ) from exc
            raise

        self._record_version_audit(operation="calculate", version=version, diagnostics=diagnostics)
        self._session.flush()
        self._emit_snapshot_event(version, occurred_at=now)
        return PlannedCostCalculationResult(version=version, diagnostics=tuple(diagnostics))

    # -- Shared helpers ---------------------------------------------------

    def _require_version(self, version_id: str) -> ProjectPlannedCostVersion:
        version = self._planned_cost_repo.get(version_id)
        if version is None:
            raise NotFoundError(
                "Planned-cost version not found.", code="PLANNED_COST_VERSION_NOT_FOUND"
            )
        return version

    def _require_context(self, operation_label: str) -> TenantContext:
        if self._tenant_context_service is None:
            raise BusinessRuleError(
                f"Active organization context is required to {operation_label}.",
                code="TENANT_CONTEXT_REQUIRED",
            )
        return self._tenant_context_service.require_organization_context(
            operation_label=operation_label
        )

    @staticmethod
    def _integrity_message(exc: IntegrityError) -> str:
        orig_message = str(getattr(exc, "orig", "") or "")
        return (orig_message or str(exc)).lower()

    def _record_version_audit(
        self,
        *,
        operation: str,
        version: ProjectPlannedCostVersion,
        diagnostics: list[ResourceAllocationDiagnostic],
    ) -> None:
        record_audit_entry(
            self,
            operation=f"project_planned_cost_version.{operation}",
            entity_type="project_planned_cost_version",
            entity_id=version.id,
            entity_parent_id=version.project_id,
            module="project_management",
            old_value=None,
            new_value=json.dumps(
                {
                    "revision": version.revision,
                    "status": version.status.value,
                    "currency_code": version.currency_code,
                    "as_of": version.as_of.isoformat(),
                    "rates_complete": version.rates_complete,
                    "allocations_complete": version.allocations_complete,
                    "cost_codes_complete": version.cost_codes_complete,
                    "unresolved_rate_count": version.unresolved_rate_count,
                    "partially_allocated_resource_count": version.partially_allocated_resource_count,
                    "unclassified_line_count": version.unclassified_line_count,
                    "diagnostic_reason_codes": [d.reason_code for d in diagnostics],
                },
                sort_keys=True,
            ),
            workspace_id=version.project_id,
            source="application",
            severity="high",
            compliance_tag="financial",
            metadata={"action": operation},
            commit=False,
            fail_closed=True,
        )


__all__ = ["PlannedCostCalculationResult", "PlannedCostService"]

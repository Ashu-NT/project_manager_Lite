from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.core.modules.project_management.access.scope_permissions import require_project_permission
from src.core.modules.project_management.application.common.clock import Clock
from src.core.modules.project_management.application.common.module_guard import (
    ProjectManagementModuleGuardMixin,
)
from src.core.modules.project_management.contracts.financial_sources.procurement import (
    ProcurementCommitmentFinancialSource,
)
from src.core.modules.project_management.contracts.financial_sources.reference import (
    FinancialPostingPurpose,
    FinancialSourceModule,
    FinancialSourceType,
)
from src.core.modules.project_management.contracts.repositories.finance.commitments.commitment import (
    ProjectCommitmentRepository,
)
from src.core.modules.project_management.contracts.repositories.finance.cost_entries.cost_entry import (
    ProjectCostEntryRepository,
)
from src.core.modules.project_management.contracts.repositories.finance.configuration.financial_configuration import (
    ProjectCostCodeRepository,
    ProjectFinancialProfileRepository,
)
from src.core.modules.project_management.contracts.repositories.projects.project import ProjectRepository
from src.core.modules.project_management.contracts.repositories.tasks.task import TaskRepository
from src.core.modules.project_management.domain.financials.commitment import (
    ProjectCommitment,
    ProjectCommitmentLine,
    ProjectCommitmentLineState,
    ProjectCommitmentMatch,
    ProjectCommitmentMatchKind,
    ProjectCommitmentSourceRevision,
)
from src.core.modules.project_management.domain.financials.configuration import (
    CostCodePolicy,
    FinancialProfileStatus,
)
from src.core.modules.project_management.domain.financials.cost_entry import (
    ProjectCostEntryKind,
    ProjectCostEntryStatus,
)
from src.core.modules.project_management.domain.identifiers import generate_id
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)
from src.core.platform.application.tenant.tenancy.tenant_context import TenantContextService
from src.core.platform.common.exceptions import BusinessRuleError, NotFoundError, ValidationError
from src.core.platform.contract.master_data.party.contracts import PartyRepository
from src.core.platform.contract.master_data.site.contracts import SiteRepository
from src.core.platform.finance import (
    EXCHANGE_RATE_STORAGE,
    DecimalQuantity,
    MonetaryRate,
    Money,
    MoneyPayload,
)
from src.core.platform.integration.canonical_json import canonical_json_sha256
from src.core.shared.audit import record_audit_entry
from src.core.shared.events.domain_events import domain_events


_SOURCE_STATE_MAP = {
    "SENT": ProjectCommitmentLineState.SENT,
    "PARTIALLY_RECEIVED": ProjectCommitmentLineState.PARTIALLY_RECEIVED,
    "FULLY_RECEIVED": ProjectCommitmentLineState.FULLY_RECEIVED,
    "CLOSED": ProjectCommitmentLineState.CLOSED,
    "CANCELLED": ProjectCommitmentLineState.CANCELLED,
}


class ProjectCommitmentService(ProjectManagementModuleGuardMixin):
    """Consumes typed Procurement facts into the PM commitment projection."""

    def __init__(
        self,
        *,
        session: Session,
        commitment_repo: ProjectCommitmentRepository,
        cost_entry_repo: ProjectCostEntryRepository,
        project_repo: ProjectRepository,
        financial_profile_repo: ProjectFinancialProfileRepository,
        cost_code_repo: ProjectCostCodeRepository,
        task_repo: TaskRepository,
        party_repo: PartyRepository,
        site_repo: SiteRepository,
        clock: Clock,
        user_session=None,
        enterprise_audit_service=None,
        module_catalog_service=None,
        tenant_context_service: TenantContextService | None = None,
    ) -> None:
        self._session = session
        self._commitment_repo = commitment_repo
        self._cost_entry_repo = cost_entry_repo
        self._project_repo = project_repo
        self._financial_profile_repo = financial_profile_repo
        self._cost_code_repo = cost_code_repo
        self._task_repo = task_repo
        self._party_repo = party_repo
        self._site_repo = site_repo
        self._clock = clock
        self._user_session = user_session
        self._enterprise_audit_service = enterprise_audit_service
        self._module_catalog_service = module_catalog_service
        self._tenant_context_service = tenant_context_service

    def get_line(self, line_id: str) -> ProjectCommitmentLine:
        require_permission(self._user_session, "finance.read", operation_label="view commitment")
        line = self._require_line(line_id)
        require_project_permission(
            self._user_session, line.project_id, "finance.read", operation_label="view commitment"
        )
        return line

    def list_for_project(
        self, project_id: str, *, offset: int = 0, limit: int = 50
    ) -> tuple[list[ProjectCommitmentLine], int]:
        require_permission(self._user_session, "finance.read", operation_label="list commitments")
        require_project_permission(
            self._user_session, project_id, "finance.read", operation_label="list commitments"
        )
        return self._commitment_repo.list_lines_for_project(
            project_id, offset=offset, limit=limit
        )

    def ingest_procurement_source(
        self,
        source: ProcurementCommitmentFinancialSource,
        *,
        cost_code_id: str,
        exchange_rate: Decimal | None = None,
        exchange_rate_date: date | None = None,
        exchange_rate_source: str | None = None,
        exchange_rate_captured_at: datetime | None = None,
    ) -> ProjectCommitmentLine:
        """Apply one ordered PO-line revision; delivery transport is owned by Phase C.5."""

        return self._ingest_procurement_source(
            source,
            cost_code_id=cost_code_id,
            exchange_rate=exchange_rate,
            exchange_rate_date=exchange_rate_date,
            exchange_rate_source=exchange_rate_source,
            exchange_rate_captured_at=exchange_rate_captured_at,
            actor_id=self._actor_id(),
            authorize=True,
            commit=True,
        )

    def apply_procurement_source(
        self,
        source: ProcurementCommitmentFinancialSource,
        *,
        exchange_rate: Decimal | None = None,
        exchange_rate_date: date | None = None,
        exchange_rate_source: str | None = None,
        exchange_rate_captured_at: datetime | None = None,
    ) -> ProjectCommitmentLine:
        """Apply one trusted inbox delivery without committing its transaction."""
        profile = self._financial_profile_repo.get_by_project(source.reference.project_id)
        if profile is None or profile.status != FinancialProfileStatus.ACTIVE:
            raise BusinessRuleError(
                "An active project financial profile is required for commitments.",
                code="PROJECT_FINANCIAL_PROFILE_NOT_ACTIVE",
            )
        if not profile.default_cost_code_id:
            raise BusinessRuleError(
                "Project requires a default cost code before commitments can synchronize.",
                code="PROJECT_COMMITMENT_DEFAULT_COST_CODE_REQUIRED",
            )
        return self._ingest_procurement_source(
            source,
            cost_code_id=profile.default_cost_code_id,
            exchange_rate=exchange_rate,
            exchange_rate_date=exchange_rate_date,
            exchange_rate_source=exchange_rate_source,
            exchange_rate_captured_at=exchange_rate_captured_at,
            actor_id="integration:project_finance",
            authorize=False,
            commit=False,
        )

    def _ingest_procurement_source(
        self,
        source: ProcurementCommitmentFinancialSource,
        *,
        cost_code_id: str,
        exchange_rate: Decimal | None,
        exchange_rate_date: date | None,
        exchange_rate_source: str | None,
        exchange_rate_captured_at: datetime | None,
        actor_id: str,
        authorize: bool,
        commit: bool,
    ) -> ProjectCommitmentLine:

        reference = source.reference
        context = self._require_full_context("synchronize project commitment")
        if (
            reference.tenant_id != context.tenant.id
            or reference.organization_id != context.organization.id
        ):
            raise BusinessRuleError(
                "Commitment source scope does not match the active organization.",
                code="PROJECT_COMMITMENT_SOURCE_SCOPE_MISMATCH",
            )
        if authorize:
            self._require_manage_permission(
                reference.project_id, "synchronize project commitment"
            )
        self._require_dimensions(
            project_id=reference.project_id,
            cost_code_id=cost_code_id,
            task_id=source.task_id,
            effective_date=source.order_date or self._clock.now().date(),
        )
        self._require_supplier_and_site(source.supplier_party_id, source.site_id)
        source_revision = self._source_revision(reference.source_revision)
        quantity = source.ordered_quantity.to_domain()
        rate = source.unit_price.to_domain()
        money = rate.apply(quantity).rounded()
        fx_rate, fx_date, fx_source, fx_captured_at = self._resolve_fx_snapshot(
            currency_code=money.currency.code,
            base_currency=context.organization.base_currency,
            effective_date=source.order_date or self._clock.now().date(),
            exchange_rate=exchange_rate,
            exchange_rate_date=exchange_rate_date,
            exchange_rate_source=exchange_rate_source,
            exchange_rate_captured_at=exchange_rate_captured_at,
        )
        base_money = Money.of(
            money.amount * fx_rate, context.organization.base_currency
        ).rounded()
        now = self._clock.now()
        snapshot_json = json.dumps(source.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))

        try:
            with self._session.begin_nested():
                line, operation, replay = self._apply_source_projection(
                    source=source,
                    cost_code_id=cost_code_id,
                    source_revision=source_revision,
                    quantity=quantity,
                    rate=rate,
                    money=money,
                    base_money=base_money,
                    base_currency=context.organization.base_currency,
                    fx_rate=fx_rate,
                    fx_date=fx_date,
                    fx_source=fx_source,
                    fx_captured_at=fx_captured_at,
                    actor_id=actor_id,
                    occurred_at=now,
                    snapshot_json=snapshot_json,
                )
        except IntegrityError as exc:
            raise BusinessRuleError(
                "The commitment source revision conflicts with an existing projection.",
                code="PROJECT_COMMITMENT_SOURCE_REPLAY_CONFLICT",
            ) from exc
        if replay:
            return line
        self._record_line_audit(operation, line)
        if commit:
            self._commit_and_emit(line.project_id)
        else:
            self._session.flush()
        return line

    def _apply_source_projection(
        self,
        *,
        source: ProcurementCommitmentFinancialSource,
        cost_code_id: str,
        source_revision: int,
        quantity: DecimalQuantity,
        rate: MonetaryRate,
        money: Money,
        base_money: Money,
        base_currency: str,
        fx_rate: Decimal,
        fx_date: date,
        fx_source: str,
        fx_captured_at: datetime,
        actor_id: str,
        occurred_at: datetime,
        snapshot_json: str,
    ) -> tuple[ProjectCommitmentLine, str, bool]:
        reference = source.reference
        line = self._commitment_repo.get_line_by_source(
            source.purchase_order_id, source.purchase_order_line_id, for_update=True
        )
        if line is not None:
            revision = self._commitment_repo.get_source_revision(line.id, source_revision)
            if revision is not None:
                if revision.source_content_hash == reference.content_hash:
                    return line, "replay_source_revision", True
                raise BusinessRuleError(
                    "This commitment source revision was replayed with different content.",
                    code="PROJECT_COMMITMENT_SOURCE_REPLAY_CONFLICT",
                )
            self._get_or_create_header(
                source, actor_id=actor_id, occurred_at=occurred_at
            )
            self._require_unchanged_source_identity(
                line, source, base_currency, cost_code_id
            )
            expected_version = line.row_version
            line.apply_source_revision(
                state=_SOURCE_STATE_MAP[source.state.value],
                ordered_quantity=quantity.value,
                unit_price=rate.money.amount,
                amount=money.amount,
                base_amount=base_money.amount,
                exchange_rate=fx_rate,
                exchange_rate_date=fx_date,
                exchange_rate_source=fx_source,
                exchange_rate_captured_at=fx_captured_at,
                source_revision=source_revision,
                source_content_hash=reference.content_hash,
                source_idempotency_key=reference.idempotency_key,
                task_id=source.task_id,
                order_date=source.order_date,
                expected_delivery_date=source.expected_delivery_date,
                source_requisition_id=source.source_requisition_id,
                source_requisition_line_id=source.source_requisition_line_id,
                actor_id=actor_id,
                occurred_at=occurred_at,
            )
            self._commitment_repo.update_line(line, expected_row_version=expected_version)
            operation = "apply_source_revision"
        else:
            commitment = self._get_or_create_header(
                source, actor_id=actor_id, occurred_at=occurred_at
            )
            line = ProjectCommitmentLine(
                id=generate_id(), tenant_id=reference.tenant_id,
                organization_id=reference.organization_id, project_id=reference.project_id,
                commitment_id=commitment.id,
                purchase_order_line_id=source.purchase_order_line_id,
                cost_code_id=cost_code_id, task_id=source.task_id,
                state=_SOURCE_STATE_MAP[source.state.value],
                ordered_quantity=quantity.value, quantity_unit=quantity.unit,
                unit_price=rate.money.amount, amount=money.amount,
                currency_code=money.currency.code, base_amount=base_money.amount,
                base_currency_code=base_currency, exchange_rate=fx_rate,
                exchange_rate_date=fx_date, exchange_rate_source=fx_source,
                exchange_rate_captured_at=fx_captured_at, order_date=source.order_date,
                expected_delivery_date=source.expected_delivery_date,
                source_requisition_id=source.source_requisition_id,
                source_requisition_line_id=source.source_requisition_line_id,
                source_revision=source_revision,
                source_content_hash=reference.content_hash,
                source_idempotency_key=reference.idempotency_key,
                created_by=actor_id, created_at=occurred_at,
                updated_by=actor_id, updated_at=occurred_at,
            )
            self._commitment_repo.add_line(line)
            operation = "create_from_source"
        self._commitment_repo.add_source_revision(
            ProjectCommitmentSourceRevision(
                id=generate_id(), tenant_id=line.tenant_id,
                organization_id=line.organization_id, project_id=line.project_id,
                commitment_line_id=line.id, source_revision=source_revision,
                source_content_hash=reference.content_hash,
                source_idempotency_key=reference.idempotency_key,
                snapshot_json=snapshot_json, observed_at=occurred_at,
            )
        )
        self._commitment_repo.flush()
        return line, operation, False

    def match_cost_entry(
        self, *, line_id: str, cost_entry_id: str
    ) -> ProjectCommitmentMatch:
        line = self._require_line(line_id, for_update=True)
        self._require_manage_permission(line.project_id, "match commitment actual")
        entry = self._cost_entry_repo.get(cost_entry_id, for_update=True)
        if entry is None:
            raise NotFoundError(
                "Project cost entry not found.", code="PROJECT_COST_ENTRY_NOT_FOUND"
            )
        return self._create_match(
            line=line,
            entry=entry,
            actor_id=self._actor_id(),
            commit=True,
        )

    def apply_procurement_receipt_match(
        self,
        *,
        purchase_order_id: str,
        purchase_order_line_id: str,
        cost_entry_id: str,
        supplier_party_id: str,
        site_id: str,
    ) -> ProjectCommitmentMatch:
        """Match one trusted receipt posting without committing the inbox transaction."""
        line = self._commitment_repo.get_line_by_source(
            purchase_order_id, purchase_order_line_id, for_update=True
        )
        if line is None:
            raise BusinessRuleError(
                "Receipt accrual requires its purchase-order commitment projection.",
                code="PROJECT_COMMITMENT_RECEIPT_SOURCE_NOT_FOUND",
            )
        commitment = self._commitment_repo.get(line.commitment_id)
        if commitment is None:
            raise BusinessRuleError(
                "Receipt accrual commitment header is missing.",
                code="PROJECT_COMMITMENT_HEADER_INTEGRITY_FAILED",
            )
        if (
            commitment.supplier_party_id != supplier_party_id
            or commitment.site_id != site_id
        ):
            raise BusinessRuleError(
                "Receipt supplier or site does not match the purchase-order commitment.",
                code="PROJECT_COMMITMENT_RECEIPT_DIMENSION_MISMATCH",
            )
        entry = self._cost_entry_repo.get(cost_entry_id, for_update=True)
        if entry is None:
            raise NotFoundError(
                "Project cost entry not found.", code="PROJECT_COST_ENTRY_NOT_FOUND"
            )
        return self._create_match(
            line=line,
            entry=entry,
            actor_id="integration:project_finance",
            commit=False,
        )

    def _create_match(
        self,
        *,
        line: ProjectCommitmentLine,
        entry,
        actor_id: str,
        commit: bool,
    ) -> ProjectCommitmentMatch:
        if (
            entry.status != ProjectCostEntryStatus.POSTED
            or entry.entry_kind == ProjectCostEntryKind.REVERSAL
            or entry.source_module != FinancialSourceModule.INVENTORY_PROCUREMENT
            or entry.source_type != FinancialSourceType.RECEIPT_LINE
            or entry.posting_purpose != FinancialPostingPurpose.RECEIPT_ACCRUAL
        ):
            raise BusinessRuleError(
                "Only posted Procurement receipt-accrual entries can be matched to commitments.",
                code="PROJECT_COMMITMENT_COST_ENTRY_NOT_MATCHABLE",
            )
        if entry.project_id != line.project_id or entry.currency_code != line.currency_code:
            raise BusinessRuleError(
                "Commitment and cost entry project/currency dimensions must match.",
                code="PROJECT_COMMITMENT_COST_ENTRY_DIMENSION_MISMATCH",
            )
        idempotency_key = self._match_idempotency_key("match", line.id, entry.id)
        replay = self._commitment_repo.get_match_by_idempotency_key(idempotency_key)
        if replay is not None:
            return replay
        existing = self._commitment_repo.get_original_match_for_cost_entry(entry.id)
        if existing is not None:
            raise BusinessRuleError(
                "This cost entry is already matched to another commitment line.",
                code="PROJECT_COMMITMENT_COST_ENTRY_ALREADY_MATCHED",
            )
        now = self._clock.now()
        remaining_amount = line.amount - line.matched_amount
        matched_amount = min(entry.amount, remaining_amount)
        if matched_amount <= 0:
            raise BusinessRuleError(
                "Commitment line has no remaining amount available for this receipt.",
                code="PROJECT_COMMITMENT_NO_REMAINING_MATCH_AMOUNT",
            )
        amount = Money.of(matched_amount, entry.currency_code)
        expected_version = line.row_version
        line.apply_match(amount, actor_id=actor_id, occurred_at=now)
        match = ProjectCommitmentMatch(
            id=generate_id(), tenant_id=line.tenant_id, organization_id=line.organization_id,
            project_id=line.project_id, commitment_line_id=line.id, cost_entry_id=entry.id,
            kind=ProjectCommitmentMatchKind.MATCH, amount=amount.amount,
            currency_code=amount.currency.code, idempotency_key=idempotency_key,
            created_by=actor_id, created_at=now,
        )
        try:
            with self._session.begin_nested():
                self._commitment_repo.update_line(line, expected_row_version=expected_version)
                self._commitment_repo.add_match(match)
                self._commitment_repo.flush()
        except IntegrityError as exc:
            raise BusinessRuleError(
                "The cost entry was matched concurrently.",
                code="PROJECT_COMMITMENT_MATCH_CONFLICT",
            ) from exc
        self._record_match_audit("match", match, line)
        if commit:
            self._commit_and_emit(line.project_id)
        else:
            self._session.flush()
        return match

    def reverse_match(
        self, *, original_match_id: str, reversal_cost_entry_id: str
    ) -> ProjectCommitmentMatch:
        original = self._commitment_repo.get_match(original_match_id)
        if original is None or original.kind != ProjectCommitmentMatchKind.MATCH:
            raise NotFoundError(
                "Original commitment match not found.",
                code="PROJECT_COMMITMENT_MATCH_NOT_FOUND",
            )
        line = self._require_line(original.commitment_line_id, for_update=True)
        self._require_manage_permission(line.project_id, "reverse commitment match")
        entry = self._cost_entry_repo.get(reversal_cost_entry_id, for_update=True)
        if entry is None:
            raise NotFoundError(
                "Reversal cost entry not found.", code="PROJECT_COST_ENTRY_NOT_FOUND"
            )
        if (
            entry.status != ProjectCostEntryStatus.POSTED
            or entry.entry_kind != ProjectCostEntryKind.REVERSAL
            or entry.reverses_entry_id != original.cost_entry_id
            or abs(entry.amount) < original.amount
            or entry.currency_code != original.currency_code
        ):
            raise BusinessRuleError(
                "The reversal entry must reverse at least the matched commitment amount.",
                code="PROJECT_COMMITMENT_MATCH_REVERSAL_INVALID",
            )
        idempotency_key = self._match_idempotency_key(
            "reversal", original.id, entry.id
        )
        replay = self._commitment_repo.get_match_by_idempotency_key(idempotency_key)
        if replay is not None:
            return replay
        if self._commitment_repo.has_reversal_for_match(original.id):
            raise BusinessRuleError(
                "This commitment match has already been reversed.",
                code="PROJECT_COMMITMENT_MATCH_ALREADY_REVERSED",
            )
        actor_id = self._actor_id()
        now = self._clock.now()
        amount = Money.of(original.amount, original.currency_code)
        expected_version = line.row_version
        line.reverse_match(amount, actor_id=actor_id, occurred_at=now)
        reversal = ProjectCommitmentMatch(
            id=generate_id(), tenant_id=line.tenant_id, organization_id=line.organization_id,
            project_id=line.project_id, commitment_line_id=line.id, cost_entry_id=entry.id,
            kind=ProjectCommitmentMatchKind.REVERSAL, amount=-original.amount,
            currency_code=original.currency_code, idempotency_key=idempotency_key,
            reverses_match_id=original.id, created_by=actor_id, created_at=now,
        )
        try:
            with self._session.begin_nested():
                self._commitment_repo.update_line(line, expected_row_version=expected_version)
                self._commitment_repo.add_match(reversal)
                self._commitment_repo.flush()
        except IntegrityError as exc:
            raise BusinessRuleError(
                "The commitment match was reversed concurrently.",
                code="PROJECT_COMMITMENT_MATCH_REVERSAL_CONFLICT",
            ) from exc
        self._record_match_audit("reverse_match", reversal, line)
        self._commit_and_emit(line.project_id)
        return reversal

    def _get_or_create_header(
        self,
        source: ProcurementCommitmentFinancialSource,
        *,
        actor_id: str,
        occurred_at: datetime,
    ) -> ProjectCommitment:
        existing = self._commitment_repo.get_by_purchase_order(source.purchase_order_id)
        if existing is not None:
            if (
                existing.project_id != source.reference.project_id
                or existing.purchase_order_number != source.purchase_order_number
                or existing.supplier_party_id != source.supplier_party_id
                or existing.site_id != source.site_id
            ):
                raise BusinessRuleError(
                    "Purchase order commitment identity changed after projection creation.",
                    code="PROJECT_COMMITMENT_SOURCE_IDENTITY_CONFLICT",
                )
            return existing
        commitment = ProjectCommitment.create(
            tenant_id=source.reference.tenant_id,
            organization_id=source.reference.organization_id,
            project_id=source.reference.project_id,
            purchase_order_id=source.purchase_order_id,
            purchase_order_number=source.purchase_order_number,
            supplier_party_id=source.supplier_party_id,
            site_id=source.site_id,
            actor_id=actor_id,
            occurred_at=occurred_at,
        )
        self._commitment_repo.add(commitment)
        self._commitment_repo.flush()
        return commitment

    def _require_dimensions(
        self,
        *,
        project_id: str,
        cost_code_id: str,
        task_id: str | None,
        effective_date: date,
    ) -> None:
        if self._project_repo.get(project_id) is None:
            raise NotFoundError("Project not found.", code="PROJECT_NOT_FOUND")
        profile = self._financial_profile_repo.get_by_project(project_id)
        if profile is None or profile.status != FinancialProfileStatus.ACTIVE:
            raise BusinessRuleError(
                "An active project financial profile is required for commitments.",
                code="PROJECT_FINANCIAL_PROFILE_NOT_ACTIVE",
            )
        cost_code = self._cost_code_repo.get(cost_code_id)
        if cost_code is None:
            raise NotFoundError("Cost code not found.", code="PROJECT_COST_CODE_NOT_FOUND")
        if not cost_code.is_effective_on(effective_date):
            raise BusinessRuleError(
                "Cost code is not effective for the commitment date.",
                code="PROJECT_COMMITMENT_COST_CODE_INACTIVE",
            )
        if profile.cost_code_policy == CostCodePolicy.RESTRICTED:
            allowed = {
                item.cost_code_id for item in self._cost_code_repo.list_restrictions(project_id)
            }
            if cost_code_id not in allowed:
                raise BusinessRuleError(
                    "Cost code is not permitted for this project.",
                    code="PROJECT_COMMITMENT_COST_CODE_NOT_PERMITTED",
                )
        if task_id:
            task = self._task_repo.get(task_id)
            if task is None:
                raise NotFoundError("Task not found.", code="TASK_NOT_FOUND")
            if task.project_id != project_id:
                raise BusinessRuleError(
                    "Task does not belong to the commitment project.",
                    code="PROJECT_COMMITMENT_TASK_PROJECT_MISMATCH",
                )

    def _require_supplier_and_site(self, supplier_party_id: str, site_id: str) -> None:
        supplier = self._party_repo.get(supplier_party_id)
        if supplier is None or not supplier.is_active:
            raise NotFoundError(
                "Active supplier party not found.", code="PROJECT_COMMITMENT_SUPPLIER_NOT_FOUND"
            )
        site = self._site_repo.get(site_id)
        if site is None or not site.is_active:
            raise NotFoundError(
                "Active site not found.", code="PROJECT_COMMITMENT_SITE_NOT_FOUND"
            )

    @staticmethod
    def _require_unchanged_source_identity(
        line: ProjectCommitmentLine,
        source: ProcurementCommitmentFinancialSource,
        base_currency: str,
        cost_code_id: str,
    ) -> None:
        if (
            line.project_id != source.reference.project_id
            or line.cost_code_id != cost_code_id
            or line.quantity_unit != source.ordered_quantity.unit
            or line.currency_code != source.unit_price.currency
            or line.base_currency_code != base_currency
        ):
            raise BusinessRuleError(
                "Commitment source project, unit, or currency changed after recognition.",
                code="PROJECT_COMMITMENT_SOURCE_IDENTITY_CONFLICT",
            )

    def _resolve_fx_snapshot(
        self,
        *,
        currency_code: str,
        base_currency: str,
        effective_date: date,
        exchange_rate: Decimal | None,
        exchange_rate_date: date | None,
        exchange_rate_source: str | None,
        exchange_rate_captured_at: datetime | None,
    ) -> tuple[Decimal, date, str, datetime]:
        if currency_code == base_currency:
            if exchange_rate not in (None, Decimal("1"), 1, "1"):
                raise ValidationError(
                    "Identity-currency commitments must use exchange rate 1.",
                    code="PROJECT_COMMITMENT_IDENTITY_RATE_INVALID",
                )
            return Decimal("1"), effective_date, "identity", self._clock.now()
        if (
            exchange_rate is None
            or exchange_rate_date is None
            or not str(exchange_rate_source or "").strip()
            or exchange_rate_captured_at is None
        ):
            raise ValidationError(
                "Cross-currency commitments require a complete exchange-rate snapshot.",
                code="PROJECT_COMMITMENT_FX_SNAPSHOT_REQUIRED",
            )
        rate = EXCHANGE_RATE_STORAGE.validate(exchange_rate)
        if rate <= 0:
            raise ValidationError(
                "Commitment exchange rate must be positive.",
                code="PROJECT_COMMITMENT_EXCHANGE_RATE_INVALID",
            )
        if exchange_rate_captured_at.tzinfo is None or exchange_rate_captured_at.utcoffset() is None:
            raise ValidationError(
                "Exchange-rate capture timestamp must include a timezone.",
                code="PROJECT_COMMITMENT_FX_CAPTURE_TIME_INVALID",
            )
        return (
            rate,
            exchange_rate_date,
            str(exchange_rate_source).strip(),
            exchange_rate_captured_at,
        )

    @staticmethod
    def _source_revision(value: str) -> int:
        try:
            revision = int(value)
        except (TypeError, ValueError) as exc:
            raise ValidationError(
                "Procurement commitment source revision must be a positive integer.",
                code="PROJECT_COMMITMENT_SOURCE_REVISION_INVALID",
            ) from exc
        if revision < 1:
            raise ValidationError(
                "Procurement commitment source revision must be a positive integer.",
                code="PROJECT_COMMITMENT_SOURCE_REVISION_INVALID",
            )
        return revision

    def _require_line(
        self, line_id: str, *, for_update: bool = False
    ) -> ProjectCommitmentLine:
        line = self._commitment_repo.get_line(line_id, for_update=for_update)
        if line is None:
            raise NotFoundError(
                "Project commitment line not found.", code="PROJECT_COMMITMENT_LINE_NOT_FOUND"
            )
        return line

    def _require_manage_permission(self, project_id: str, operation: str) -> None:
        require_permission(self._user_session, "finance.manage", operation_label=operation)
        require_project_permission(
            self._user_session, project_id, "finance.manage", operation_label=operation
        )

    def _require_full_context(self, operation: str):
        if self._tenant_context_service is None:
            raise BusinessRuleError(
                f"Active organization context is required to {operation}.",
                code="TENANT_CONTEXT_REQUIRED",
            )
        context = self._tenant_context_service.require_organization_context(
            operation_label=operation
        )
        if context.organization is None:
            raise BusinessRuleError(
                "Active organization context is required.",
                code="ORGANIZATION_CONTEXT_REQUIRED",
            )
        return context

    def _actor_id(self) -> str:
        actor_id = getattr(getattr(self._user_session, "principal", None), "user_id", None)
        if not actor_id:
            raise BusinessRuleError(
                "An authenticated actor is required for commitment commands.",
                code="PROJECT_COMMITMENT_ACTOR_REQUIRED",
            )
        return str(actor_id)

    @staticmethod
    def _match_idempotency_key(operation: str, left_id: str, right_id: str) -> str:
        digest = canonical_json_sha256(
            {"operation": operation, "left_id": left_id, "right_id": right_id}
        )
        return f"pcmatch:v1:{digest}"

    def _record_line_audit(self, operation: str, line: ProjectCommitmentLine) -> None:
        record_audit_entry(
            self,
            operation=f"project_commitment.{operation}",
            entity_type="project_commitment_line",
            entity_id=line.id,
            entity_parent_id=line.project_id,
            module="project_management",
            old_value=None,
            new_value=json.dumps(
                {
                    "state": line.state.value,
                    "amount": MoneyPayload.from_domain(line.money).amount,
                    "currency_code": line.currency_code,
                    "base_amount": MoneyPayload.from_domain(
                        Money.of(line.base_amount, line.base_currency_code)
                    ).amount,
                    "base_currency_code": line.base_currency_code,
                    "matched_amount": MoneyPayload.from_domain(line.matched_money).amount,
                    "remaining_amount": MoneyPayload.from_domain(line.remaining_money).amount,
                    "source_revision": line.source_revision,
                    "source_content_hash": line.source_content_hash,
                    "row_version": line.row_version,
                },
                sort_keys=True,
            ),
            workspace_id=line.project_id,
            source="application",
            severity="high",
            compliance_tag="financial",
            metadata={"action": operation},
            commit=False,
            fail_closed=True,
        )

    def _record_match_audit(
        self, operation: str, match: ProjectCommitmentMatch, line: ProjectCommitmentLine
    ) -> None:
        record_audit_entry(
            self,
            operation=f"project_commitment.{operation}",
            entity_type="project_commitment_match",
            entity_id=match.id,
            entity_parent_id=line.project_id,
            module="project_management",
            old_value=None,
            new_value=json.dumps(
                {
                    "kind": match.kind.value,
                    "commitment_line_id": match.commitment_line_id,
                    "cost_entry_id": match.cost_entry_id,
                    "amount": str(match.amount),
                    "currency_code": match.currency_code,
                    "reverses_match_id": match.reverses_match_id,
                },
                sort_keys=True,
            ),
            workspace_id=line.project_id,
            source="application",
            severity="high",
            compliance_tag="financial",
            metadata={"action": operation},
            commit=False,
            fail_closed=True,
        )

    def _commit_and_emit(self, project_id: str) -> None:
        self._session.commit()
        domain_events.commitments_changed.emit(project_id)


__all__ = ["ProjectCommitmentService"]

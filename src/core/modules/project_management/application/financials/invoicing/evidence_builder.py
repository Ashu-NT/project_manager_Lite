from __future__ import annotations

from src.core.modules.project_management.access.scope_permissions import (
    require_project_permission,
)
from src.core.modules.project_management.domain.financials.billing_preparation import (
    BillingPreparationStatus,
    ProjectBillingPreparation,
    ProjectBillingPreparationLine,
)
from src.core.modules.project_management.domain.financials.billing_profile import (
    ProjectBillingProfile,
)
from src.core.modules.project_management.gateway.billing.accounting_billing import (
    BillingPreparationLinePayload,
    ProjectBillingPreparationPayload,
)
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)
from src.core.platform.common.exceptions import BusinessRuleError
from src.core.platform.domain.security.auth.session import UserSessionContext


class BillingPreparationEvidenceBuilder:
    """Build immutable approved evidence without owning persistence or a transaction."""

    def __init__(self, *, user_session: UserSessionContext | None) -> None:
        self._user_session = user_session

    def build(
        self,
        preparation: ProjectBillingPreparation,
        profile: ProjectBillingProfile,
        *,
        message_id: str,
        approved_lines: tuple[ProjectBillingPreparationLine, ...],
    ) -> ProjectBillingPreparationPayload:
        require_permission(
            self._user_session, "finance.read",
            operation_label="build accounting delivery payload",
        )
        require_project_permission(
            self._user_session, preparation.project_id, "finance.read",
            operation_label="build accounting delivery payload",
        )
        if preparation.status is not BillingPreparationStatus.APPROVED:
            raise BusinessRuleError(
                "Only approved billing evidence can cross the accounting boundary.",
                code="BILLING_DELIVERY_NOT_APPROVED",
            )
        if not profile.customer_party_id or not preparation.approved_by or not preparation.approved_at:
            raise BusinessRuleError(
                "Approved billing evidence is incomplete.", code="BILLING_DELIVERY_INCOMPLETE"
            )
        lines = tuple(
            BillingPreparationLinePayload(
                line_id=line.id,
                source_type=line.source_type.value,
                source_id=line.source_id,
                source_revision=line.source_revision,
                source_content_hash=line.source_content_hash,
                description=line.description,
                source_date=line.source_date,
                quantity=format(line.quantity, "f"),
                unit=line.unit,
                unit_rate=format(line.unit_rate, "f"),
                net_amount=format(line.net_amount, "f"),
                currency_code=line.currency_code,
                task_id=line.task_id,
                resource_id=line.resource_id,
            )
            for line in approved_lines
        )
        return ProjectBillingPreparationPayload(
            schema_name="project_billing_preparation.v1",
            message_id=message_id,
            tenant_id=preparation.tenant_id,
            organization_id=preparation.organization_id,
            project_id=preparation.project_id,
            preparation_id=preparation.id,
            preparation_number=preparation.preparation_number,
            billing_method=preparation.billing_method.value,
            period_start=preparation.period_start,
            period_end=preparation.period_end,
            currency_code=preparation.currency_code,
            customer_party_id=profile.customer_party_id,
            contract_reference=profile.contract_reference,
            external_customer_reference=profile.external_customer_reference,
            purchase_order_reference=profile.purchase_order_reference,
            payment_terms_days=profile.payment_terms_days,
            total_amount=format(preparation.total_amount, "f"),
            approved_by=preparation.approved_by,
            approved_at=preparation.approved_at,
            lines=lines,
        )

__all__ = ["BillingPreparationEvidenceBuilder"]

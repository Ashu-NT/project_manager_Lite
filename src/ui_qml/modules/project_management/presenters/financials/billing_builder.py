from __future__ import annotations

from src.core.modules.project_management.api.desktop.financials.models.billing import FinancialBillingWorkspaceDto
from src.ui_qml.modules.project_management.view_models.financials import (
    FinancialsCollectionViewModel,
    FinancialsDetailFieldViewModel,
    FinancialsDetailViewModel,
    FinancialsRecordViewModel,
)


def build_billing_views(source: FinancialBillingWorkspaceDto) -> dict[str, object]:
    profile = source.profile
    return {
        "billing_profile": FinancialsDetailViewModel(
            id=profile.id,
            title="Commercial Billing Profile",
            status_label=profile.status.replace("_", " ").title(),
            subtitle="PM commercial terms used to prepare billing evidence.",
            empty_state="Configure a billable Project profile before preparing billing evidence.",
            fields=(
                FinancialsDetailFieldViewModel("Contract", profile.contract_reference),
                FinancialsDetailFieldViewModel(
                    "Contract value", f"{profile.contract_value} {profile.currency_code}"
                ),
                FinancialsDetailFieldViewModel("Customer Party", profile.customer_party_id),
                FinancialsDetailFieldViewModel(
                    "External customer", profile.external_customer_reference or "Not mapped"
                ),
                FinancialsDetailFieldViewModel(
                    "Purchase order", profile.purchase_order_reference or "Not supplied"
                ),
                FinancialsDetailFieldViewModel(
                    "Payment terms", f"{profile.payment_terms_days} days"
                ),
            ) if profile.id else (),
        ),
        "billing_schedule": FinancialsCollectionViewModel(
            title="Fixed-Price Schedule",
            subtitle="PM-owned commercial milestones eligible for preparation.",
            empty_state="No fixed-price billing schedule lines exist.",
            items=tuple(
                FinancialsRecordViewModel(
                    id=item.id,
                    title=item.name,
                    status_label=item.status.replace("_", " ").title(),
                    subtitle=f"Due {item.due_date}",
                    supporting_text=item.acceptance_reference or "No acceptance reference",
                    meta_text=f"{item.amount} {item.currency_code}",
                    can_primary_action=False,
                    can_secondary_action=False,
                    state={"rowVersion": item.row_version, "taskId": item.task_id},
                )
                for item in source.schedule_lines
            ),
        ),
        "billing_preparations": FinancialsCollectionViewModel(
            title="Billing Preparations",
            subtitle="Governed PM evidence and externally reported accounting outcomes.",
            empty_state="No billing preparation exists for this project.",
            items=tuple(
                FinancialsRecordViewModel(
                    id=item.id,
                    title=item.preparation_number,
                    status_label=item.status.replace("_", " ").title(),
                    subtitle=f"{item.billing_method.replace('_', ' ').title()} | {item.period_label}",
                    supporting_text=(
                        f"Accounting: {item.external_system} / {item.external_status}"
                        if item.external_system
                        else "Not yet acknowledged by Accounting"
                    ),
                    meta_text=f"{item.total_amount} {item.currency_code} | {item.line_count} sources",
                    can_primary_action=False,
                    can_secondary_action=False,
                    state={
                        "rowVersion": item.row_version,
                        "externalInvoiceReference": item.external_invoice_reference,
                        "reconciliationReference": item.reconciliation_reference,
                    },
                )
                for item in source.preparations
            ),
            page=source.preparation_page,
            page_size=source.preparation_page_size,
            total=source.preparation_total,
        ),
    }


__all__ = ["build_billing_views"]

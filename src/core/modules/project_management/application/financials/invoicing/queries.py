from __future__ import annotations

from dataclasses import replace

from src.core.modules.project_management.access.scope_permissions import (
    require_project_permission,
)
from src.core.modules.project_management.application.financials.accounting.status_capabilities import (
    with_accounting_capabilities,
)
from src.core.modules.project_management.contracts.reads.financials.models.finance_billing_facts import (
    AccountingStatusFact,
    AccountingStatusQuery,
    BillingPreparationLineQuery,
    BillingPreparationQuery,
    BillingScheduleQuery,
    BillingSourceOptionFact,
    BillingSourceQuery,
    FinanceBillingWorkspaceFacts,
)
from src.core.modules.project_management.contracts.reads.financials.models.finance_budget_facts import (
    FinancePageFacts,
)
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)


class InvoicingWorkspaceQueries:
    def list_eligible_billing_sources(
        self, project_id: str, preparation_id: str, *, request: BillingSourceQuery
    ) -> FinancePageFacts[BillingSourceOptionFact]:
        require_permission(
            self._user_session, "finance.manage",
            operation_label="select billable preparation source",
        )
        require_project_permission(
            self._user_session, project_id, "finance.manage",
            operation_label="select billable preparation source",
        )
        if self._billing_reader is None or self._tenant_context_service is None:
            raise RuntimeError("Finance Billing Reader is not configured.")
        scope = self._tenant_context_service.require_active_scope_ids(
            operation_label="select billable preparation source"
        )
        return self._billing_reader.list_eligible_sources(
            tenant_id=scope.tenant_id,
            organization_id=scope.organization_id,
            project_id=project_id,
            preparation_id=preparation_id,
            request=request,
        )

    def get_billing_read_workspace(
        self,
        project_id: str,
        *,
        selected_preparation_id: str = "",
        schedule_request: BillingScheduleQuery | None = None,
        preparation_request: BillingPreparationQuery | None = None,
        line_request: BillingPreparationLineQuery | None = None,
    ) -> FinanceBillingWorkspaceFacts:
        require_permission(
            self._user_session,
            "finance.read",
            operation_label="view project commercial billing evidence",
        )
        require_project_permission(
            self._user_session,
            project_id,
            "finance.read",
            operation_label="view project commercial billing evidence",
        )
        if self._billing_reader is None or self._tenant_context_service is None:
            raise RuntimeError("Finance Billing Reader is not configured.")
        scope = self._tenant_context_service.require_active_scope_ids(
            operation_label="view project commercial billing evidence"
        )
        arguments = {
            "tenant_id": scope.tenant_id,
            "organization_id": scope.organization_id,
            "project_id": project_id,
        }
        profile = self._billing_reader.get_profile(**arguments)
        if profile is not None:
            profile = replace(
                profile,
                can_activate=(
                    self._has_project_permission(project_id, "finance.manage")
                    and profile.status == "draft"
                ),
                can_add_schedule_line=(
                    self._has_project_permission(project_id, "finance.manage")
                    and profile.status == "active"
                ),
                can_create_preparation=(
                    self._has_project_permission(project_id, "finance.manage")
                    and profile.status == "active"
                ),
            )
        schedule = self._billing_reader.list_schedule(
            **arguments,
            request=schedule_request or BillingScheduleQuery(),
        )
        schedule = replace(
            schedule,
            items=tuple(
                replace(
                    item,
                    can_mark_ready=(
                        self._has_project_permission(project_id, "finance.manage")
                        and item.status == "planned"
                    ),
                )
                for item in schedule.items
            ),
        )
        preparations = self._billing_reader.list_preparations(
            **arguments,
            request=preparation_request or BillingPreparationQuery(),
        )
        requested_id = str(selected_preparation_id or "").strip()
        selected = (
            self._billing_reader.get_preparation(
                **arguments,
                preparation_id=requested_id,
            )
            if requested_id
            else None
        )
        resolved_id = selected.id if selected is not None else ""
        if selected is not None:
            can_manage = self._has_project_permission(project_id, "finance.manage")
            can_decide = self._has_project_permission(project_id, "approval.decide")
            actor_id = str(
                getattr(getattr(self._user_session, "principal", None), "user_id", "")
                or ""
            )
            is_draft = selected.status == "draft"
            independent_decider = bool(
                actor_id
                and actor_id != selected.created_by
                and actor_id != (selected.submitted_by or "")
            )
            from src.core.platform.domain.integration.accounting.connector import (
                AccountingHandoffCapability,
                AccountingHandoffDenial,
            )
            handoff = (
                self._accounting_capability.evaluate(
                    authorized=self._has_project_permission(project_id, "finance.accounting_handoff.request"),
                    eligible=bool(selected.status == "approved" and selected.line_count > 0
                                  and selected.approval_request_id and selected.approved_by and selected.approved_at),
                ) if self._accounting_capability is not None else AccountingHandoffCapability(
                    allowed=False, reason=AccountingHandoffDenial.ADAPTER_NOT_INSTALLED,
                )
            )
            selected = replace(
                selected,
                can_edit_draft=can_manage and is_draft,
                can_add_source=can_manage and is_draft,
                can_remove_source=can_manage and is_draft and selected.line_count > 0,
                can_submit=can_manage and is_draft and selected.line_count > 0,
                can_approve=can_decide and selected.status == "submitted" and independent_decider,
                can_reject=can_decide and selected.status == "submitted" and independent_decider,
                can_cancel=can_manage and is_draft,
                can_create_correction=can_manage and selected.status == "reconciled",
                can_request_delivery=handoff.allowed,
                handoff_denial_reason=handoff.reason.value if handoff.reason else "",
                handoff_denial_message=handoff.message,
                can_view_accounting_status=self._has_project_permission(project_id, "finance.accounting_status.read"),
            )
        requested_lines = line_request or BillingPreparationLineQuery()
        lines = (
            self._billing_reader.list_preparation_lines(
                **arguments,
                preparation_id=resolved_id,
                request=requested_lines,
            )
            if resolved_id
            else FinancePageFacts(
                items=(),
                total=0,
                page=requested_lines.normalized_page,
                page_size=requested_lines.normalized_page_size,
                sort_key=requested_lines.normalized_sort_key,
                sort_direction=(
                    "asc" if requested_lines.sort_direction == "asc" else "desc"
                ),
            )
        )
        if not self._has_project_permission(project_id, "finance.read_sensitive"):
            lines = replace(
                lines,
                items=tuple(
                    replace(
                        item,
                        unit_rate=None,
                        resource_id=None,
                        source_amount=None,
                        markup_percent=None,
                        rate_card_id=None,
                        rate_line_id=None,
                        rate_card_version=None,
                    )
                    for item in lines.items
                ),
            )
        if not self._has_project_permission(project_id, "finance.accounting_status.read"):
            def without_external_status(item):
                return replace(
                    item, latest_external_event_type="", latest_external_system="",
                    latest_external_status="", latest_external_invoice_reference="",
                    latest_reconciliation_reference="", latest_external_message="",
                    latest_external_occurred_at=None,
                )
            preparations = replace(preparations, items=tuple(
                replace(item, latest_external_event_type="", latest_external_system="",
                        latest_external_status="", latest_external_occurred_at=None)
                for item in preparations.items
            ))
            if selected is not None:
                selected = without_external_status(selected)
        return FinanceBillingWorkspaceFacts(
            profile=profile,
            selected_preparation_id=resolved_id,
            selected_preparation=selected,
            schedule=schedule,
            preparations=preparations,
            lines=lines,
            can_manage_billing=self._has_project_permission(project_id, "finance.manage"),
        )

    def get_accounting_statuses(
        self,
        project_id: str,
        *,
        request: AccountingStatusQuery | None = None,
    ) -> FinancePageFacts[AccountingStatusFact]:
        require_permission(
            self._user_session, "finance.accounting_status.read",
            operation_label="view Accounting handoff status",
        )
        require_project_permission(
            self._user_session, project_id, "finance.accounting_status.read",
            operation_label="view Accounting handoff status",
        )
        require_permission(
            self._user_session,
            "finance.read",
            operation_label="view project Accounting outcomes",
        )
        require_project_permission(
            self._user_session,
            project_id,
            "finance.read",
            operation_label="view project Accounting outcomes",
        )
        if self._billing_reader is None or self._tenant_context_service is None:
            raise RuntimeError("Finance Billing Reader is not configured.")
        scope = self._tenant_context_service.require_active_scope_ids(
            operation_label="view project Accounting outcomes"
        )
        page = self._billing_reader.list_accounting_statuses(
            tenant_id=scope.tenant_id,
            organization_id=scope.organization_id,
            project_id=project_id,
            request=request or AccountingStatusQuery(),
        )
        return with_accounting_capabilities(
            page, capability_service=self._accounting_capability,
            authorized=self._has_project_permission(project_id, "finance.accounting_handoff.request"),
        )

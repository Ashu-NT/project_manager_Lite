from __future__ import annotations

from typing import Any, cast

from src.core.platform.application.approval.approval_mutation_participant import (
    build_request_audit_details,
    request_approval_using,
)
from src.core.platform.application.approval.dto.responses.requests import (
    ApprovalRequestResponse,
)
from src.core.platform.application.approval.mappers.requests import (
    approval_request_response,
)
from src.core.platform.application.approval.participants import (
    ApprovalParticipantRegistry,
)
from src.core.platform.application.approval.scope import ApprovalScope
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)
from src.core.platform.common.exceptions import BusinessRuleError, NotFoundError
from src.core.platform.common.ids import generate_id
from src.core.platform.contract.models.approval.contracts import (
    ApprovalDecisionInput,
    ApprovalHandlerResult,
)
from src.core.platform.contract.repositories.approval.contracts import (
    ApprovalRepository,
)
from src.core.platform.contract.uow.approval.approval_unit_of_work import (
    PlatformUnitOfWorkFactory,
)
from src.core.platform.domain.approval import (
    ApprovalApproved,
    ApprovalRejected,
    ApprovalRequest,
    ApprovalStatus,
)
from src.core.platform.domain.security.auth.session import UserSessionContext
from src.core.shared.audit import record_audit_entry
from src.core.shared.events.domain_event_context import DomainEventContext
from src.core.shared.time.clock import Clock


class ApprovalCommandHandler:
    """Owns approval transactions, including module participants, audit and events."""

    def __init__(
        self,
        *,
        uow_factory: PlatformUnitOfWorkFactory,
        participants: ApprovalParticipantRegistry,
        scope: ApprovalScope,
        user_session: UserSessionContext | None = None,
        clock: Clock | None = None,
    ) -> None:
        self._uow_factory = uow_factory
        self._participants = participants
        self._scope = scope
        self._user_session = user_session
        self._clock = clock

    def _require_clock(self) -> Clock:
        if self._clock is None:
            raise BusinessRuleError(
                "Approval event recording requires a configured Clock.",
                code="APPROVAL_CLOCK_REQUIRED",
            )
        return self._clock

    def _new_context(self, *, causation_id: str | None = None) -> DomainEventContext:
        return DomainEventContext(correlation_id=generate_id(), causation_id=causation_id)

    def request_change(
        self,
        *,
        request_type: str,
        entity_type: str,
        entity_id: str,
        project_id: str | None,
        module: str | None = None,
        payload: dict | None = None,
    ) -> ApprovalRequest:
        require_permission(
            self._user_session,
            "approval.request",
            operation_label="request governed change",
        )
        tenant_context = self._scope.tenant_context
        if tenant_context is None:
            raise BusinessRuleError(
                "Tenant context is required to request a governed change.",
                code="TENANT_CONTEXT_REQUIRED",
            )
        tenant_id = tenant_context.require_active_tenant_id(
            operation_label="request governed change"
        )
        organization_id = self._scope.active_organization_id(
            operation_label="request governed change"
        )
        principal = self._user_session.principal if self._user_session else None
        clock = self._require_clock()

        with self._uow_factory.create(context=self._new_context()) as uow:
            self._scope.assert_project_in_active_organization(
                uow.approvals, project_id, operation_label="request governed change"
            )
            request = request_approval_using(
                approval_repo=uow.approvals,
                enterprise_audit_service=uow._enterprise_audit_service,
                clock=clock,
                record_event=uow.record_event,
                request_type=request_type,
                entity_type=entity_type,
                entity_id=entity_id,
                tenant_id=tenant_id,
                organization_id=organization_id,
                project_id=project_id,
                payload=payload,
                requested_by_user_id=principal.user_id if principal else None,
                requested_by_username=principal.username if principal else None,
                decision_permission=self._participants.review_permissions.get(
                    request_type.strip().lower(), "approval.decide"
                ),
            )
            uow.commit()
        return request

    def reject(self, command: ApprovalDecisionInput) -> ApprovalRequestResponse:
        request_id = command.request_id
        require_permission(
            self._user_session,
            "approval.decide",
            operation_label="reject approval request",
        )
        clock = self._require_clock()
        with self._uow_factory.create(context=self._new_context(causation_id=request_id)) as uow:
            request = self._require_pending_using(uow.approvals, request_id)
            self._ensure_not_self_decision(request)
            self._require_reviewer_eligibility(uow.approvals, request.id)
            principal = self._user_session.principal if self._user_session else None
            request.status = ApprovalStatus.REJECTED
            request.decided_at = clock.now()
            request.decided_by_user_id = principal.user_id if principal else None
            request.decided_by_username = principal.username if principal else None
            request.decision_note = command.note
            handler_result = ApprovalHandlerResult()
            registration = self._participants.reject_handlers.get(request.request_type)
            if registration is not None:
                handler, dependencies_factory = registration
                deps = dependencies_factory(cast(Any, uow)._session)
                handler_result = self._normalize_handler_result(handler(request, deps))

            uow.approvals.update(request)
            uow.record_event(
                ApprovalRejected(
                    approval_id=request.id,
                    tenant_id=request.tenant_id,
                    organization_id=request.organization_id,
                    approval_type=request.request_type,
                    entity_type=request.entity_type,
                    entity_id=request.entity_id,
                    decided_by_user_id=request.decided_by_user_id,
                    occurred_at=clock.now(),
                )
            )
            record_audit_entry(
                uow,
                operation="update",
                entity_type="approval_request",
                entity_id=request.id,
                module="platform",
                category="APPROVAL",
                severity="high",
                metadata={"action": "governance.reject", **build_request_audit_details(request, decision_note=request.decision_note)},
                commit=False,
                fail_closed=True,
            )
            for domain_event in handler_result.domain_events:
                uow.record_event(domain_event)
            uow.commit()

        return approval_request_response(request)

    def approve_and_apply(self, command: ApprovalDecisionInput) -> ApprovalRequestResponse:
        request_id = command.request_id
        require_permission(
            self._user_session,
            "approval.decide",
            operation_label="approve approval request",
        )
        clock = self._require_clock()
        with self._uow_factory.create(context=self._new_context(causation_id=request_id)) as uow:
            request = self._require_pending_using(uow.approvals, request_id)
            self._ensure_not_self_decision(request)
            self._require_reviewer_eligibility(uow.approvals, request.id)
            registration = self._participants.apply_handlers.get(request.request_type)
            if registration is None:
                raise BusinessRuleError(
                    f"No apply handler registered for '{request.request_type}'.",
                    code="APPROVAL_HANDLER_MISSING",
                )
            handler, dependencies_factory = registration
            deps = dependencies_factory(cast(Any, uow)._session)
            handler_result = self._normalize_handler_result(handler(request, deps))
            principal = self._user_session.principal if self._user_session else None
            request.status = ApprovalStatus.APPROVED
            request.decided_at = clock.now()
            request.decided_by_user_id = principal.user_id if principal else None
            request.decided_by_username = principal.username if principal else None
            request.decision_note = command.note
            uow.approvals.update(request)
            uow.record_event(
                ApprovalApproved(
                    approval_id=request.id,
                    tenant_id=request.tenant_id,
                    organization_id=request.organization_id,
                    approval_type=request.request_type,
                    entity_type=request.entity_type,
                    entity_id=request.entity_id,
                    decided_by_user_id=request.decided_by_user_id,
                    occurred_at=clock.now(),
                )
            )
            record_audit_entry(
                uow,
                operation="update",
                entity_type="approval_request",
                entity_id=request.id,
                module="platform",
                category="APPROVAL",
                severity="high",
                metadata={"action": "governance.approve", **build_request_audit_details(request, decision_note=request.decision_note)},
                commit=False,
                fail_closed=True,
            )
            for domain_event in handler_result.domain_events:
                uow.record_event(domain_event)
            uow.commit()
        return approval_request_response(request)

    def _require_pending_using(self, approval_repo: ApprovalRepository, request_id: str) -> ApprovalRequest:
        request = approval_repo.get_for_update(request_id)
        if request is None:
            raise NotFoundError("Approval request not found.", code="APPROVAL_NOT_FOUND")
        self._scope.assert_project_in_active_organization(
            approval_repo,
            request.project_id,
            operation_label="view approval request",
        )
        if request.status != ApprovalStatus.PENDING:
            raise BusinessRuleError(
                "Approval request is already decided.",
                code="APPROVAL_ALREADY_DECIDED",
            )
        return request

    def _require_reviewer_eligibility(self, approval_repo: ApprovalRepository, request_id: str) -> None:
        principal = self._user_session.principal if self._user_session else None
        if principal is None or not approval_repo.is_reviewer_eligible(request_id, principal.user_id):
            raise BusinessRuleError(
                "You are not eligible to decide this approval request.",
                code="APPROVAL_REVIEWER_NOT_ELIGIBLE",
            )

    def _ensure_not_self_decision(self, request: ApprovalRequest) -> None:
        principal = self._user_session.principal if self._user_session else None
        if principal is None or not request.requested_by_user_id:
            return
        if principal.user_id == request.requested_by_user_id:
            raise BusinessRuleError(
                "You cannot approve or reject your own governance request.",
                code="APPROVAL_SELF_DECISION_FORBIDDEN",
            )

    @staticmethod
    def _normalize_handler_result(
        result: ApprovalHandlerResult | None,
    ) -> ApprovalHandlerResult:
        if result is None:
            return ApprovalHandlerResult()
        if not isinstance(result, ApprovalHandlerResult):
            raise BusinessRuleError(
                "Approval apply handler returned an unsupported result.",
                code="APPROVAL_HANDLER_RESULT_INVALID",
            )
        return result

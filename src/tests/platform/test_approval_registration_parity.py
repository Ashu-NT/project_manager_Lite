"""P4-PRE Step 1 / P4 Step 2 (ADR-005 Section 24, Round 8): proves the 18 real approval
apply/reject registrations survive the switch from long-lived-service closures (Step 1) to
module-owned, session-parameterized transaction participants registered directly, alongside a
`dependencies_factory` (Step 2) -- no registration missing, none duplicated, none pointed at the
wrong module's participant.
"""

from __future__ import annotations

from src.core.modules.inventory_procurement.infrastructure.approval.procurement_apply_participant import (
    ProcurementApprovalParticipant,
)
from src.core.modules.inventory_procurement.infrastructure.approval.purchasing_apply_participant import (
    PurchasingApprovalParticipant,
)
from src.core.modules.project_management.infrastructure.approval.baseline_apply_participant import (
    BaselineApprovalParticipant,
)
from src.core.modules.project_management.infrastructure.approval.billing_preparation_apply_participant import (
    BillingPreparationApprovalParticipant,
)
from src.core.modules.project_management.infrastructure.approval.budget_apply_participant import (
    BudgetApprovalParticipant,
)
from src.core.modules.project_management.infrastructure.approval.financial_change_apply_participant import (
    FinancialChangeApprovalParticipant,
)
from src.core.modules.project_management.infrastructure.approval.project_cost_apply_participant import (
    ProjectCostApprovalParticipant,
)
from src.core.modules.project_management.infrastructure.approval.task_apply_participant import (
    TaskApprovalParticipant,
)

# request_type -> (participant class, has_reject_handler)
EXPECTED_APPLY_REGISTRATIONS = {
    "baseline.create": BaselineApprovalParticipant,
    "dependency.add": TaskApprovalParticipant,
    "dependency.remove": TaskApprovalParticipant,
    "dependency.update": TaskApprovalParticipant,
    "task.constraint.update": TaskApprovalParticipant,
    "scheduling.leveling.apply": TaskApprovalParticipant,
    "budget.approve": BudgetApprovalParticipant,
    "project_cost.approve": ProjectCostApprovalParticipant,
    "financial_change.apply": FinancialChangeApprovalParticipant,
    "project_billing_preparation.approve": BillingPreparationApprovalParticipant,
    "purchase_requisition.submit": ProcurementApprovalParticipant,
    "purchase_order.submit": PurchasingApprovalParticipant,
}

EXPECTED_REJECT_REGISTRATIONS = {
    "budget.approve": BudgetApprovalParticipant,
    "project_cost.approve": ProjectCostApprovalParticipant,
    "financial_change.apply": FinancialChangeApprovalParticipant,
    "project_billing_preparation.approve": BillingPreparationApprovalParticipant,
    "purchase_requisition.submit": ProcurementApprovalParticipant,
    "purchase_order.submit": PurchasingApprovalParticipant,
}


def _bound_participant_class(entry):
    # P4 Step 2: each registered entry is now `(handler, dependencies_factory)`, where `handler`
    # is the participant's own bound method (e.g. `budget_participant.apply`), registered
    # directly -- no lambda/closure indirection to unwrap any more. `handler.__self__` is the
    # participant instance itself.
    handler, dependencies_factory = entry
    assert callable(dependencies_factory), (
        f"expected a callable dependencies_factory alongside {handler}, got {dependencies_factory!r}"
    )
    participant = getattr(handler, "__self__", None)
    assert participant is not None and type(participant).__name__.endswith("ApprovalParticipant"), (
        f"expected {handler} to be a bound *ApprovalParticipant method"
    )
    return type(participant)


def test_exactly_eighteen_registrations_exist(services):
    approval_service = services["approval_service"]
    apply_handlers = approval_service._apply_handlers
    reject_handlers = approval_service._reject_handlers

    assert len(apply_handlers) == len(EXPECTED_APPLY_REGISTRATIONS), (
        f"expected {len(EXPECTED_APPLY_REGISTRATIONS)} apply handlers, "
        f"found {sorted(apply_handlers)}"
    )
    assert len(reject_handlers) == len(EXPECTED_REJECT_REGISTRATIONS), (
        f"expected {len(EXPECTED_REJECT_REGISTRATIONS)} reject handlers, "
        f"found {sorted(reject_handlers)}"
    )
    total = len(apply_handlers) + len(reject_handlers)
    assert total == 18, f"expected 18 total approval registrations, found {total}"


def test_every_expected_apply_request_type_is_registered_to_the_right_participant(services):
    apply_handlers = services["approval_service"]._apply_handlers
    for request_type, expected_class in EXPECTED_APPLY_REGISTRATIONS.items():
        assert request_type in apply_handlers, f"missing apply handler for {request_type!r}"
        actual_class = _bound_participant_class(apply_handlers[request_type])
        assert actual_class is expected_class, (
            f"{request_type!r} apply handler is bound to {actual_class.__name__}, "
            f"expected {expected_class.__name__}"
        )
    # No unexpected extras.
    assert set(apply_handlers) == set(EXPECTED_APPLY_REGISTRATIONS)


def test_every_expected_reject_request_type_is_registered_to_the_right_participant(services):
    reject_handlers = services["approval_service"]._reject_handlers
    for request_type, expected_class in EXPECTED_REJECT_REGISTRATIONS.items():
        assert request_type in reject_handlers, f"missing reject handler for {request_type!r}"
        actual_class = _bound_participant_class(reject_handlers[request_type])
        assert actual_class is expected_class, (
            f"{request_type!r} reject handler is bound to {actual_class.__name__}, "
            f"expected {expected_class.__name__}"
        )
    assert set(reject_handlers) == set(EXPECTED_REJECT_REGISTRATIONS)


def test_every_dependencies_factory_produces_deps_bound_to_the_supplied_session(tmp_path, services):
    """The Step-2 acceptance criterion: every registered `dependencies_factory` genuinely
    accepts an arbitrary Session, not just the one Session it happened to be built alongside."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from src.infra.persistence.orm.base import Base

    approval_service = services["approval_service"]
    engine = create_engine(f"sqlite:///{tmp_path}/registration_parity_probe.db", future=True)
    Base.metadata.create_all(engine)
    probe_session = sessionmaker(bind=engine, future=True)()
    try:
        for registrations in (approval_service._apply_handlers, approval_service._reject_handlers):
            for request_type, (_handler, dependencies_factory) in registrations.items():
                deps = dependencies_factory(probe_session)
                assert deps is not None, f"{request_type!r}'s dependencies_factory returned None"
    finally:
        probe_session.close()


def test_no_request_type_has_both_a_missing_and_duplicate_registration(services):
    approval_service = services["approval_service"]
    apply_keys = list(approval_service._apply_handlers.keys())
    reject_keys = list(approval_service._reject_handlers.keys())
    assert len(apply_keys) == len(set(apply_keys)), "duplicate apply registration key found"
    assert len(reject_keys) == len(set(reject_keys)), "duplicate reject registration key found"

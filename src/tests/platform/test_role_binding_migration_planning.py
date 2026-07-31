from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from unittest.mock import Mock

import pytest
from sqlalchemy import select

from src.core.platform.common.exceptions import BusinessRuleError
from src.core.platform.infrastructure.persistence.orm.audit_entry import AuditEntryORM
from src.core.platform.infrastructure.persistence.orm.auth import (
    LegacyRoleBindingMigrationRecordORM,
)
from src.core.platform.infrastructure.persistence.repositories.audit_entry import (
    SqlAlchemyAuditRepository,
)
from src.core.platform.infrastructure.persistence.repositories.auth import (
    SqlAlchemyRoleBindingMigrationRepository,
)
from src.infra.security.role_binding_migration_plan import (
    ProposedRoleScope,
    RoleBindingMigrationPlanError,
    RoleBindingMigrationReview,
    RoleBindingMigrationReviewDecision,
    build_reviewed_role_binding_migration_plan,
    build_role_binding_migration_preview,
    validate_reviewed_plan_against_preview,
)
from src.infra.security.role_binding_migration_preparation import (
    RoleBindingMigrationPreparationService,
)
from tools import prepare_role_binding_migration


# RBAC-TRANSITION-ONLY: Remove with the migration planner after evidence retention.
def _row(
    binding_id: str,
    *,
    user_id: str,
    role_id: str,
    role_name: str,
    allowed_scope: str,
    role_tenant_id: str | None = None,
    role_status: str = "active",
    organization_id: str | None = None,
    candidate_tenant_id: str | None = None,
    active_tenant_ids: list[str] | None = None,
    classification: str = "review_candidate",
) -> dict[str, object]:
    return {
        "binding_id": binding_id,
        "user_id": user_id,
        "role_id": role_id,
        "role_name": role_name,
        "role_tenant_id": role_tenant_id,
        "role_allowed_scope_type": allowed_scope,
        "role_status": role_status,
        "role_is_assignable": True,
        "organization_id": organization_id,
        "candidate_tenant_id": candidate_tenant_id,
        "active_tenant_ids": active_tenant_ids or [],
        "classification": classification,
    }


def _rows() -> list[dict[str, object]]:
    return [
        _row(
            "safe-platform",
            user_id="user-platform",
            role_id="role-platform",
            role_name="admin",
            allowed_scope="platform",
        ),
        _row(
            "safe-tenant",
            user_id="user-tenant",
            role_id="role-viewer",
            role_name="viewer",
            allowed_scope="tenant",
            candidate_tenant_id="tenant-a",
            active_tenant_ids=["tenant-a"],
        ),
        _row(
            "safe-organization",
            user_id="user-org",
            role_id="role-org",
            role_name="org_admin",
            allowed_scope="organization",
            organization_id="org-a",
            candidate_tenant_id="tenant-a",
            active_tenant_ids=["tenant-a"],
        ),
        _row(
            "ambiguous",
            user_id="user-multi",
            role_id="role-viewer",
            role_name="viewer",
            allowed_scope="tenant",
            active_tenant_ids=["tenant-a", "tenant-b"],
        ),
        _row(
            "cross-tenant",
            user_id="user-cross",
            role_id="role-org",
            role_name="org_admin",
            allowed_scope="organization",
            organization_id="org-b",
            candidate_tenant_id="tenant-b",
            active_tenant_ids=["tenant-a"],
        ),
        _row(
            "scope-mismatch",
            user_id="user-mismatch",
            role_id="role-viewer",
            role_name="viewer",
            allowed_scope="tenant",
            organization_id="org-a",
            candidate_tenant_id="tenant-a",
            active_tenant_ids=["tenant-a"],
        ),
        _row(
            "inactive",
            user_id="user-inactive",
            role_id="role-inactive",
            role_name="viewer",
            allowed_scope="tenant",
            role_status="retired",
            candidate_tenant_id="tenant-a",
            active_tenant_ids=["tenant-a"],
        ),
        _row(
            "duplicate-a",
            user_id="user-duplicate",
            role_id="role-viewer",
            role_name="viewer",
            allowed_scope="tenant",
            candidate_tenant_id="tenant-a",
            active_tenant_ids=["tenant-a"],
        ),
        _row(
            "duplicate-b",
            user_id="user-duplicate",
            role_id="role-viewer",
            role_name="viewer",
            allowed_scope="tenant",
            candidate_tenant_id="tenant-a",
            active_tenant_ids=["tenant-a"],
        ),
    ]


def _inventory(
    rows: list[dict[str, object]] | None = None,
    *,
    audit_count: int = 0,
) -> dict[str, object]:
    snapshot = {
        "database": {"dialect": "sqlite", "alembic_revisions": ["test"]},
        "schema": {"table_counts": {"audit_entries": audit_count}},
        "data": {"legacy_bindings": rows if rows is not None else _rows()},
        "findings": [],
        "finding_counts_by_severity": {},
    }
    serialized = json.dumps(
        snapshot,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "read_only": True,
        "snapshot_sha256": hashlib.sha256(serialized.encode("utf-8")).hexdigest(),
        "snapshot": snapshot,
    }


def _review(
    preview,
    *,
    reviewer_id: str = "security-reviewer",
    quarantine_ids: set[str] | None = None,
) -> RoleBindingMigrationReview:
    quarantined = quarantine_ids or set()
    decisions = tuple(
        RoleBindingMigrationReviewDecision(
            binding_id=proposal.source.binding_id,
            decision=(
                "quarantine"
                if proposal.source.binding_id in quarantined
                else "approve"
            ),
            reason_code=(
                "REVIEWER_REJECTED_SCOPE"
                if proposal.source.binding_id in quarantined
                else None
            ),
        )
        for proposal in preview.records
        if proposal.review_required
    )
    return RoleBindingMigrationReview(
        inventory_report_sha256=preview.inventory_report_sha256,
        source_inventory_sha256=preview.source_inventory_sha256,
        preview_sha256=preview.preview_sha256,
        reviewer_id=reviewer_id,
        reviewed_at=datetime.now(timezone.utc),
        decisions=decisions,
    )


def _plan(
    report: dict[str, object],
    *,
    reviewer_id: str = "security-reviewer",
    quarantine_ids: set[str] | None = None,
):
    preview = build_role_binding_migration_preview(report)
    return build_reviewed_role_binding_migration_plan(
        preview,
        _review(
            preview,
            reviewer_id=reviewer_id,
            quarantine_ids=quarantine_ids,
        ),
    )


def _service(session, services, report, *, audit_repo=None):
    return RoleBindingMigrationPreparationService(
        session=session,
        migration_repo=SqlAlchemyRoleBindingMigrationRepository(session),
        audit_repo=audit_repo or SqlAlchemyAuditRepository(session),
        user_session=services["user_session"],
        current_inventory_provider=lambda: report,
    )


def test_preview_only_allows_exact_inventory_derived_scopes() -> None:
    preview = build_role_binding_migration_preview(_inventory())
    proposals = {record.source.binding_id: record for record in preview.records}

    assert proposals["safe-platform"].proposed_scope == ProposedRoleScope(
        scope_type="platform"
    )
    assert proposals["safe-tenant"].proposed_scope == ProposedRoleScope(
        scope_type="tenant",
        tenant_id="tenant-a",
    )
    assert proposals["safe-organization"].proposed_scope == ProposedRoleScope(
        scope_type="organization",
        tenant_id="tenant-a",
        scope_id="org-a",
    )
    assert proposals["ambiguous"].quarantine_reason_code == "AMBIGUOUS_MULTI_TENANT"
    assert (
        proposals["cross-tenant"].quarantine_reason_code
        == "CROSS_TENANT_ORGANIZATION_BINDING"
    )
    assert proposals["scope-mismatch"].quarantine_reason_code == "ROLE_SCOPE_MISMATCH"
    assert proposals["inactive"].quarantine_reason_code == "ROLE_INACTIVE"
    assert proposals["duplicate-a"].quarantine_reason_code == "DUPLICATE_LEGACY_BINDING"
    assert proposals["duplicate-b"].quarantine_reason_code == "DUPLICATE_LEGACY_BINDING"


def test_source_hash_ignores_unrelated_report_counts_but_report_hash_does_not() -> None:
    first = build_role_binding_migration_preview(_inventory(audit_count=0))
    second = build_role_binding_migration_preview(_inventory(audit_count=9))

    assert first.inventory_report_sha256 != second.inventory_report_sha256
    assert first.source_inventory_sha256 == second.source_inventory_sha256
    assert first.preview_sha256 == second.preview_sha256


def test_tampered_inventory_and_incomplete_review_are_rejected() -> None:
    report = _inventory()
    report["snapshot"]["data"]["legacy_bindings"][0]["role_name"] = "changed"
    with pytest.raises(RoleBindingMigrationPlanError):
        build_role_binding_migration_preview(report)

    preview = build_role_binding_migration_preview(_inventory())
    review = _review(preview)
    incomplete = review.model_copy(update={"decisions": review.decisions[:-1]})
    with pytest.raises(RoleBindingMigrationPlanError):
        build_reviewed_role_binding_migration_plan(preview, incomplete)


def test_review_cannot_invent_a_scope_even_with_an_in_memory_model_copy() -> None:
    preview = build_role_binding_migration_preview(_inventory())
    plan = build_reviewed_role_binding_migration_plan(preview, _review(preview))
    index = next(
        index
        for index, record in enumerate(plan.records)
        if record.source.binding_id == "safe-tenant"
    )
    forged_record = plan.records[index].model_copy(
        update={"resolved_scope": ProposedRoleScope(scope_type="platform")}
    )
    forged_records = list(plan.records)
    forged_records[index] = forged_record
    forged_plan = plan.model_copy(update={"records": tuple(forged_records)})

    with pytest.raises(RoleBindingMigrationPlanError, match="not inventory-derived"):
        validate_reviewed_plan_against_preview(forged_plan, preview)


def test_preparation_is_atomic_audited_and_idempotent(session, services) -> None:
    report = _inventory()
    plan = _plan(report, quarantine_ids={"safe-organization"})
    service = _service(session, services, report)

    first = service.prepare(plan, expected_plan_sha256=plan.plan_sha256)
    second = service.prepare(plan, expected_plan_sha256=plan.plan_sha256)

    assert first.already_prepared is False
    assert second.already_prepared is True
    assert second.batch.id == first.batch.id
    assert len(first.records) == plan.record_count
    audit_rows = session.execute(
        select(AuditEntryORM).where(
            AuditEntryORM.operation == "authorization.migration.prepared"
        )
    ).scalars().all()
    assert len(audit_rows) == 1
    assert audit_rows[0].tenant_id is None
    assert audit_rows[0].organization_id is None
    assert (
        json.loads(audit_rows[0].metadata_json)["reviewed_plan_sha256"]
        == plan.plan_sha256
    )


def test_preparation_rejects_self_review_hash_mismatch_and_plan_conflict(
    session,
    services,
) -> None:
    report = _inventory()
    principal = services["user_session"].principal
    self_reviewed = _plan(report, reviewer_id=principal.username)
    service = _service(session, services, report)

    with pytest.raises(BusinessRuleError) as self_review_error:
        service.prepare(
            self_reviewed,
            expected_plan_sha256=self_reviewed.plan_sha256,
        )
    assert self_review_error.value.code == "AUTH_MIGRATION_INDEPENDENT_REVIEW_REQUIRED"

    first = _plan(report, reviewer_id="reviewer-one")
    with pytest.raises(BusinessRuleError) as hash_error:
        service.prepare(first, expected_plan_sha256="0" * 64)
    assert hash_error.value.code == "AUTH_MIGRATION_PLAN_HASH_MISMATCH"
    service.prepare(first, expected_plan_sha256=first.plan_sha256)

    conflicting = _plan(
        report,
        reviewer_id="reviewer-two",
        quarantine_ids={"safe-tenant"},
    )
    with pytest.raises(BusinessRuleError) as conflict_error:
        service.prepare(conflicting, expected_plan_sha256=conflicting.plan_sha256)
    assert conflict_error.value.code == "AUTH_MIGRATION_PLAN_CONFLICT"


def test_idempotent_retry_rejects_tampered_persisted_evidence(
    session,
    services,
) -> None:
    report = _inventory()
    plan = _plan(report)
    service = _service(session, services, report)
    result = service.prepare(plan, expected_plan_sha256=plan.plan_sha256)
    row = session.execute(
        select(LegacyRoleBindingMigrationRecordORM).where(
            LegacyRoleBindingMigrationRecordORM.batch_id == result.batch.id
        )
    ).scalars().first()
    row.reviewed_by = "tampered-reviewer"
    session.commit()

    with pytest.raises(BusinessRuleError) as mismatch_error:
        service.prepare(plan, expected_plan_sha256=plan.plan_sha256)
    assert mismatch_error.value.code == "AUTH_MIGRATION_EVIDENCE_MISMATCH"


def test_live_source_drift_and_audit_failure_do_not_persist_evidence(
    session,
    services,
) -> None:
    report = _inventory()
    plan = _plan(report)
    changed_rows = _rows()
    changed_rows[1] = {**changed_rows[1], "active_tenant_ids": ["tenant-b"]}
    drifted_report = _inventory(changed_rows)

    with pytest.raises(BusinessRuleError) as drift_error:
        _service(session, services, drifted_report).prepare(
            plan,
            expected_plan_sha256=plan.plan_sha256,
        )
    assert drift_error.value.code == "AUTH_MIGRATION_SOURCE_DRIFT"

    failing_audit = Mock()
    failing_audit.add_platform.side_effect = RuntimeError("audit unavailable")
    with pytest.raises(RuntimeError, match="audit unavailable"):
        _service(
            session,
            services,
            report,
            audit_repo=failing_audit,
        ).prepare(plan, expected_plan_sha256=plan.plan_sha256)
    repository = SqlAlchemyRoleBindingMigrationRepository(session)
    assert repository.get_batch_by_inventory_sha256(
        plan.source_inventory_sha256
    ) is None


def test_cli_builds_exclusive_preview_and_reviewed_plan_artifacts(tmp_path) -> None:
    inventory_path = tmp_path / "inventory.json"
    preview_path = tmp_path / "preview.json"
    review_path = tmp_path / "review.json"
    plan_path = tmp_path / "reviewed-plan.json"
    inventory_path.write_text(json.dumps(_inventory()), encoding="utf-8")

    assert prepare_role_binding_migration.main(
        [
            "--inventory",
            str(inventory_path),
            "--output",
            str(preview_path),
        ]
    ) == 0
    preview_payload = json.loads(preview_path.read_text(encoding="utf-8"))
    preview = build_role_binding_migration_preview(_inventory())
    assert preview_payload["preview_sha256"] == preview.preview_sha256
    review_path.write_text(
        _review(preview).model_dump_json(indent=2),
        encoding="utf-8",
    )

    assert prepare_role_binding_migration.main(
        [
            "--inventory",
            str(inventory_path),
            "--review",
            str(review_path),
            "--output",
            str(plan_path),
        ]
    ) == 0
    plan_payload = json.loads(plan_path.read_text(encoding="utf-8"))
    assert len(plan_payload["plan_sha256"]) == 64
    assert plan_payload["record_count"] == len(_rows())

    with pytest.raises(SystemExit) as duplicate_output:
        prepare_role_binding_migration.main(
            [
                "--inventory",
                str(inventory_path),
                "--output",
                str(preview_path),
            ]
        )
    assert duplicate_output.value.code == 2

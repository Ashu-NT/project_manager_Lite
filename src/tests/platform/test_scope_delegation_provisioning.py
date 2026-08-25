"""Tests for the reviewed resource-scope delegation provisioning tool.

Covers:
  1. preview() reports the code-owned catalog against current DB state
  2. apply() creates the missing policies and is idempotent
  3. apply() rejects a stale (changed) catalog hash
  4. apply() rejects a catalog referencing an undefined role
"""
from __future__ import annotations

import pytest

from src.core.platform.application.security.authorization.roles import (
    DEFAULT_SCOPE_DELEGATIONS,
    ScopeDelegationProvisioningService,
)
from src.core.platform.common.exceptions import BusinessRuleError
from src.core.platform.infrastructure.persistence.repositories.security.auth.auth import (
    SqlAlchemyRoleDelegationPolicyRepository,
)


def _service(services) -> ScopeDelegationProvisioningService:
    auth = services["auth_service"]
    role_governance_service = services["role_governance_service"]
    return ScopeDelegationProvisioningService(
        role_repo=auth._role_repo,
        delegation_repo=SqlAlchemyRoleDelegationPolicyRepository(services["session"]),
        role_governance_service=role_governance_service,
    )


def test_preview_reports_full_catalog_with_no_missing_roles(services) -> None:
    plan = _service(services).preview()

    assert not plan.missing_role_names
    assert len(plan.entries) == len(DEFAULT_SCOPE_DELEGATIONS)
    assert plan.has_changes


def test_apply_creates_missing_policies_and_is_idempotent(services) -> None:
    service = _service(services)
    plan = service.preview()
    assert plan.has_changes

    result = service.apply(expected_catalog_hash=plan.catalog_hash)

    assert len(result.created) == len(plan.pending_entries)
    assert result.catalog_hash == plan.catalog_hash

    second_plan = service.preview()
    assert not second_plan.has_changes
    assert all(entry.exists for entry in second_plan.entries)


def test_apply_rejects_stale_catalog_hash(services) -> None:
    service = _service(services)

    with pytest.raises(BusinessRuleError) as exc_info:
        service.apply(expected_catalog_hash="stale-hash-from-an-old-preview")

    assert exc_info.value.code == "SCOPE_DELEGATION_CATALOG_HASH_MISMATCH"


def test_apply_rejects_catalog_with_undefined_role(services) -> None:
    service = _service(services)
    bad_catalog = (("access_admin", "project_nonexistent_role", "project"),)

    plan = service.preview(bad_catalog)
    assert "project_nonexistent_role" in plan.missing_role_names

    with pytest.raises(BusinessRuleError) as exc_info:
        service.apply(expected_catalog_hash=plan.catalog_hash, catalog=bad_catalog)

    assert exc_info.value.code == "SCOPE_DELEGATION_ROLE_MISSING"

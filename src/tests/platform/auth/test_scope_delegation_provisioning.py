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
    ScopeDelegationProvisioningCommandHandler,
    ScopeDelegationProvisioningQueryHandler,
)
from src.core.platform.application.security.authorization.roles._scope_delegation import (
    DEFAULT_SCOPE_DELEGATIONS,
)
from src.core.platform.common.exceptions import BusinessRuleError
from src.core.platform.infrastructure.persistence.repositories.security.auth.auth import (
    SqlAlchemyRoleDelegationPolicyRepository,
)


def _handlers(services):
    role_governance_commands = services["role_governance_commands"]
    queries = ScopeDelegationProvisioningQueryHandler(
        role_repo=services["auth_queries"]._role_repo,
        delegation_repo=SqlAlchemyRoleDelegationPolicyRepository(services["session"]),
    )
    commands = ScopeDelegationProvisioningCommandHandler(
        role_repo=services["auth_queries"]._role_repo,
        queries=queries,
        role_governance_commands=role_governance_commands,
    )
    return commands, queries


def test_preview_reports_full_catalog_with_no_missing_roles(services) -> None:
    plan = _handlers(services)[1].preview()

    assert not plan.missing_role_names
    assert len(plan.entries) == len(DEFAULT_SCOPE_DELEGATIONS)
    assert plan.has_changes


def test_apply_creates_missing_policies_and_is_idempotent(services) -> None:
    commands, queries = _handlers(services)
    plan = queries.preview()
    assert plan.has_changes

    result = commands.apply(expected_catalog_hash=plan.catalog_hash)

    assert len(result.created) == len(plan.pending_entries)
    assert result.catalog_hash == plan.catalog_hash

    second_plan = queries.preview()
    assert not second_plan.has_changes
    assert all(entry.exists for entry in second_plan.entries)


def test_apply_rejects_stale_catalog_hash(services) -> None:
    commands, queries = _handlers(services)

    with pytest.raises(BusinessRuleError) as exc_info:
        commands.apply(expected_catalog_hash="stale-hash-from-an-old-preview")

    assert exc_info.value.code == "SCOPE_DELEGATION_CATALOG_HASH_MISMATCH"


def test_apply_rejects_catalog_with_undefined_role(services) -> None:
    commands, queries = _handlers(services)
    bad_catalog = (("access_admin", "project_nonexistent_role", "project"),)

    plan = queries.preview(bad_catalog)
    assert "project_nonexistent_role" in plan.missing_role_names

    with pytest.raises(BusinessRuleError) as exc_info:
        commands.apply(expected_catalog_hash=plan.catalog_hash, catalog=bad_catalog)

    assert exc_info.value.code == "SCOPE_DELEGATION_ROLE_MISSING"

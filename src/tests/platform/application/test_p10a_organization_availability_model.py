"""Multi-organization availability model: `Organization.status` (ACTIVE/INACTIVE/ARCHIVED) is
independent per-organization availability, with no mutual-exclusion invariant against sibling
organizations. Multiple organizations may be ACTIVE per tenant simultaneously; per-user session
selection (`TenantContextService.set_active_organization`) is independent of that lifecycle status.
`activate_organization`/`deactivate_organization`/`archive_organization` are lifecycle-only,
single-row mutations.

This module holds:
  1. structural guards proving the legacy sibling-mutual-exclusion machinery is gone and stays gone;
  2. structural guards proving `TenantContextService.set_active_organization`/
     `UserSessionContext.active_organization_id` remain canonical and untouched;
  3. behavioral characterization of the multi-org model end to end (two organizations enabled
     simultaneously, independent per-session selection, a disabled organization rejected at
     switch time).
"""

from __future__ import annotations

import dataclasses
import glob
import inspect

import pytest

from src.core.platform.application.master_data.org import (
    organization_service as organization_service_module,
)
from src.core.platform.application.master_data.org.organization_service import (
    OrganizationService,
)
from src.core.platform.application.tenant.tenancy.tenant_context import (
    TenantContextService,
)
from src.core.platform.common.exceptions import BusinessRuleError
from src.core.platform.contract.repositories.master_data.org.contracts import (
    OrganizationRepository,
)
from src.core.platform.domain.master_data.org import (
    ORGANIZATION_STATUS_ACTIVE,
    ORGANIZATION_STATUS_INACTIVE,
    Organization,
)
from src.core.platform.domain.security.auth.session import (
    UserSessionContext,
    UserSessionPrincipal,
)

_COUNTER = {"n": 0}


def _unique_code(prefix: str) -> str:
    _COUNTER["n"] += 1
    return f"{prefix}-{_COUNTER['n']}"


def _strip_strings_and_comments(source: str) -> str:
    import re

    no_docstrings = re.sub(r'"""[\s\S]*?"""', "", source)
    no_comments = re.sub(r"#.*", "", no_docstrings)
    return no_comments


def _production_source_files():
    for path in glob.glob("src/**/*.py", recursive=True):
        normalized = path.replace("\\", "/")
        if "__pycache__" in normalized or "/tests/" in normalized:
            continue
        yield normalized


# ---------------------------------------------------------------------------
# 1. Structural guards: the legacy mutual-exclusion machinery is gone.
# ---------------------------------------------------------------------------


def test_organization_service_has_no_set_active_organization_method():
    assert not hasattr(OrganizationService, "set_active_organization")


def test_organization_service_has_no_get_active_organization_method():
    """`OrganizationService.get_active_organization()` (a singular-designee lookup superseded by
    `TenantContextService.get_active_organization()`) is deleted, not kept as unused dead code."""
    assert not hasattr(OrganizationService, "get_active_organization")


def test_organization_service_has_no_sibling_deactivation_helpers():
    for legacy_name in (
        "_deactivate_other_organizations",
        "_deactivate_other_organizations_using",
        "_has_other_active_organizations_using",
        "_activate_organization_using",
    ):
        assert not hasattr(OrganizationService, legacy_name), (
            f"{legacy_name} is legacy mutual-exclusion machinery and must not exist, "
            "renamed or otherwise"
        )


def test_organization_service_has_activate_deactivate_archive_organization_methods():
    assert hasattr(OrganizationService, "activate_organization")
    assert hasattr(OrganizationService, "deactivate_organization")
    assert hasattr(OrganizationService, "archive_organization")
    assert hasattr(OrganizationService, "_transition_organization_status")


def test_organization_repository_contract_has_no_singular_active_lookup():
    """`get_active()` (unscoped, dead) and `get_active_for_tenant()` ("the one active org for a
    tenant") both represented the deleted singular-designation concept."""
    for legacy_name in ("get_active", "get_active_for_tenant"):
        assert not hasattr(OrganizationRepository, legacy_name)


def test_organization_domain_field_is_status_not_is_enabled():
    field_names = {f.name for f in dataclasses.fields(Organization)}
    assert "status" in field_names
    assert "is_enabled" not in field_names
    assert "is_active" not in field_names


def test_no_mutual_exclusion_vocabulary_remains_in_organization_service_source():
    source = _strip_strings_and_comments(inspect.getsource(organization_service_module))
    for forbidden in (
        "ORGANIZATION_ACTIVE_REQUIRED",
        "_deactivate_other_organizations",
        "_has_other_active_organizations",
        "at least one active organization",
    ):
        assert forbidden not in source, f"legacy mutual-exclusion vocabulary found: {forbidden!r}"


def test_no_organization_repository_implementation_still_defines_active_only_or_enabled_only_param():
    """Neither `active_only` nor `enabled_only` must survive as a repository filter kwarg name on
    any Organization repository -- the correct name is `status`."""
    import re

    for path in _production_source_files():
        if not path.endswith("infrastructure/persistence/repositories/master_data/org/org.py"):
            continue
        with open(path, encoding="utf-8") as handle:
            source = handle.read()
        assert "active_only" not in source
        assert "enabled_only" not in source
        assert re.search(r"def list_all\(self, \*, status", source)
        assert re.search(r"def list_for_tenant\(self, tenant_id: str, \*, status", source)


# ---------------------------------------------------------------------------
# 2. Structural guards: the canonical session-selection mechanism is untouched.
# ---------------------------------------------------------------------------


def test_tenant_context_service_set_active_organization_remains_the_canonical_selector():
    assert hasattr(TenantContextService, "set_active_organization")
    assert hasattr(TenantContextService, "_set_active_organization")


def test_user_session_context_active_organization_id_remains_untouched():
    assert hasattr(UserSessionContext, "active_organization_id")
    assert hasattr(UserSessionContext, "set_active_organization_id")


def test_tenant_context_service_switch_checks_status_not_is_enabled():
    source = inspect.getsource(TenantContextService._set_active_organization)
    assert "status" in source
    assert "is_enabled" not in source
    assert "is_active" not in source


# ---------------------------------------------------------------------------
# 3. Behavioral characterization of the corrected model.
# ---------------------------------------------------------------------------


def test_creating_organization_b_does_not_disable_organization_a(services):
    organization_service = services["organization_service"]
    org_a = organization_service.create_organization(
        organization_code=_unique_code("MULTI-A"), display_name="Multi Org A"
    )
    org_b = organization_service.create_organization(
        organization_code=_unique_code("MULTI-B"), display_name="Multi Org B"
    )
    org_c = organization_service.create_organization(
        organization_code=_unique_code("MULTI-C"), display_name="Multi Org C"
    )

    reloaded = {
        org.id: org.status
        for org in organization_service.list_organizations()
    }
    assert reloaded[org_a.id] == ORGANIZATION_STATUS_ACTIVE
    assert reloaded[org_b.id] == ORGANIZATION_STATUS_ACTIVE
    assert reloaded[org_c.id] == ORGANIZATION_STATUS_ACTIVE


def test_disabled_organization_cannot_be_selected_but_others_remain_unaffected(services):
    organization_service = services["organization_service"]
    tenant_context_service = services["tenant_context_service"]

    org_a = organization_service.create_organization(
        organization_code=_unique_code("DISABLED-A"), display_name="Disabled Test A"
    )
    org_b = organization_service.create_organization(
        organization_code=_unique_code("DISABLED-B"), display_name="Disabled Test B"
    )
    org_b = organization_service.deactivate_organization(org_b.id)

    with pytest.raises(BusinessRuleError):
        tenant_context_service.set_active_organization(org_b.id)

    # The denied switch must not have mutated either organization's row.
    reloaded_a = organization_service._organization_repo.get(org_a.id)
    reloaded_b = organization_service._organization_repo.get(org_b.id)
    assert reloaded_a.status == ORGANIZATION_STATUS_ACTIVE
    assert reloaded_b.status == ORGANIZATION_STATUS_INACTIVE


def test_independent_sessions_select_different_organizations_simultaneously(services):
    """Two users, both with access to two organizations in the same tenant, may have their own
    sessions independently pointed at different organizations at the same time."""
    organization_service = services["organization_service"]
    real_tenant_context_service = services["tenant_context_service"]
    tenant_id = real_tenant_context_service.get_active_tenant_id()

    org_a = organization_service.create_organization(
        organization_code=_unique_code("TWOUSER-A"), display_name="Two-User Org A"
    )
    org_b = organization_service.create_organization(
        organization_code=_unique_code("TWOUSER-B"), display_name="Two-User Org B"
    )

    def _build_session_for(user_id: str) -> tuple[UserSessionContext, TenantContextService]:
        ctx = UserSessionContext()
        ctx.set_principal(
            UserSessionPrincipal(
                user_id=user_id,
                username=user_id,
                display_name=user_id,
                role_names=frozenset(["admin"]),
                permissions=frozenset(["settings.manage"]),
            )
        )
        ctx.set_active_tenant_id(tenant_id)
        tenant_context = TenantContextService(
            tenant_repo=real_tenant_context_service._tenant_repo,
            organization_repo=real_tenant_context_service._organization_repo,
            user_session=ctx,
            user_tenant_repo=real_tenant_context_service._user_tenant_repo,
            context_policy=real_tenant_context_service._context_policy,
        )
        return ctx, tenant_context

    alice_session, alice_context = _build_session_for("p10a-alice")
    bob_session, bob_context = _build_session_for("p10a-bob")

    alice_context.set_active_organization(org_a.id)
    bob_context.set_active_organization(org_b.id)

    assert alice_context.get_active_organization_id() == org_a.id
    assert bob_context.get_active_organization_id() == org_b.id

    # Bob selecting Org B must not have changed Alice's own session selection, and neither
    # selection touched any Organization row's availability.
    assert alice_context.get_active_organization_id() == org_a.id
    reloaded_a = organization_service._organization_repo.get(org_a.id)
    reloaded_b = organization_service._organization_repo.get(org_b.id)
    assert reloaded_a.status == ORGANIZATION_STATUS_ACTIVE
    assert reloaded_b.status == ORGANIZATION_STATUS_ACTIVE


def test_activating_organization_never_switches_any_session_context(services):
    """Availability and session selection are fully decoupled -- activating an organization must
    never, as a side effect, change what any session's current organization is."""
    organization_service = services["organization_service"]
    tenant_context_service = services["tenant_context_service"]

    before_id = tenant_context_service.get_active_organization_id()

    newly_created = organization_service.create_organization(
        organization_code=_unique_code("NOSIDEEFFECT"),
        display_name="No Side Effect Org",
    )
    organization_service.deactivate_organization(newly_created.id)
    organization_service.activate_organization(newly_created.id)

    assert tenant_context_service.get_active_organization_id() == before_id

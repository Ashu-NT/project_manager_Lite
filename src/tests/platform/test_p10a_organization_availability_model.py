"""P10A (Multi-Organization Domain-Model Correction): `Organization.is_active` carried legacy
single-organization mutual-exclusion designation semantics -- application code enforced "at most
one organization is_active=True per tenant" and coupled that persisted flag to session context
selection. P9B's SaaS-readiness audit established the domain/authorization architecture already
supports multiple organizations per tenant, multiple organizations per user
(`RoleBinding(actual_scope_type="organization")` -> `Principal.scoped_access["organization"]`),
and independent per-user session selection (`TenantContextService.set_active_organization`) --
the ONLY defect was `Organization.is_active`'s mutual-exclusion behavior.

P10A renamed the field to `is_enabled` (independent per-organization availability, no invariant
against siblings), deleted the sibling-deactivation machinery and
`OrganizationService.set_active_organization` (its persisted-designation half; its session-switch
half was always `TenantContextService.set_active_organization`'s own job), and added
`enable_organization`/`disable_organization` (availability-only, single-row mutations).

This module holds:
  1. structural guards proving the legacy mutual-exclusion machinery is gone and stays gone;
  2. structural guards proving `TenantContextService.set_active_organization`/
     `UserSessionContext.active_organization_id` remain canonical and untouched;
  3. behavioral characterization of the corrected multi-org model end to end (two organizations
     enabled simultaneously, independent per-session selection, a disabled organization rejected
     at switch time) that the P10A governing spec's own test matrix requires and which no other
     test file covers.
"""

from __future__ import annotations

import dataclasses
import glob
import inspect

import pytest

from src.core.platform.application.master_data.org import organization_service as organization_service_module
from src.core.platform.application.master_data.org.organization_service import OrganizationService
from src.core.platform.application.tenant.tenancy.tenant_context import TenantContextService
from src.core.platform.common.exceptions import BusinessRuleError
from src.core.platform.contract.repositories.master_data.org.contracts import OrganizationRepository
from src.core.platform.domain.master_data.org import Organization
from src.core.platform.domain.security.auth.session import UserSessionContext, UserSessionPrincipal

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
    """P10A: `OrganizationService.get_active_organization()` was the singular-designee lookup --
    dead code even before P10A (the real runtime path already used
    `TenantContextService.get_active_organization()`), and deleted rather than kept as an unused
    legacy concept."""
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


def test_organization_service_has_enable_and_disable_organization_methods():
    assert hasattr(OrganizationService, "enable_organization")
    assert hasattr(OrganizationService, "disable_organization")
    assert hasattr(OrganizationService, "_enable_organization_using")


def test_organization_repository_contract_has_no_singular_active_lookup():
    """`get_active()` (unscoped, dead) and `get_active_for_tenant()` ("the one active org for a
    tenant") both represented the deleted singular-designation concept."""
    for legacy_name in ("get_active", "get_active_for_tenant"):
        assert not hasattr(OrganizationRepository, legacy_name)


def test_organization_domain_field_is_is_enabled_not_is_active():
    field_names = {f.name for f in dataclasses.fields(Organization)}
    assert "is_enabled" in field_names
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


def test_no_organization_repository_implementation_still_defines_active_only_param():
    """`active_only` (the pre-P10A repository filter kwarg name) must not survive under its old
    name on any Organization repository -- the corrected name is `enabled_only`."""
    import re

    for path in _production_source_files():
        if not path.endswith("infrastructure/persistence/repositories/master_data/org/org.py"):
            continue
        with open(path, encoding="utf-8") as handle:
            source = handle.read()
        assert "active_only" not in source
        assert re.search(r"def list_(all|for_tenant)\(self, \*, enabled_only", source)


# ---------------------------------------------------------------------------
# 2. Structural guards: the canonical session-selection mechanism is untouched.
# ---------------------------------------------------------------------------


def test_tenant_context_service_set_active_organization_remains_the_canonical_selector():
    assert hasattr(TenantContextService, "set_active_organization")
    assert hasattr(TenantContextService, "_set_active_organization")


def test_user_session_context_active_organization_id_remains_untouched():
    assert hasattr(UserSessionContext, "active_organization_id")
    assert hasattr(UserSessionContext, "set_active_organization_id")


def test_tenant_context_service_switch_checks_is_enabled_not_is_active():
    source = inspect.getsource(TenantContextService._set_active_organization)
    assert "is_enabled" in source
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
        org.id: org.is_enabled
        for org in organization_service.list_organizations()
    }
    assert reloaded[org_a.id] is True
    assert reloaded[org_b.id] is True
    assert reloaded[org_c.id] is True


def test_disabled_organization_cannot_be_selected_but_others_remain_unaffected(services):
    organization_service = services["organization_service"]
    tenant_context_service = services["tenant_context_service"]

    org_a = organization_service.create_organization(
        organization_code=_unique_code("DISABLED-A"), display_name="Disabled Test A"
    )
    org_b = organization_service.create_organization(
        organization_code=_unique_code("DISABLED-B"), display_name="Disabled Test B", is_enabled=False
    )

    with pytest.raises(BusinessRuleError):
        tenant_context_service.set_active_organization(org_b.id)

    # The denied switch must not have mutated either organization's row.
    reloaded_a = organization_service._organization_repo.get(org_a.id)
    reloaded_b = organization_service._organization_repo.get(org_b.id)
    assert reloaded_a.is_enabled is True
    assert reloaded_b.is_enabled is False


def test_independent_sessions_select_different_organizations_simultaneously(services):
    """P10A section 14 (TWO-USER MODEL): two users, both with access to two organizations in the
    same tenant, may have their own sessions independently pointed at different organizations at
    the same time -- proving the domain/session architecture, not desktop multi-window UI."""
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
    assert reloaded_a.is_enabled is True
    assert reloaded_b.is_enabled is True


def test_enabling_organization_never_switches_any_session_context(services):
    """P10A: availability and session selection are fully decoupled -- enabling an organization
    must never, as a side effect, change what any session's current organization is."""
    organization_service = services["organization_service"]
    tenant_context_service = services["tenant_context_service"]

    before_id = tenant_context_service.get_active_organization_id()

    newly_enabled = organization_service.create_organization(
        organization_code=_unique_code("NOSIDEEFFECT"),
        display_name="No Side Effect Org",
        is_enabled=False,
    )
    organization_service.enable_organization(newly_enabled.id)

    assert tenant_context_service.get_active_organization_id() == before_id

"""P10B: architecture guards for organization-scoped access assignment.

Organization is now a selectable Access Workspace scope type (see
`test_platform_access_scopes.py`'s `test_access_service_supports_organization_scope_grants_and_
principal_hydration` and `test_platform_control_desktop_api.py`'s
`test_build_desktop_api_registry_exposes_organization_as_an_access_scope_type` for the positive
behavioral proof). These guards protect the specific constraints the governing spec called out:
no new user<->organization persistence model, no parallel authorization path around
RoleGovernance, and no UI-layer repository/ORM leakage in the Access Workspace surface.
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path

import src.core.platform.access.application.access_control_service as access_control_service_module
from src.core.platform.access.application.access_control_service import AccessControlService

_REPO_ROOT = Path(__file__).resolve().parents[3]
_FORBIDDEN_MODEL_NAMES = frozenset({"OrganizationUser", "UserOrganization", "OrganizationMembership"})


def _iter_source_files(*relative_dirs: str):
    for relative_dir in relative_dirs:
        base = _REPO_ROOT / relative_dir
        yield from base.rglob("*.py")


def test_no_new_user_organization_persistence_model_was_introduced():
    """P10B explicitly forbids a parallel `OrganizationUser`/`UserOrganization`/
    `OrganizationMembership` table -- organization access must stay RoleBinding-based."""
    offenders: list[str] = []
    for path in _iter_source_files("src/core", "src/infra"):
        try:
            source = path.read_text(encoding="utf-8-sig")
        except (UnicodeDecodeError, OSError):
            continue
        try:
            tree = ast.parse(source, filename=str(path))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name in _FORBIDDEN_MODEL_NAMES:
                offenders.append(f"{path.relative_to(_REPO_ROOT)}:{node.lineno} class {node.name}")
    assert offenders == [], f"Found forbidden parallel access-persistence model(s): {offenders}"


def test_organization_scope_grants_route_through_role_governance_not_a_parallel_path():
    """`AccessControlService._assign_canonical_scope_grant`/`_remove_canonical_scope_grant` are
    the ONLY methods that mutate a canonical (project/site/storeroom/organization) scope grant,
    and both are structurally required to go through `RoleGovernanceService.assign_role`/
    `revoke_role_binding` -- there is no alternate organization-specific write path."""
    assign_source = inspect.getsource(AccessControlService._assign_canonical_scope_grant)
    remove_source = inspect.getsource(AccessControlService._remove_canonical_scope_grant)
    assert "role_governance_service.assign_role(" in assign_source
    assert "role_governance_service.revoke_role_binding(" in remove_source
    # "organization" must not bypass this shared method with its own branch.
    module_source = inspect.getsource(access_control_service_module)
    assert "if scope_type == \"organization\"" not in module_source
    assert "if normalized_scope_type == \"organization\"" not in module_source


def test_organization_is_a_canonical_scope_type_not_a_special_case():
    """`organization` must be a member of the same generic `_CANONICAL_SCOPE_TYPES` allowlist
    project/site/storeroom already use, not a separately-branched code path."""
    canonical_scope_types = access_control_service_module._CANONICAL_SCOPE_TYPES
    assert canonical_scope_types == frozenset({"organization", "project", "site", "storeroom"})


def test_access_workspace_presenter_and_controller_do_not_import_repositories_or_orm():
    """The Access Workspace presenter/controller stay desktop-API-only -- P10B added no new
    scope-type-specific code there (the layer was already scope-type-agnostic), so this guard
    simply confirms that remains true."""
    presenter_path = (
        _REPO_ROOT
        / "src/ui_qml/platform/presenters/identity_access/access/access_workspace_presenter.py"
    )
    controller_path = (
        _REPO_ROOT
        / "src/ui_qml/platform/controllers/identity_access/access/access_workspace_controller.py"
    )
    for path in (presenter_path, controller_path):
        source = path.read_text(encoding="utf-8-sig")
        assert "repositories" not in source, f"{path} must not import repositories"
        assert "sqlalchemy" not in source.lower(), f"{path} must not import ORM/SQLAlchemy"
        assert ".access_policy import" not in source, (
            f"{path} must stay scope-type-agnostic -- it must not import a specific scope's "
            "access policy module directly"
        )


def test_organization_access_policy_role_choices_map_to_pre_existing_system_roles():
    """`ORGANIZATION_SCOPE_ROLE_CANONICAL_NAMES` must resolve to the pre-existing `org_admin`/
    `org_viewer`/`org_member` system roles (see `role_scope_policy.py`'s
    `_ORGANIZATION_SCOPE_ROLE_NAMES`) -- P10B must not invent new organization role names."""
    from src.core.platform.domain.master_data.org.access_policy import (
        ORGANIZATION_SCOPE_ROLE_CANONICAL_NAMES,
        ORGANIZATION_SCOPE_ROLE_CHOICES,
    )
    from src.core.platform.application.security.authorization.roles.role_scope_policy import (
        _ORGANIZATION_SCOPE_ROLE_NAMES,
    )

    assert set(ORGANIZATION_SCOPE_ROLE_CANONICAL_NAMES.keys()) == set(ORGANIZATION_SCOPE_ROLE_CHOICES)
    assert set(ORGANIZATION_SCOPE_ROLE_CANONICAL_NAMES.values()) == set(_ORGANIZATION_SCOPE_ROLE_NAMES)

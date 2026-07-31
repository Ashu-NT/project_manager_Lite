from __future__ import annotations

# RBAC-TRANSITION-ONLY: Delete this guardrail after the final registered
# transition component is removed.

from src.tests.path_rewrites import REPO_ROOT


_MARKER = "RBAC-TRANSITION-ONLY"
_REGISTER = "### Transition-code decommission register"
_TRANSITION_COMPONENT_PATHS = (
    "docs/tenancy_rbac_hardening/ADR-003_OPERATIONAL_EVIDENCE.md",
    "src/core/platform/auth/application/auth_query.py",
    "src/core/platform/auth/application/principal_builder.py",
    "src/core/platform/auth/application/registration_service.py",
    "src/core/platform/auth/application/role_assignment_service.py",
    "src/core/platform/auth/contracts/__init__.py",
    "src/core/platform/auth/contracts/auth_repository.py",
    "src/core/platform/auth/domain/__init__.py",
    "src/core/platform/auth/domain/role_binding_migration.py",
    "src/core/platform/auth/domain/user.py",
    "src/core/platform/infrastructure/persistence/mappers/auth.py",
    "src/core/platform/infrastructure/persistence/orm/auth.py",
    "src/core/platform/infrastructure/persistence/repositories/auth.py",
    "src/core/platform/tenancy/application/tenant_membership_service.py",
    "src/infra/composition/repositories.py",
    "src/infra/platform/security_config.py",
    "src/infra/security/__init__.py",
    "src/infra/security/authorization_transition_evidence.py",
    "src/tests/architecture/test_rbac_transition_decommission.py",
    "src/tests/platform/test_authorization_transition_evidence.py",
    "src/tests/platform/test_role_binding_migration_foundation.py",
    "src/tests/platform/test_role_policy_reconciliation_cli_evidence.py",
    "tools/verify_authorization_transition_evidence.py",
)


def test_rbac_transition_components_remain_marked_for_decommission() -> None:
    missing_files: list[str] = []
    missing_markers: list[str] = []
    for relative_path in _TRANSITION_COMPONENT_PATHS:
        path = REPO_ROOT / relative_path
        if not path.is_file():
            missing_files.append(relative_path)
            continue
        if _MARKER not in path.read_text(encoding="utf-8"):
            missing_markers.append(relative_path)

    assert not missing_files, (
        "Update the RBAC transition registry when deleting components: "
        f"{missing_files}"
    )
    assert not missing_markers, (
        "Transition components lost their decommission marker: "
        f"{missing_markers}"
    )


def test_rbac_transition_decommission_register_remains_documented() -> None:
    readme = (
        REPO_ROOT / "docs/tenancy_rbac_hardening/README.md"
    ).read_text(encoding="utf-8")

    assert _REGISTER in readme
    assert "`RBAC-TRANSITION-ONLY`" in readme
    assert "Applied Alembic revision files are immutable" in readme

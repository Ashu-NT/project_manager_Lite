from __future__ import annotations

from pathlib import Path


PM_REPOSITORIES = Path(
    "src/core/modules/project_management/infrastructure/persistence/repositories"
)
SHARED_SCOPE_SUPPORT = Path(
    "src/core/platform/infrastructure/persistence/repositories/_tenant_scope.py"
)


def test_pm_repositories_do_not_hydrate_full_tenant_or_organization_entities() -> None:
    offenders = [
        path.as_posix()
        for path in PM_REPOSITORIES.rglob("*.py")
        if "require_organization_context(" in path.read_text(encoding="utf-8")
    ]

    assert offenders == []


def test_full_entity_context_contract_remains_available_for_genuine_consumers() -> None:
    source = SHARED_SCOPE_SUPPORT.read_text(encoding="utf-8")

    assert "def _context(self, *, operation_label: str) -> ActiveScopeIds:" in source
    assert "def _tenant_context(self, *, operation_label: str) -> TenantContext:" in source
    assert "require_active_scope_ids(" in source
    assert "require_context(" in source

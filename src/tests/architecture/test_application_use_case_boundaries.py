"""Business use cases must not depend on desktop or HTTP adapters."""

import ast
from pathlib import Path

from src.core.platform.contract.use_cases.platform_runtime import (
    RuntimeEntitlementFact,
    RuntimeModuleFact,
)
from src.core.platform.domain.tenant.modules import EnterpriseModule, ModuleEntitlement

SRC_ROOT = Path(__file__).resolve().parents[2] / "core"
BUSINESS_ROOTS = (
    SRC_ROOT / "platform/application",
    SRC_ROOT / "platform/contract",
    SRC_ROOT / "modules/project_management/application",
    SRC_ROOT / "modules/project_management/contracts",
)


def test_application_and_contract_packages_do_not_import_api_adapters() -> None:
    violations: list[str] = []
    for root in BUSINESS_ROOTS:
        for path in root.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    imports = (node.module or "",)
                elif isinstance(node, ast.Import):
                    imports = tuple(alias.name for alias in node.names)
                else:
                    continue
                for imported in imports:
                    if imported.startswith("src.core.") and ".api." in imported:
                        violations.append(f"{path.relative_to(SRC_ROOT)}:{node.lineno}: {imported}")
    assert not violations, "\n".join(violations)


def test_runtime_use_case_facts_do_not_contain_domain_aggregates(services) -> None:
    snapshot = services["platform_runtime_application_service"].snapshot().module_snapshot
    assert snapshot.entitlements
    assert all(isinstance(item, RuntimeEntitlementFact) for item in snapshot.entitlements)
    assert all(not isinstance(item, ModuleEntitlement) for item in snapshot.entitlements)
    assert all(isinstance(item, RuntimeModuleFact) for item in snapshot.enabled_modules)
    assert all(not isinstance(item, EnterpriseModule) for item in snapshot.enabled_modules)

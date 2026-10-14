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


_HANDLER_FACADES = (
    "modules/project_management/application/projects/service.py",
    "modules/project_management/application/resources/project_resources/project_resource_service.py",
    "modules/project_management/application/tasks/service.py",
)


def _handler_modules() -> tuple[Path, ...]:
    roots = (
        SRC_ROOT / "modules/project_management/application",
        SRC_ROOT / "platform/application",
    )
    modules = {
        path
        for root in roots
        for path in root.rglob("*.py")
        if {"commands", "queries"} & set(path.relative_to(root).parts[:-1])
    }
    modules.update(SRC_ROOT / relative for relative in _HANDLER_FACADES)
    return tuple(sorted(modules))


def test_pm_handler_facades_leave_handler_construction_to_composition() -> None:
    modules = _handler_modules()
    assert modules
    for path in modules:
        tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
        constructors = tuple(
            node.func.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
            and node.func.id.endswith("Handler")
        )
        assert not constructors, (str(path.relative_to(SRC_ROOT)), constructors)


def test_migrated_platform_services_do_not_import_concrete_infrastructure() -> None:
    migrated = (
        *(SRC_ROOT / "platform/application/master_data/org").rglob("*.py"),
        SRC_ROOT / "platform/application/security/authorization/roles/tenant_role_administration_service.py",
        SRC_ROOT / "platform/application/security/authorization/roles/role_policy_reconciliation_service.py",
        *(SRC_ROOT / "platform/application/security/auth").rglob("*.py"),
        *(SRC_ROOT / "platform/application/security/authorization/roles/commands").rglob("*.py"),
        *(SRC_ROOT / "platform/application/time_management/time").rglob("*.py"),
    )
    for path in migrated:
        tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
        imports = (
            node.module or ""
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
        )
        assert not any(
            ".infrastructure." in imported or imported.startswith("src.infra.")
            for imported in imports
        ), str(path.relative_to(SRC_ROOT))


def test_pm_shared_command_inputs_live_in_use_case_contracts() -> None:
    desktop_root = SRC_ROOT / "modules/project_management/api/desktop"
    legacy = sorted(
        str(path.relative_to(SRC_ROOT))
        for path in desktop_root.glob("*/commands")
        if any(path.rglob("*.py"))
    )
    assert not legacy, legacy
    use_cases = SRC_ROOT / "modules/project_management/contracts/use_cases"
    for feature in (
        "collaboration",
        "financials",
        "portfolio",
        "projects",
        "register",
        "resources",
        "scheduling",
        "tasks",
        "timesheets",
    ):
        assert (use_cases / feature / "__init__.py").is_file(), feature


def test_register_dashboard_snapshot_exposes_scalar_risk_facts() -> None:
    from dataclasses import fields

    from src.core.modules.project_management.application.risk import (
        RegisterDashboardSnapshot,
    )

    high_risks = next(f for f in fields(RegisterDashboardSnapshot) if f.name == "high_risks")
    assert "RegisterHighRiskItem" in str(high_risks.type)
    assert "RegisterEntry," not in str(high_risks.type)

"""Business use cases must not depend on desktop or HTTP adapters."""

import ast
from pathlib import Path

from src.core.platform.application.platform_runtime.dto import (
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
    snapshot = services["platform_runtime_query"].snapshot().module_snapshot
    assert snapshot.entitlements
    assert all(isinstance(item, RuntimeEntitlementFact) for item in snapshot.entitlements)
    assert all(not isinstance(item, ModuleEntitlement) for item in snapshot.entitlements)
    assert all(isinstance(item, RuntimeModuleFact) for item in snapshot.enabled_modules)
    assert all(not isinstance(item, EnterpriseModule) for item in snapshot.enabled_modules)


_HANDLER_FACADES = (
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
        or path.name in {"commands.py", "queries.py"}
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
        SRC_ROOT / "platform/application/security/authorization/roles/commands/tenant_role_commands.py",
        *(SRC_ROOT / "platform/application/security/authorization/roles/queries").rglob("*.py"),
        *(SRC_ROOT / "platform/application/approval").rglob("*.py"),
        *(SRC_ROOT / "platform/application/notifications").rglob("*.py"),
        *(SRC_ROOT / "platform/application/finance").rglob("*.py"),
        *(SRC_ROOT / "platform/application/security/identity").rglob("*.py"),
        *(SRC_ROOT / "platform/application/tenant/tenancy/commands").rglob("*.py"),
        *(SRC_ROOT / "platform/application/tenant/tenancy/queries").rglob("*.py"),
        *(SRC_ROOT / "platform/application/time_management/calendar").rglob("*.py"),
        *(SRC_ROOT / "platform/application/master_data/data_exchange").rglob("*.py"),
        *(SRC_ROOT / "platform/application/platform_runtime").rglob("*.py"),
        *(SRC_ROOT / "platform/application/data_operations/runtime_tracking").rglob("*.py"),
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


def test_cross_module_approval_and_notification_ports_are_neutral() -> None:
    for feature in ("approval", "notifications"):
        root = SRC_ROOT / "platform/contract/port" / feature
        for path in root.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8-sig"))
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    imports = (node.module or "",)
                elif isinstance(node, ast.Import):
                    imports = tuple(alias.name for alias in node.names)
                else:
                    continue
                assert not any(
                    ".application." in name or ".infrastructure." in name
                    or name.startswith(("src.infra.", "src.ui_qml."))
                    for name in imports
                ), str(path.relative_to(SRC_ROOT))


def test_pm_command_dtos_live_in_feature_application_packages() -> None:
    desktop_root = SRC_ROOT / "modules/project_management/api/desktop"
    legacy = sorted(
        str(path.relative_to(SRC_ROOT))
        for path in desktop_root.glob("*/commands")
        if any(path.rglob("*.py"))
    )
    assert not legacy, legacy
    application = SRC_ROOT / "modules/project_management/application"
    for relative_path in (
        "collaboration/dto.py",
        "portfolio/dto.py",
        "projects/dto.py",
        "resources/dto.py",
        "risk/dto/register_commands.py",
        "scheduling/dto.py",
        "tasks/dto.py",
        "timesheets/dto.py",
        "financials/invoicing/dto.py",
        "financials/budgets/dto.py",
        "financials/financial_changes/dto.py",
        "financials/configuration/dto.py",
        "financials/cost/entries/dto.py",
        "financials/forecasts/dto.py",
        "financials/rate_cards/dto.py",
    ):
        assert (application / relative_path).is_file(), relative_path
    assert not any((SRC_ROOT / "modules/project_management/contracts/use_cases").rglob("*.py"))


def test_platform_command_dtos_live_in_feature_application_packages() -> None:
    application = SRC_ROOT / "platform/application"
    for feature in ("site", "documents", "party", "department", "employee", "org"):
        assert (application / "master_data" / feature / "dto.py").is_file(), feature
    assert (application / "platform_runtime/dto.py").is_file()
    assert not any((SRC_ROOT / "platform/contract/use_cases").rglob("*.py"))


def test_register_dashboard_snapshot_exposes_scalar_risk_facts() -> None:
    from dataclasses import fields

    from src.core.modules.project_management.application.risk import (
        RegisterDashboardSnapshot,
    )

    high_risks = next(f for f in fields(RegisterDashboardSnapshot) if f.name == "high_risks")
    assert "RegisterHighRiskItem" in str(high_risks.type)
    assert "RegisterEntry," not in str(high_risks.type)

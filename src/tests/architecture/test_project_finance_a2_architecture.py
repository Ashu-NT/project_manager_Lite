from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def _import_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def _call_keywords(source: str, function_name: str) -> set[str]:
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id == function_name:
                return {keyword.arg for keyword in node.keywords if keyword.arg is not None}
    raise AssertionError(f"Factory call not found: {function_name}")


def test_financial_source_contracts_do_not_import_source_modules_or_ui() -> None:
    package_dir = (
        ROOT
        / "src"
        / "core"
        / "modules"
        / "project_management"
        / "contracts"
        / "financial_sources"
    )
    forbidden_prefixes = (
        "src.core.platform.time",
        "src.core.modules.inventory_procurement",
        "src.ui_qml",
    )

    violations = sorted(
        f"{path.name}:{name}"
        for path in sorted(package_dir.glob("*.py"))
        for name in _import_names(path)
        if name.startswith(forbidden_prefixes)
    )
    assert not violations, f"Financial source contracts cross ownership boundaries: {violations}"


def test_platform_finance_and_integration_do_not_import_business_modules() -> None:
    roots = (
        ROOT / "src" / "core" / "platform" / "finance",
        ROOT / "src" / "core" / "platform" / "integration",
    )
    violations: list[tuple[str, str]] = []

    for root in roots:
        for path in root.rglob("*.py"):
            for name in _import_names(path):
                if name.startswith("src.core.modules") or name.startswith("src.ui_qml"):
                    violations.append((str(path.relative_to(ROOT)), name))

    assert not violations, f"Platform foundations import business/UI modules: {violations}"


def test_canonical_finance_snapshot_replaces_transient_forecast_formulas() -> None:
    project_registry = (ROOT / "src" / "infra" / "composition" / "project_registry.py").read_text(
        encoding="utf-8"
    )
    app_container = (ROOT / "src" / "infra" / "composition" / "app_container.py").read_text(
        encoding="utf-8"
    )
    runtime_builder = (
        ROOT
        / "src"
        / "core"
        / "modules"
        / "project_management"
        / "api"
        / "desktop_runtime"
        / "desktop_api_builder.py"
    ).read_text(encoding="utf-8")
    builder_root = (
        ROOT
        / "src"
        / "core"
        / "modules"
        / "project_management"
        / "api"
        / "desktop"
        / "financials"
        / "builders"
    )
    desktop_builders = "\n".join(
        (builder_root / name).read_text(encoding="utf-8")
        for name in ("forecast_builder.py", "commitment_builder.py")
    )

    assert "ForecastCostService" not in project_registry
    assert "forecast_service" not in app_container
    assert "forecast_service=resolved.forecast_service" not in runtime_builder
    assert "finance_service=resolved.finance_service" in runtime_builder
    dashboard_keywords = _call_keywords(
        runtime_builder,
        "build_project_management_dashboard_desktop_api",
    )
    financials_keywords = _call_keywords(
        runtime_builder,
        "build_project_management_financials_desktop_api",
    )
    assert "finance_workspace_query" not in dashboard_keywords
    assert "finance_workspace_query" in financials_keywords
    assert "list_cost_items_for_project" not in desktop_builders
    assert "_compute_etc_eac" not in desktop_builders
    assert "result.bac *" not in desktop_builders

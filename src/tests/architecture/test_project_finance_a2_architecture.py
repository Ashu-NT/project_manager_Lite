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


def test_financial_source_contracts_do_not_import_source_modules_or_ui() -> None:
    path = (
        ROOT
        / "src"
        / "core"
        / "modules"
        / "project_management"
        / "contracts"
        / "financial_sources.py"
    )
    forbidden_prefixes = (
        "src.core.platform.time",
        "src.core.modules.inventory_procurement",
        "src.ui_qml",
    )

    violations = sorted(
        name
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


def test_forecast_service_is_composed_and_desktop_builders_are_mapping_only() -> None:
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

    assert "forecast_service = ForecastCostService(" in project_registry
    assert "forecast_service: ForecastCostService" in app_container
    assert "forecast_service=resolved.forecast_service" in runtime_builder
    assert "list_cost_items_for_project" not in desktop_builders
    assert "_compute_etc_eac" not in desktop_builders
    assert "result.bac *" not in desktop_builders

from __future__ import annotations

import ast
import importlib
import inspect
from dataclasses import is_dataclass
from pathlib import Path

from src.core.modules.project_management.application.financials.services.finance_service import (
    FinanceService,
)
from src.core.modules.project_management.application.financials.earned_value.evm_series import (
    EarnedValueSeriesCalculator,
)
from src.core.modules.project_management.application.financials.earned_value.evm_calculator import (
    EarnedValueCalculator,
)
from src.core.modules.project_management.application.financials.costs.cost_breakdown_engine import (
    CostBreakdownEngine,
)
from src.core.modules.project_management.application.financials.costs.cost_policy_engine import (
    CostPolicyEngine,
)
from src.core.modules.project_management.infrastructure.reporting.builders.cost_breakdown import (
    ReportingCostBreakdownMixin,
)
from src.core.modules.project_management.infrastructure.reporting.builders.cost_policy import (
    ReportingCostPolicyMixin,
)
from src.core.modules.project_management.infrastructure.reporting.builders.evm_core import (
    ReportingEvmCoreMixin,
)
from src.core.modules.project_management.application.resources.portfolio_resource_pool_service import (
    PortfolioResourcePoolService,
)
from src.core.modules.project_management.application.portfolio.queries.portfolio_scenarios import (
    PortfolioScenarioQueryMixin,
)
from src.core.modules.project_management.application.portfolio.queries.portfolio_executive import (
    PortfolioExecutiveQueryMixin,
)
from src.core.modules.project_management.infrastructure.reporting.builders.kpi import (
    ReportingKpiMixin,
)
from src.tests.path_rewrites import REPO_ROOT


PM_ROOT = REPO_ROOT / "src/core/modules/project_management"
CONTRACT_READS = PM_ROOT / "contracts/reads"
FINANCE_READS = PM_ROOT / "infrastructure/persistence/reads/financials"
FINANCE_STATEMENTS = FINANCE_READS / "statements/finance_snapshot_statements.py"
FINANCE_READER = FINANCE_READS / "sqlalchemy_finance_snapshot_reader.py"
FINANCE_POLICY = PM_ROOT / "application/financials/costs/cost_policy_engine.py"
PROJECT_REGISTRY = REPO_ROOT / "src/infra/composition/project_registry.py"
PHASE1_TEST = REPO_ROOT / "src/tests/project_management/test_finance_snapshot_phase1_reader.py"
PHASE3A_TEST = REPO_ROOT / "src/tests/project_management/test_evm_series_phase3a_parity.py"
PHASE3B_TEST = REPO_ROOT / "src/tests/project_management/test_reporting_financials_phase3b_parity.py"
PORTFOLIO_POOL_READER = (
    PM_ROOT
    / "infrastructure/persistence/reads/portfolio/sqlalchemy_resource_pool_reader.py"
)
PORTFOLIO_SCENARIO_READER = (
    PM_ROOT / "infrastructure/persistence/reads/portfolio/sqlalchemy_scenario_reader.py"
)
PORTFOLIO_HEATMAP_READER = (
    PM_ROOT / "infrastructure/persistence/reads/portfolio/sqlalchemy_heatmap_reader.py"
)

FORBIDDEN_CONTRACT_IMPORTS = (
    "src.core.modules.project_management.application",
    "src.core.modules.project_management.api.desktop",
    "src.core.modules.project_management.infrastructure",
    "sqlalchemy",
)
FORBIDDEN_READER_IMPORTS = (
    "src.core.modules.project_management.application",
    "src.core.modules.project_management.api.desktop",
)


def _tree(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _imports_from_tree(tree: ast.AST) -> tuple[str, ...]:
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.append(node.module)
    return tuple(names)


def _forbidden_imports(source: str, prefixes: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(
        name
        for name in _imports_from_tree(ast.parse(source))
        if any(name == prefix or name.startswith(f"{prefix}.") for prefix in prefixes)
    )


def _protocol_methods(path: Path) -> tuple[ast.FunctionDef | ast.AsyncFunctionDef, ...]:
    methods: list[ast.FunctionDef | ast.AsyncFunctionDef] = []
    for node in _tree(path).body:
        if not isinstance(node, ast.ClassDef):
            continue
        if not any(ast.unparse(base).endswith("Protocol") for base in node.bases):
            continue
        methods.extend(
            member
            for member in node.body
            if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef))
            and not member.name.startswith("_")
        )
    return tuple(methods)


def _missing_scope_parameters(source: str) -> tuple[str, ...]:
    missing: list[str] = []
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        if not any(ast.unparse(base).endswith("Protocol") for base in node.bases):
            continue
        for method in node.body:
            if not isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if method.name.startswith("_"):
                continue
            names = {arg.arg for arg in (*method.args.args, *method.args.kwonlyargs)}
            absent = {"tenant_id", "organization_id"} - names
            if absent:
                missing.append(f"{node.name}.{method.name}:{','.join(sorted(absent))}")
    return tuple(missing)


def _reader_write_calls(source: str) -> tuple[str, ...]:
    forbidden = {"add", "add_all", "commit", "delete", "flush", "merge", "rollback"}
    return tuple(
        node.func.attr
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr in forbidden
    )


def test_reader_contracts_are_scoped_and_return_contract_facts_only() -> None:
    methods_found = 0
    violations: list[str] = []
    for path in CONTRACT_READS.rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        imports = _forbidden_imports(source, FORBIDDEN_CONTRACT_IMPORTS)
        if imports:
            violations.append(f"{path.relative_to(REPO_ROOT)} imports {imports}")
        missing_scope = _missing_scope_parameters(source)
        if missing_scope:
            violations.append(f"{path.relative_to(REPO_ROOT)} missing scope {missing_scope}")
        for method in _protocol_methods(path):
            methods_found += 1
            annotation = ast.unparse(method.returns) if method.returns is not None else ""
            if not annotation or any(
                forbidden in annotation
                for forbidden in ("domain.", "application.", "infrastructure.", "ORM")
            ):
                violations.append(
                    f"{path.relative_to(REPO_ROOT)}:{method.name} return={annotation!r}"
                )

    assert methods_found > 0, "No contracts/reads Protocol methods were inspected"
    assert violations == []


def test_reader_fact_dataclasses_are_frozen_slotted_and_contract_owned() -> None:
    checked: list[str] = []
    violations: list[str] = []
    models_root = CONTRACT_READS
    for path in models_root.rglob("models/*.py"):
        if path.name == "__init__.py":
            continue
        module_name = ".".join(path.relative_to(REPO_ROOT).with_suffix("").parts)
        module = importlib.import_module(module_name)
        for name, value in vars(module).items():
            if not inspect.isclass(value) or value.__module__ != module_name:
                continue
            checked.append(f"{module_name}.{name}")
            params = getattr(value, "__dataclass_params__", None)
            if not is_dataclass(value) or params is None or not params.frozen:
                violations.append(f"{module_name}.{name} is not a frozen dataclass")
            if "__slots__" not in value.__dict__:
                violations.append(f"{module_name}.{name} is not slotted")

    assert checked, "No contracts/reads fact dataclasses were inspected"
    assert violations == []


def test_sqlalchemy_readers_are_read_only_and_policy_free() -> None:
    violations: list[str] = []
    forbidden_terms = (
        "finance.read",
        "finance.read_sensitive",
        "include_manual_labor",
        "rate_resolver",
        "redact",
        "ProjectPlannedCostVersion",
        "ProjectPlannedCostLine",
    )
    for path in (p for p in FINANCE_READS.rglob("*reader.py") if p.is_file()):
        source = path.read_text(encoding="utf-8")
        imports = _forbidden_imports(source, FORBIDDEN_READER_IMPORTS)
        if imports:
            violations.append(f"{path.relative_to(REPO_ROOT)} imports {imports}")
        writes = _reader_write_calls(source)
        if writes:
            violations.append(f"{path.relative_to(REPO_ROOT)} writes via {writes}")
        lowered = source.lower()
        for term in forbidden_terms:
            if term.lower() in lowered:
                violations.append(f"{path.relative_to(REPO_ROOT)} contains {term}")
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.ExceptHandler) and node.type is not None:
                if ast.unparse(node.type) in {"Exception", "BaseException"}:
                    violations.append(f"{path.relative_to(REPO_ROOT)} catches {ast.unparse(node.type)}")

    assert violations == []


def test_finance_statement_builders_require_explicit_scope() -> None:
    violations: list[str] = []
    for node in _tree(FINANCE_STATEMENTS).body:
        if not isinstance(node, ast.FunctionDef) or not node.name.endswith("_statement"):
            continue
        parameters = {arg.arg for arg in (*node.args.args, *node.args.kwonlyargs)}
        missing = {"tenant_id", "organization_id", "project_id"} - parameters
        if missing:
            violations.append(f"{node.name} missing {sorted(missing)}")
        body = ast.unparse(node)
        if node.name == "resource_facts_statement":
            required = ("ResourceORM.tenant_id", "ResourceORM.organization_id", "_project_scope")
        else:
            required = ("_project_scope",)
        for token in required:
            if token not in body:
                violations.append(f"{node.name} missing predicate {token}")

    assert violations == []


def test_cost_aggregation_cannot_fan_out_across_independent_sources() -> None:
    aggregate = next(
        node
        for node in _tree(FINANCE_STATEMENTS).body
        if isinstance(node, ast.FunctionDef) and node.name == "cost_aggregate_facts_statement"
    )
    source = ast.unparse(aggregate)
    orm_names = {
        node.id
        for node in ast.walk(aggregate)
        if isinstance(node, ast.Name) and node.id.endswith("ORM")
    }

    assert "func.sum" in source
    assert "group_by" in source
    assert orm_names == {"CostItemORM", "ProjectORM"}


def test_finance_service_keeps_reader_labor_policy_ownership_and_no_fallback() -> None:
    source = inspect.getsource(FinanceService.get_finance_snapshot)

    assert source.count("self._finance_snapshot_reader.read_facts(") == 1
    assert source.count("self._labor.calculate_project_labor_details(") == 1
    assert source.count("engine.compose_from_facts(") == 1
    for forbidden in (
        "_cost_repo.list_by_project",
        "_project_resource_repo.list_by_project",
        "_task_repo.list_by_project",
        "_project_repo.get",
        "resolve_manual_labor_inclusion",
        "include_manual_labor_planned",
        "include_manual_labor_actual",
    ):
        assert forbidden not in source

    policy_source = FINANCE_POLICY.read_text(encoding="utf-8")
    assert "def compose_from_facts(" in policy_source
    assert "include_manual_labor_planned" in policy_source


def test_runtime_composition_and_desktop_proof_remain_present() -> None:
    registry = PROJECT_REGISTRY.read_text(encoding="utf-8")
    runtime_test = PHASE1_TEST.read_text(encoding="utf-8")

    assert "finance_snapshot_reader=SqlAlchemyFinanceSnapshotReader(session=session)" in registry
    assert "isinstance(reader, SqlAlchemyFinanceSnapshotReader)" in runtime_test
    assert "registry.project_management_financials.get_finance_snapshot" in runtime_test


def test_evm_series_keeps_bounded_reader_and_policy_ownership() -> None:
    source = inspect.getsource(EarnedValueSeriesCalculator.build_series)

    assert source.count("self._reader.read_facts(") == 1
    assert source.count("calculate_project_labor_series(") == 1
    assert source.count("prepare_working_days(") == 1
    assert source.count("compose_from_facts_at(") == 1
    assert "prepared_facts=facts" in source
    for forbidden in (
        "_project_repo",
        "_baseline_repo",
        "_task_repo",
        "_cost_repo",
        "_assignment_repo",
        "_resource_repo",
        "resolve_many(",
        "calculate_project_labor_details(",
    ):
        assert forbidden not in source


def test_evm_series_runtime_reader_proof_remains_present() -> None:
    registry = PROJECT_REGISTRY.read_text(encoding="utf-8")
    runtime_test = PHASE3A_TEST.read_text(encoding="utf-8")

    assert "evm_series_reader=SqlAlchemyEvmSeriesReader(session=session)" in registry
    assert "isinstance(reader, SqlAlchemyEvmSeriesReader)" in runtime_test
    assert "reporting.get_evm_series(" in runtime_test


def test_reporting_financial_reads_use_one_facts_policy_composition() -> None:
    finance_source = inspect.getsource(ReportingCostPolicyMixin._compose_finance_policy)
    evm_source = inspect.getsource(ReportingCostPolicyMixin._compose_evm_policy)
    totals_source = inspect.getsource(ReportingCostPolicyMixin.get_project_cost_control_totals)
    sources_source = inspect.getsource(ReportingCostPolicyMixin.get_project_cost_source_breakdown)
    breakdown_source = inspect.getsource(ReportingCostBreakdownMixin.get_cost_breakdown)
    earned_value_source = inspect.getsource(ReportingEvmCoreMixin.get_earned_value)

    assert finance_source.count("self._finance_snapshot_reader.read_facts(") == 1
    assert evm_source.count("self._evm_series_reader.read_facts(") == 1
    for source in (finance_source, evm_source):
        assert source.count("calculate_project_labor_details(") == 1
        assert source.count("compose_from_facts(") == 1
        for forbidden in (
            "_project_repo",
            "_baseline_repo",
            "_task_repo",
            "_cost_repo",
            "_assignment_repo",
            "_resource_repo",
            "build_snapshot(",
        ):
            assert forbidden not in source

    assert "_compose_finance_policy(" in totals_source
    assert "_compose_finance_policy(" in sources_source
    assert "_compose_evm_policy(" in breakdown_source
    assert "build_breakdown_from_snapshot(" in breakdown_source
    assert "_compose_evm_policy(" in earned_value_source
    assert "prepared_facts=facts" in earned_value_source
    assert "ACTUAL_COST_INCOMPLETE" in earned_value_source


def test_reporting_financial_runtime_reader_proof_remains_present() -> None:
    registry = PROJECT_REGISTRY.read_text(encoding="utf-8")
    runtime_test = PHASE3B_TEST.read_text(encoding="utf-8")

    assert "finance_snapshot_reader=SqlAlchemyFinanceSnapshotReader(session=session)" in registry
    assert "isinstance(reader, SqlAlchemyFinanceSnapshotReader)" in runtime_test
    assert "reporting.get_project_cost_control_totals(" in runtime_test


def test_phase3b_removed_repository_backed_financial_transition_paths() -> None:
    for removed in (
        "get_cost_control_totals",
        "get_cost_source_breakdown",
        "get_actual_cost",
    ):
        assert not hasattr(CostPolicyEngine, removed)
    assert not hasattr(CostBreakdownEngine, "build_breakdown")

    evm_source = inspect.getsource(EarnedValueCalculator)
    for forbidden in (
        "ProjectRepository",
        "TaskRepository",
        "BaselineRepository",
        "_project_repo",
        "_task_repo",
        "_baseline_repo",
        "_get_actual_cost",
    ):
        assert forbidden not in evm_source


def test_portfolio_capacity_uses_one_scoped_reader_and_bulk_calendar_snapshot() -> None:
    source = inspect.getsource(PortfolioResourcePoolService)
    get_pool_source = inspect.getsource(PortfolioResourcePoolService.get_pool_report)
    registry = PROJECT_REGISTRY.read_text(encoding="utf-8")
    reader_source = PORTFOLIO_POOL_READER.read_text(encoding="utf-8")

    assert get_pool_source.count("self._reader.read_facts(") == 1
    assert get_pool_source.count("self._working_dates(") == 1
    for forbidden in (
        "self._resources",
        "self._assignments",
        "self._tasks",
        "self._projects",
        "ResourceAvailabilityService",
    ):
        assert forbidden not in source
    assert "reader=SqlAlchemyPortfolioResourcePoolReader(session=session)" in registry
    assert "ResourceORM.tenant_id == tenant_id" in reader_source
    assert "ResourceORM.organization_id == organization_id" in reader_source
    assert "ProjectORM.tenant_id == tenant_id" in reader_source
    assert "ProjectORM.organization_id == organization_id" in reader_source


def test_portfolio_scenarios_use_one_scoped_fact_graph_and_shared_load_engine() -> None:
    compare_source = inspect.getsource(PortfolioScenarioQueryMixin.compare_scenarios)
    acquisition_source = inspect.getsource(PortfolioScenarioQueryMixin._read_scenario_facts)
    scenario_source = inspect.getsource(PortfolioScenarioQueryMixin)
    reporting_source = inspect.getsource(ReportingKpiMixin.get_resource_load_summary)
    registry = PROJECT_REGISTRY.read_text(encoding="utf-8")
    reader_source = PORTFOLIO_SCENARIO_READER.read_text(encoding="utf-8")

    assert acquisition_source.count("self._scenario_reader.read_facts(") == 1
    assert compare_source.count("self._read_scenario_facts(") == 1
    assert "self.evaluate_scenario(" not in compare_source
    assert "ResourceLoadEngine.calculate(" in scenario_source
    assert "ResourceLoadEngine.calculate(" in reporting_source
    for forbidden in (
        "_scenario_repo.get(",
        "_intake_repo.list(",
        "_resource_repo.list(",
        "_reporting.get_resource_load_summary(",
    ):
        assert forbidden not in scenario_source
    assert "scenario_reader=SqlAlchemyPortfolioScenarioReader(session=session)" in registry
    for predicate in (
        "PortfolioScenarioORM.tenant_id == tenant_id",
        "PortfolioScenarioORM.organization_id == organization_id",
        "ProjectORM.tenant_id == tenant_id",
        "ProjectORM.organization_id == organization_id",
        "ResourceORM.tenant_id == tenant_id",
        "ResourceORM.organization_id == organization_id",
    ):
        assert predicate in reader_source


def test_portfolio_heatmap_uses_one_scoped_fact_graph_and_pure_policy_engines() -> None:
    heatmap_source = inspect.getsource(PortfolioExecutiveQueryMixin.list_portfolio_heatmap)
    source = inspect.getsource(PortfolioExecutiveQueryMixin)
    registry = PROJECT_REGISTRY.read_text(encoding="utf-8")
    reader_source = PORTFOLIO_HEATMAP_READER.read_text(encoding="utf-8")

    assert heatmap_source.count("self._heatmap_reader.read_facts(") == 1
    assert "CPMCalculator(calendar).calculate(" in source
    assert "ResourceLoadEngine.calculate(" in source
    assert "LaborCostEngine.for_facts(" in source
    assert "CostPolicyEngine.for_facts(" in source
    assert "working_day_dates_between(" in source
    for forbidden in (
        "_reporting.get_project_kpis(",
        "_reporting.get_resource_load_summary(",
        "_project_repo.get(",
        "_task_repo.list_by_project(",
        "_assignment_repo.list_by_tasks(",
        "_resource_repo.get(",
    ):
        assert forbidden not in heatmap_source
    assert "heatmap_reader=SqlAlchemyPortfolioHeatmapReader(session=session)" in registry
    for predicate in (
        "ProjectORM.tenant_id == tenant_id",
        "ProjectORM.organization_id == organization_id",
        "ResourceORM.tenant_id == tenant_id",
        "ResourceORM.organization_id == organization_id",
    ):
        assert predicate in reader_source


def test_guard_detectors_reject_deliberately_broken_in_memory_examples() -> None:
    bad_contract = """
from typing import Protocol
from src.core.modules.project_management.application.financials.models.finance_models import FinanceSnapshot
class BrokenReader(Protocol):
    def read(self, *, tenant_id: str) -> FinanceSnapshot: ...
"""
    bad_adapter = """
class SqlAlchemyBrokenReader:
    def read(self):
        self._session.commit()
"""

    assert _forbidden_imports(bad_contract, FORBIDDEN_CONTRACT_IMPORTS)
    assert _missing_scope_parameters(bad_contract)
    assert _reader_write_calls(bad_adapter) == ("commit",)

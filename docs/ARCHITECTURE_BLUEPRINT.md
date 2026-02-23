# Architecture Blueprint

## Scope

This document captures current architecture hotspots, target structure, and guardrails for keeping this project maintainable as a project-management desktop app.

## Current Layering

1. `core/`
Application/domain logic (entities, interfaces, services, reporting calculations).
2. `infra/`
Persistence and dependency wiring (`db` repositories + service graph factory).
3. `ui/`
Qt presentation layer and user interaction workflows.

This is already a good layered baseline and should be preserved.

## Monolith Hotspots (Current Audit)

Top large modules observed in this codebase:

1. `main.py` (~498 lines)
2. `ui/calendar/tab.py` (~412 lines)
3. `core/services/scheduling/engine.py` (~408 lines)
4. `ui/resource/tab.py` (~313 lines)
5. `infra/db/mappers.py` (~306 lines)
6. `core/models.py` (~305 lines)
7. `ui/task/tab.py` (~289 lines)

## Refactor Applied In This Pass

1. Report UI split into coordinator + dialogs:
   - Coordinator: `ui/report/tab.py` (~196 lines)
   - Dialogs: `ui/report/dialogs.py` (~260 lines)
2. Export architecture was previously consolidated:
   - Canonical export pipeline: `core/reporting/api.py` + `core/reporting/renderers/*`
   - Compatibility adapter: `core/reporting/exporters.py` (deprecated wrapper)
3. Reporting domain service split (Phase 2):
   - Orchestrator: `core/services/reporting/service.py` (~55 lines)
   - KPI mixin: `core/services/reporting/kpi.py` (~221 lines)
   - Labor mixin: `core/services/reporting/labor.py` (~201 lines)
   - EVM facade mixin: `core/services/reporting/evm.py` (~8 lines)
   - EVM core calculations: `core/services/reporting/evm_core.py` (~213 lines)
   - EVM series generation: `core/services/reporting/evm_series.py` (~56 lines)
   - Variance mixin: `core/services/reporting/variance.py` (~66 lines)
   - Cost breakdown mixin: `core/services/reporting/cost_breakdown.py` (~158 lines)
4. Project UI split into coordinator + submodules:
   - Coordinator: `ui/project/tab.py` (~197 lines)
   - Dialog facade: `ui/project/dialogs.py` (~10 lines)
   - Project metadata dialog: `ui/project/project_edit_dialog.py` (~170 lines)
   - Project-resource facade: `ui/project/project_resource_dialogs.py` (~4 lines)
   - Project resources list dialog: `ui/project/project_resources_dialog.py` (~194 lines)
   - Project resource edit dialog: `ui/project/project_resource_edit_dialog.py` (~182 lines)
   - Table model: `ui/project/models.py` (~63 lines)
5. Task UI split into coordinator + submodules:
   - Coordinator: `ui/task/tab.py` (~289 lines)
   - Dialog facade: `ui/task/dialogs.py` (~15 lines)
   - Task dialogs: `ui/task/task_dialogs.py` (~263 lines)
   - Dependency dialogs: `ui/task/dependency_dialogs.py` (~169 lines)
   - Assignment dialogs: `ui/task/assignment_dialogs.py` (~217 lines)
   - Table model: `ui/task/models.py` (~62 lines)
   - Compatibility exports: `ui/task/components.py` (~21 lines)
6. Infrastructure DB repositories split by aggregate:
   - Compatibility facade: `infra/db/repositories.py` (~82 lines)
   - Shared mappers: `infra/db/mappers.py` (~306 lines)
   - Project repos: `infra/db/repositories_project.py` (~60 lines)
   - Task/dependency/assignment repos: `infra/db/repositories_task.py` (~102 lines)
   - Resource repo: `infra/db/repositories_resource.py` (~25 lines)
   - Cost/calendar repos: `infra/db/repositories_cost_calendar.py` (~103 lines)
   - Baseline repo: `infra/db/repositories_baseline.py` (~52 lines)
7. Cost UI split into coordinator + submodules:
   - Coordinator: `ui/cost/tab.py` (~144 lines)
   - Project/data flow mixin: `ui/cost/project_flow.py` (~115 lines)
   - Labor summary mixin: `ui/cost/labor_summary.py` (~130 lines)
   - Cost actions mixin: `ui/cost/actions.py` (~103 lines)
   - Compatibility exports: `ui/cost/components.py` (~10 lines)
   - Models: `ui/cost/models.py` (~104 lines)
   - Cost item dialog: `ui/cost/cost_dialogs.py` (~145 lines)
   - Labor dialogs: `ui/cost/labor_dialogs.py` (~231 lines)
8. Task domain service split into capability mixins:
   - Orchestrator: `core/services/task/service.py` (~48 lines)
   - Lifecycle: `core/services/task/lifecycle.py` (~161 lines)
   - Dependency flow: `core/services/task/dependency.py` (~63 lines)
   - Assignment flow: `core/services/task/assignment.py` (~130 lines)
   - Query layer: `core/services/task/query.py` (~46 lines)
   - Validation/rules: `core/services/task/validation.py` (~144 lines)
9. Dashboard UI split into coordinator + focused modules:
   - Coordinator: `ui/dashboard/tab.py` (~176 lines)
   - Data/loading mixin: `ui/dashboard/data_ops.py` (~124 lines)
   - Rendering facade: `ui/dashboard/rendering.py` (~10 lines)
   - Summary/KPI rendering: `ui/dashboard/rendering_summary.py` (~77 lines)
   - Charts/lists rendering: `ui/dashboard/rendering_charts.py` (~79 lines)
   - EVM rendering: `ui/dashboard/rendering_evm.py` (~169 lines)
   - Reusable widgets: `ui/dashboard/widgets.py` (~67 lines)

## Architecture Principles (Enforced)

1. Single Responsibility:
   - Tabs coordinate workflows.
   - Dialogs own view rendering/details.
   - Services own business logic.
2. Layered Dependency Rule:
   - `core` must not import `ui`.
3. Stable Interfaces:
   - Keep service/repository contracts in `core/interfaces.py`.
4. Replace Duplication With Adapters:
   - Legacy entry points become wrappers to canonical implementations.
5. Monolith Growth Budgets:
   - Existing large files have explicit growth caps to prevent further entropy.

## Patterns To Use

1. `Facade`
   - Service-level APIs (`ReportingService`, `DashboardService`).
2. `Strategy`
   - Reporting renderers (`gantt`, `evm`, `excel`, `pdf`).
3. `Adapter`
   - Legacy compatibility wrappers (`core/reporting/exporters.py`).
4. `Repository`
   - Infra DB adapters for persistence operations.
5. `Composition over Inheritance` in UI
   - Tab classes should compose dialogs/components instead of embedding all classes in one file.

## Next Structural Refactors (Recommended Order)

1. Refactor startup/wiring monolith in `main.py` into:
   - app bootstrap, dependency wiring, and launcher modules.
2. Split `ui/calendar/tab.py` into coordinator + dialogs/models.
3. Split `core/services/scheduling/engine.py` into:
   - forward-pass scheduling, critical-path analysis, and calendar utilities.

## Guardrails

Architecture guardrails are codified in:
`tests/test_architecture_guardrails.py`

These checks validate:

1. Hard file-size ceiling.

2. `core -> ui` import violations.
3. Report tab remains coordinator-only.
4. Project tab remains coordinator-only.
5. Growth budgets for known large modules.

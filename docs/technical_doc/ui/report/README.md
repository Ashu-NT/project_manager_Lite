# UI Report Module

`ui/report/` is the reporting center for operational dialogs and executive
exports.

## Files

- coordinator: `tab.py`
- actions: `actions.py`
- project selector flow: `project_flow.py`
- dialog facade: `dialogs.py`
- dialogs:
  - KPI, Gantt, critical path, resource load
  - performance variance
  - EVM analysis
  - finance view
  - baseline comparison
- helper UI builders: `dialog_helpers.py`

## Coordinator (`ReportTab`)

The tab is intentionally coordinator-only:

- builds sectioned UI
- wires actions to mixin methods
- applies export permission logic
- handles project reload lifecycle

Operational views:

- KPI
- Gantt preview
- critical path
- resource load
- performance variance
- EVM
- finance
- baseline comparison

Exports:

- Gantt PNG
- EVM PNG
- Excel report
- PDF report

## Action Layer (`ReportActionsMixin`)

Behavior:

- validates selected project before actions
- opens dialogs for view actions
- executes exports asynchronously using `start_async_job`
- creates per-job worker service scope to avoid UI-thread session contention
- handles baseline-required cases gracefully (`NO_BASELINE` guidance)

## Permission Model

- viewing depends on report tab visibility at main-window permission gate
- export buttons require `report.export`
- finance view enabled only when finance service is available

## Error and UX Model

- `NotFoundError` and `BusinessRuleError` are surfaced as contextual warnings
- exports provide user-selected output paths
- async jobs support retry and cancel semantics

## Reporting Stack Integration

Actions call into `core.reporting.api`, which composes data from:

- `ReportingService`
- optional `FinanceService`

This keeps UI module focused on workflow and interaction, not render mechanics.

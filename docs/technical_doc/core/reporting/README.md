# Core Reporting Export Layer

`core/reporting/` is the export and rendering layer that transforms reporting
service outputs into distributable artifacts (PNG, Excel, PDF).

## Layer Boundaries

- Upstream data source: `core.services.reporting.ReportingService` and optional
  `core.services.finance.FinanceService`.
- Downstream output: files on disk for user export workflows.
- UI tabs call this layer through `core.reporting.api`.

## Files and Responsibilities

- `api.py`:
  - high-level export functions
  - context assembly
  - temporary artifact cleanup
  - graceful handling for optional baseline-dependent data (`NO_BASELINE`)
- `contexts.py`:
  - typed context dataclasses for renderer contracts
- `renderers/gantt.py` and `renderers/evm.py`:
  - chart image generation
- `renderers/excel.py`:
  - workbook generation with multiple analysis sheets
- `renderers/pdf.py`:
  - executive summary PDF generation
- `exporters.py`:
  - compatibility adapter for legacy import paths

## Export API Contract

Primary functions:

- `generate_gantt_png(...)`
- `generate_evm_png(...)`
- `generate_excel_report(...)`
- `generate_pdf_report(...)`

Common behavior:

- ensure output parent directory exists
- derive all payloads from current reporting service state
- include finance snapshot when finance service is provided

## Context Composition

`ExcelReportContext` and `PdfReportContext` carry:

- KPI summary
- resource load
- EVM summary and EVM time series
- baseline variance
- cost breakdown and cost source policy split
- finance snapshot
- as-of date
- format-specific visualization payload (gantt bars or gantt image path)

## Excel Renderer Notes

Workbook commonly includes:

- overview KPI sheet
- task detail sheet
- resource summary sheet
- optional EVM sheet
- baseline variance sheet
- cost breakdown and source sheets
- finance summary and ledger sheets

## PDF Renderer Notes

PDF layout includes:

- project summary
- gantt image section
- optional EVM and baseline variance sections
- cost breakdown and source sections
- finance summary/cashflow analytics sections
- resource load summary

## Fault Tolerance

- Optional report sections are omitted if corresponding data is unavailable.
- Baseline-dependent queries can be soft-failed for exports where meaningful.
- temporary artifacts are cleaned up in `finally` paths.

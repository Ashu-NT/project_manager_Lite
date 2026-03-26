# Import Export Report Runtime Follow-Up

## Purpose

This README defines the follow-up design and remaining work for extracting shared import, export,
and report runtime machinery into `platform`.

The governing rule remains:

**share enterprise capabilities, not business ownership.**

This means the platform may own reusable runtime machinery, but it must not
become the owner of project, task, KPI, stock, payroll, asset, or other
module-specific meaning.

## Why This Slice Exists

The current codebase already has strong module-local implementations for:

- PM import orchestration under `core/modules/project_management/services/import_service`
- PM reporting analytics under `core/modules/project_management/services/reporting`
- PM export/rendering under `core/modules/project_management/reporting`
- UI async execution plumbing under `ui/platform/shared/async_job.py`

That is enough for `project_management`, but it is not yet the right shape for
future modules that will need the same runtime patterns without inheriting PM
business semantics.

This follow-up exists to define the extraction boundary and remaining follow-up after the first implementation landed.

## Implementation Status

- Foundation implemented:
  - `core/platform/importing`
  - `core/platform/exporting`
  - `core/platform/report_runtime`
- PM compatibility wrappers now register module-owned definitions against those platform runtimes.
- Shared runtime dispatch now enforces module-entitlement and permission checks when the live platform session/runtime context is supplied.
- Remaining follow-up is broader module adoption, richer background-job and writer orchestration, and shared-master bulk import/export contracts.

## Ownership Rule

### Platform Owns

- source reader and writer registries
- upload and file-handling plumbing
- generic preview and execution envelopes
- row-level error format and validation envelope
- artifact metadata and delivery plumbing
- temp artifact lifecycle and cleanup patterns
- background-job hooks, retries, cancellation, and status tracking
- permission, audit, and notification integration hooks
- report document primitives and renderer contracts

### Modules Own

- import definitions
- column mappings
- business validation rules
- row-to-entity transformation logic
- upsert and commit semantics
- report definitions and supported report variants
- KPI, EVM, schedule, finance, and other business formulas
- export field selections
- module-specific report sections, charts, and narrative meaning

## Explicit Non-Goals

The following are out of scope for `platform` in this slice:

- moving PM KPI, EVM, gantt, baseline, or cost semantics into `platform`
- moving PM critical-path or resource-leveling logic into `platform`
- creating platform models named after PM business concepts such as `ProjectKPI`
- letting `platform` query PM repositories directly as if it owned PM reporting
- creating a generic platform report that is really just the PM report surface
- forcing a storage or transport rewrite before the runtime contracts exist

## Target Repository Shape

The first implementation slice should introduce new platform packages in
`core/` and keep infrastructure and UI changes as thin adapters.

```text
core/
  platform/
    importing/
      __init__.py
      contracts.py
      models.py
      parsers.py
      registry.py
      runtime.py
      policies.py
    exporting/
      __init__.py
      contracts.py
      models.py
      registry.py
      runtime.py
      delivery.py
      writers/
        __init__.py
        csv.py
        excel.py
    report_runtime/
      __init__.py
      contracts.py
      models.py
      filters.py
      registry.py
      runtime.py
      renderers/
        __init__.py
        excel.py
        pdf.py

core/
  modules/
    project_management/
      importing/
        __init__.py
        definitions.py
        projects.py
        resources.py
        tasks.py
        costs.py
      exporting/
        __init__.py
        definitions.py
        field_sets.py
      reporting/
        __init__.py
        definitions.py
        documents.py
```

The first slice should not create broad new `infra/platform/...` packages unless
there is a real adapter or persistence concern that cannot stay behind the
existing local file behavior.

## Package Contracts

### `core/platform/importing`

Responsibility:

- understand file shapes and source rows
- normalize preview and execution results
- enforce generic permission and audit hooks
- hand business interpretation to module-owned import definitions

Suggested neutral models:

```python
@dataclass(frozen=True)
class ImportSourceRow:
    row_number: int
    values: Mapping[str, str]


@dataclass(frozen=True)
class RowError:
    row_number: int
    field_key: str | None
    code: str
    message: str
    severity: Literal["error", "warning"]


@dataclass(frozen=True)
class ImportFieldSpec:
    key: str
    label: str
    required: bool = False
```

Suggested extension contract:

```python
class ImportDefinition(Protocol):
    operation_key: str
    module_code: str
    permission_code: str

    def field_specs(self) -> Sequence[ImportFieldSpec]: ...
    def preview(
        self,
        rows: Sequence[ImportSourceRow],
        context: ImportContext,
    ) -> ImportPreview: ...
    def execute(
        self,
        rows: Sequence[ImportSourceRow],
        context: ImportContext,
        progress: ProgressReporter,
    ) -> ImportExecutionResult: ...
```

Important boundary:

- `platform.importing` owns the row envelope
- module definitions own what a row means

### `core/platform/exporting`

Responsibility:

- manage export job requests
- normalize artifact metadata
- own writer registration for generic tabular outputs
- own file delivery and artifact-handling policies
- stay neutral about business fields and formulas

Suggested neutral models:

```python
@dataclass(frozen=True)
class ExportColumnSpec:
    key: str
    label: str


@dataclass(frozen=True)
class TabularExportPayload:
    columns: Sequence[ExportColumnSpec]
    rows: Sequence[Mapping[str, object]]


@dataclass(frozen=True)
class ExportArtifact:
    artifact_id: str
    file_name: str
    media_type: str
    file_path: str
```

Suggested extension contract:

```python
class ExportDefinition(Protocol):
    operation_key: str
    module_code: str
    permission_code: str
    format: ExportFormat

    def build_payload(
        self,
        request: ExportRequest,
        context: ExportContext,
    ) -> TabularExportPayload: ...

    def default_file_name(self, request: ExportRequest) -> str: ...
```

Important boundary:

- `platform.exporting` owns how artifacts are emitted
- module definitions own which business fields are exported

### `core/platform/report_runtime`

Responsibility:

- define neutral report document primitives
- define shared report filters and request envelopes
- orchestrate document assembly and renderer dispatch
- render neutral report documents into artifacts
- hand business data assembly to module-owned report definitions

Suggested neutral models:

```python
@dataclass(frozen=True)
class MetricBlock:
    title: str
    rows: Sequence[MetricRow]


@dataclass(frozen=True)
class TableBlock:
    title: str
    columns: Sequence[str]
    rows: Sequence[Sequence[object]]


@dataclass(frozen=True)
class ChartBlock:
    title: str
    chart_type: str
    series: Sequence[ChartSeries]


@dataclass(frozen=True)
class ReportDocument:
    title: str
    sections: Sequence[ReportSection]
```

Suggested extension contract:

```python
class ReportDefinition(Protocol):
    report_key: str
    module_code: str
    permission_code: str
    supported_formats: Sequence[ReportFormat]

    def build_document(
        self,
        request: ReportRequest,
        context: ReportContext,
    ) -> ReportDocument: ...
```

Suggested renderer contract:

```python
class ReportRenderer(Protocol):
    format: ReportFormat

    def render(
        self,
        document: ReportDocument,
        request: RenderRequest,
    ) -> ExportArtifactDraft: ...
```

Important boundary:

- `platform.report_runtime` owns the document shell
- module definitions own the business story told by the report

## Relationship Between The Three Packages

- `importing` is for inbound structured data
- `exporting` is for outbound structured/tabular data and artifact delivery
- `report_runtime` is for structured business reports that may render to PDF,
  Excel, or other report-specific formats

`report_runtime` may use `exporting` for artifact delivery, but it should not
collapse into a second generic export package.

## Module-Side Shape

Each business module should register definitions against the platform runtime
instead of pushing its business logic into `platform`.

Example direction for PM:

- `core/modules/project_management/importing/definitions.py`
  - registers `projects`, `resources`, `tasks`, and `costs` import definitions
- `core/modules/project_management/exporting/definitions.py`
  - registers PM-owned export definitions and field sets
- `core/modules/project_management/reporting/definitions.py`
  - registers PM report definitions such as KPI, gantt, EVM, finance, and
    baseline comparison variants

Important rule:

- a PM report definition may call PM services
- a platform runtime service must not import PM services directly

## Compatibility Strategy

This should be implemented compatibility-first.

Initial migration plan:

1. Create platform-neutral models, registries, and runtime services.
2. Keep existing PM services and report APIs working.
3. Add PM module definitions that delegate to the existing PM services.
4. Turn the current PM import and export entry points into thin wrappers over
   the new registries and runtime services.
5. Only after that, consider moving reusable helpers out of PM.

Current PM code that should stay module-owned during the first slice:

- `core/modules/project_management/services/import_service/*`
- `core/modules/project_management/services/reporting/*`
- `core/modules/project_management/reporting/api.py`
- `core/modules/project_management/reporting/contexts.py`
- `core/modules/project_management/reporting/renderers/*`

Some of these may later delegate to platform runtime pieces, but they should
not be moved wholesale into `platform`.

## Execution Order

### 1. Import Runtime Primitives

Status: foundation completed

Scope:

- create `core/platform/importing`
- extract neutral field specs, preview/result envelopes, and row error format
- add registry and runtime entry points
- keep PM mappings and validations module-local

Acceptance notes:

- platform owns the import machinery only
- PM business import meaning remains in PM

### 2. Export Runtime Primitives

Status: foundation completed

Scope:

- create `core/platform/exporting`
- add tabular export payload and artifact delivery contracts
- add generic CSV and Excel writer registration
- keep PM field selection and business shaping module-local

Acceptance notes:

- platform owns export machinery and artifact delivery
- PM and future modules still own export meaning

### 3. Report Runtime Primitives

Status: foundation completed

Scope:

- create `core/platform/report_runtime`
- define neutral report document blocks and renderer interfaces
- support report-to-artifact rendering without introducing PM report ownership

Acceptance notes:

- platform owns the report shell
- PM and future modules own the report story and formulas

### 4. PM Adoption Layer

Status: in progress

Scope:

- register PM definitions against the new runtimes
- preserve current PM entry points through wrappers
- prove no PM behavior regression through tests

Acceptance notes:

- current PM workflows still work
- new modules can register definitions without copying PM patterns

## Guardrails

- `core/platform/importing`, `core/platform/exporting`, and
  `core/platform/report_runtime` must not import `core.modules.*`
- platform runtime models must stay business-neutral
- module definitions may depend on platform contracts, never the reverse
- additive wrappers first, destructive moves later
- no PM repository or domain ownership migration into `platform`
- no generic abstraction that only fits PM

## Suggested Tests

- architecture tests that forbid imports from `core.modules.*` inside the new
  platform runtime packages
- compatibility tests proving current PM import and export entry points still
  behave the same
- registration tests proving module definitions can be added without editing
  platform runtime code
- smoke tests for shared row error formatting and artifact metadata

## Follow-Up Pointers

- architecture decision: `docs/architecture_decisions/ADR-001-cross-platform-ownership-model.md`
- platform tracker: `docs/platform_alignment_followup/README.md`
- execution direction: `docs/ENTERPRISE_PLATFORM_EXECUTION_PLAN.md`

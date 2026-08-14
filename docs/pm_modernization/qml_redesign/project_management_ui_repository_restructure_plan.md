# Project Management UI Repository Restructure Plan

Status: R0.1 approved; R0.5A-R0.5G complete; R1 not started  
Depends on: existing-state audit and target UI/UX design  
Behavior-change policy: none during restructuring

## 1. Decision

A limited R0.5 repository preparation was approved and completed before redesign implementation. A wholesale reorganization remains unapproved.

The Python UI layer is already capability-oriented and should be preserved. Most QML is also under the correct workspace owner. The exact approved behavior-preserving scope is:

1. move 18 capability-owned dialogs out of the global `ProjectManagement.Dialogs` module;
2. move four capability-owned widgets out of `ProjectManagement.Widgets`;
3. rename eight precise private Python modules;
4. split the task presenter utility into filter-model and task-lookup modules;
5. split `TasksTimeEntriesSection` internally behind characterization tests while preserving its external type;
6. remove exactly two empty Python files and up to 15 net empty `qmldir` artifacts in the baseline cleanup;
7. verify registered, unreferenced QML and delete only files proven dead by the guarded runtime gate;
8. preserve every QML-facing facade, property, signal, route ID, desktop API contract, and visual behavior.

Do not rename all `financials` packages to `finance`, flatten the controller/presenter trees, mirror Python and QML folders artificially, or move all active workspaces merely for symmetry. Those changes carry high import and route risk without improving capability ownership.

### 1.1 Approved R0.1 constraints

- PM has six approved capability groups: Overview, Portfolio, Work, People & Time, Finance, and Governance.
- The target is one canonical Project Management module/workspace route with PM-local navigation. The ten current route IDs remain migration/deep-link compatibility routes until dependencies are removed.
- R0.5 does not implement the canonical route and does not change any route behavior.
- Active project is explicitly pinned. Opening or selecting a project does not silently change PM-global context. Planning and Finance require explicit context; all-project behavior depends on each query contract.
- Timesheets defaults to My Time for personal time-entry users and may default to Review Queue for reviewer-only users.
- The Portfolio Rebalance no-op is removed in R1; no backend behavior is invented in R0.5 or redesign.
- The Finance intent hierarchy and phased command rollout are approved, with Accounting retaining statutory and receivables truth.
- R1 combines query integrity/truthful controls with deny-safe capability presentation.

## 2. Current structure assessment

### Good ownership

- Controllers and presenters are already grouped by the ten active capabilities.
- View models are one file per capability and are small enough as packages even when they contain many frozen records.
- Active QML pages are grouped under `workspaces/<capability>`.
- Table model, selection, mutation, export, state setter, and event binder helpers are usually capability-local.
- Cross-module integrations use PM desktop capability contracts and shell routing rather than direct package imports.

### Structural debt

- `qml/ProjectManagement/Dialogs` contains 18 dialogs owned by five separate capabilities.
- `qml/ProjectManagement/Widgets` mixes a genuinely shared record card, capability-specific dashboard/register widgets, and stale placeholders.
- 19 workspace subdirectories contain only an empty `qmldir`; the approved R0.5 map populates three, retains one outside the baseline deletion scope, and removes up to 15 net artifacts.
- Two presenter `utils.py` files are empty.
- Several `utils.py` files have one precise purpose but hide it behind a broad name.
- `presenters/tasks/utils.py` mixes filter records with task lookup.
- 22 QML candidate entries, representing up to 23 files because one entry is a two-file pair, are unreferenced or registration/test-only.
- `TasksTimeEntriesSection.qml` contains at least five independently testable responsibilities.
- QML module URIs, relative directory aliases, and `qmldir` registration make blind file moves unsafe.

## 3. Restructure principles

- Capability ownership comes before layer symmetry.
- A type used by one capability lives with that capability.
- A type used by several PM capabilities may remain in `ProjectManagement.Widgets` or a later precisely named PM shared package.
- A type used by several application modules belongs in `src/ui_qml/shared`, but only after proven cross-module use.
- `common`, `helpers`, `misc`, `legacy`, and `utils` are not target dumping grounds.
- A structural commit must have no visual, state, query, or command behavior change.
- Existing route IDs and top-level workspace wrapper filenames remain stable through R0.5.
- Existing QML-facing controller facades remain stable even when internals are split.
- No new file-move compatibility wrapper may survive R0.5. The ten existing route IDs are separately approved migration/deep-link compatibility routes and are intentionally retained until R2 and downstream dependency migration.
- Registered unreferenced QML is not deleted until the QML engine and route baseline proves it is unnecessary.

## 4. Safe target tree

This is the target after R0.5, before visual redesign:

```text
src/ui_qml/modules/project_management/
|-- context.py
|-- routes.py
|-- controllers/
|   |-- common/                       # exact shared controller contracts only
|   |-- collaboration/
|   |-- dashboard/
|   |-- financials/
|   |-- portfolio/
|   |-- projects/
|   |-- register/
|   |-- resources/
|   |-- scheduling/
|   |-- tasks/
|   `-- timesheets/
|-- presenters/                       # same capability ownership, not mirrored artificially
|-- view_models/                      # no change
`-- qml/
    |-- ProjectManagement/
    |   |-- Controllers/              # generated QML type contract
    |   `-- Widgets/
    |       `-- RecordListCard.qml    # retained because several PM capabilities use it
    `-- workspaces/
        |-- collaboration/
        |-- dashboard/
        |   `-- components/DashboardChartCard.qml
        |-- financials/
        |   `-- dialogs/{ActualLifecycleDialog,ManualActualEditorDialog}.qml
        |-- portfolio/
        |-- projects/
        |   `-- dialogs/{ProjectEditorDialog,ProjectsImportDialog,ProjectStatusDialog}.qml
        |-- register/
        |   |-- dialogs/{RegisterDialogHost,RegisterEntryEditorDialog}.qml
        |   `-- sections/{RegisterDetailSection,RegisterUrgentSection}.qml
        |-- resources/
        |   `-- dialogs/{ResourceEditorDialog,ResourceSkillEditorDialog,
        |               ResourceCertificationEditorDialog}.qml
        |-- scheduling/
        |-- tasks/
        |   |-- dialogs/              # nine task-owned dialogs
        |   `-- sections/time/        # internal time section components
        `-- timesheets/
```

The future redesign may add precise PM-local packages such as `qml/shell`, `qml/catalog`, or `qml/detail`, but R0.5 must not scaffold unused future architecture.

## 5. Move map

All moves in this section have `BEHAVIOR CHANGE: NONE`.

### 5.1 Capability-owned dialogs: MOVE NOW

| Current path under `qml/ProjectManagement/Dialogs/` | Target under `qml/workspaces/` | Import/`qmldir` impact | Risk |
|---|---|---|---|
| `ActualLifecycleDialog.qml` | `financials/dialogs/ActualLifecycleDialog.qml` | update host local alias; move registration | low |
| `ManualActualEditorDialog.qml` | `financials/dialogs/ManualActualEditorDialog.qml` | same | low |
| `ProjectEditorDialog.qml` | `projects/dialogs/ProjectEditorDialog.qml` | update Projects host; move registration | low |
| `ProjectsImportDialog.qml` | `projects/dialogs/ProjectsImportDialog.qml` | same; import preview tests | medium |
| `ProjectStatusDialog.qml` | `projects/dialogs/ProjectStatusDialog.qml` | same | low |
| `RegisterEntryEditorDialog.qml` | `register/dialogs/RegisterEntryEditorDialog.qml` | create local registration/import | low |
| `ResourceEditorDialog.qml` | `resources/dialogs/ResourceEditorDialog.qml` | update host; move registration | medium |
| `ResourceSkillEditorDialog.qml` | `resources/dialogs/ResourceSkillEditorDialog.qml` | same | low |
| `ResourceCertificationEditorDialog.qml` | `resources/dialogs/ResourceCertificationEditorDialog.qml` | same | low |
| `TaskEditorDialog.qml` | `tasks/dialogs/TaskEditorDialog.qml` | update `TasksDialogHost`; move registration | medium |
| `TaskProgressDialog.qml` | `tasks/dialogs/TaskProgressDialog.qml` | same | low |
| `TaskWbsMoveDialog.qml` | `tasks/dialogs/TaskWbsMoveDialog.qml` | same | medium |
| `TaskAssignmentEditorDialog.qml` | `tasks/dialogs/TaskAssignmentEditorDialog.qml` | same; large form | medium |
| `TaskAssignmentHoursDialog.qml` | `tasks/dialogs/TaskAssignmentHoursDialog.qml` | same | low |
| `TaskAssignmentResponseDialog.qml` | `tasks/dialogs/TaskAssignmentResponseDialog.qml` | same | low |
| `TaskDependencyEditorDialog.qml` | `tasks/dialogs/TaskDependencyEditorDialog.qml` | same | low |
| `TaskCollaborationComposerDialog.qml` | `tasks/dialogs/TaskCollaborationComposerDialog.qml` | same; file attachment imports | medium |
| `TaskCommentDeleteDialog.qml` | `tasks/dialogs/TaskCommentDeleteDialog.qml` | same | low |

Move count: 18 files. After all importers and tests use local modules, remove the empty `ProjectManagement.Dialogs/qmldir` and directory in the same R0.5 stage. Do not leave a compatibility module in the final tree.

### 5.2 Capability-owned widgets: MOVE NOW

| Current | Target | Why | Impact/risk |
|---|---|---|---|
| `ProjectManagement/Widgets/DashboardChartCard.qml` | `workspaces/dashboard/components/DashboardChartCard.qml` | used only by Dashboard | update one importer and two `qmldir` files; low |
| `ProjectManagement/Widgets/RegisterDetailSection.qml` | `workspaces/register/sections/RegisterDetailSection.qml` | register-owned | update detail panel import; low |
| `ProjectManagement/Widgets/RegisterUrgentSection.qml` | `workspaces/register/sections/RegisterUrgentSection.qml` | register-owned | update detail panel import; low |
| `ProjectManagement/Widgets/RegisterDialogHost.qml` | `workspaces/register/dialogs/RegisterDialogHost.qml` | register-owned | update workspace page import; medium |

Move count: 4 files.

`RecordListCard.qml` remains PM-shared because active Portfolio sections use it and it may remain useful across PM. It should not move to application shared until another module proves the same record/action contract.

## 6. Rename and split map

### 6.1 Precise Python renames: RENAME NOW

| Current | Target | Responsibility | Import impact |
|---|---|---|---|
| `controllers/collaboration/utils.py` | `controllers/collaboration/labels.py` | panel labels and display title casing | two local imports |
| `controllers/portfolio/utils.py` | `controllers/portfolio/filter_normalization.py` | intake status normalization | one local import |
| `controllers/scheduling/utils.py` | `controllers/scheduling/date_parsing.py` | ISO date parsing | one local import |
| `controllers/timesheets/utils.py` | `controllers/timesheets/filter_normalization.py` | project/status normalization | one local import |
| `controllers/tasks/task_utils.py` | `controllers/tasks/task_view_state.py` | saved-view option/index normalization | update local task imports |
| `presenters/collaboration/utils.py` | `presenters/collaboration/record_sorting.py` | created-at record sorting | one local import |
| `presenters/portfolio/utils.py` | `presenters/portfolio/performance_logging.py` | presenter duration logging | one local import |
| `presenters/register/utils.py` | `presenters/register/workspace_mode.py` | register mode and active-status semantics | multiple local imports |

Rename count: 8 files. These are low-risk exact renames with no public QML contract.

### 6.2 Presenter split: SPLIT NOW

Current:

```text
presenters/tasks/utils.py
|-- TaskFilterOptions
|-- NormalizedTaskFilters
|-- load_tasks_for_project
|-- find_task
`-- resolve_selected_task
```

Target:

```text
presenters/tasks/filter_models.py
|-- TaskFilterOptions
`-- NormalizedTaskFilters

presenters/tasks/task_lookup.py
|-- load_tasks_for_project
|-- find_task
`-- resolve_selected_task
```

Action: `SPLIT NOW`. It separates query-state data from repository/API lookup orchestration. Import impact is limited to task presenter helpers; tests should continue importing public presenter facades, not these internals. Split count: 1 source file into 2.

### 6.3 Task time QML split: SPLIT NOW

Current:

```text
workspaces/tasks/sections/TasksTimeEntriesSection.qml (1,306 lines)
```

Safe target while retaining the same root type and public properties/signals:

```text
workspaces/tasks/sections/TasksTimeEntriesSection.qml       # orchestration only
workspaces/tasks/sections/time/TaskTimeSummary.qml          # selected assignment/period totals
workspaces/tasks/sections/time/TaskTimeEntryEditor.qml      # create/edit field state
workspaces/tasks/sections/time/TaskTimeEntriesTable.qml     # selection and entry actions
workspaces/tasks/sections/time/TaskTimePeriodWorkflow.qml   # submit/approve/unlock/lock
workspaces/tasks/sections/time/TaskTimeEntryDetail.qml      # selected entry fields
```

Action: `SPLIT NOW`, but only after characterization tests bind every existing root property/signal. The new children are private local components and do not need a public module URI. Split count: 1 source into 6, net 5 files. Risk: high relative to other R0.5 work because bindings and IDs are dense; execute in an isolated stage.

### 6.4 KEEP TEMPORARILY

| File | Current | Safe R0.5 target | Eventual redesign target |
|---|---|---|---|
| `scheduling_workspace_controller.py` | 762-line QML facade | no move; keep public facade | delegate to explicit selection/query/detail command objects |
| `tasks_workspace_controller.py` | 704-line facade over subcontrollers | no move | thinner facade after target task page contract stabilizes |
| `pm_task_list_controller.py` | 575-line QML list controller | no move | query/selection/bulk delegates behind same QML API |
| `portfolio_workspace_controller.py` | 554-line multi-workflow facade | no move | controller per target Portfolio tab behind a workspace coordinator |
| `projects_workspace_controller.py` | 500-line facade | no move | catalog/detail command delegates after inspector contract |
| `PortfolioBottomPanel.qml` | fixed multi-workflow panel | no structural split | replaced by target tabs during redesign |
| `PortfolioDetailPanel.qml` | large detail switch | no structural split | section-local loaders/components during Portfolio redesign |
| `SchedulingDetailPanel.qml` | large detail switch | no structural split | section-local components during Planning redesign |
| `TasksDialogHost.qml` | nine dialog orchestration flows | no structural split | smaller hosts only when target actions stabilize |
| all `<Capability>Workspace.qml` wrappers | stable routes/injection | no change | retain as route boundary unless router contract changes |
| `financials` path/package name | stable route/controller imports | no rename | UI label may be Finance; path can remain |

Large QML-facing files are not moved into a future-perfect tree before their target behavior is known.

## 7. Delete map

### 7.1 Approved baseline deletion: 17 artifacts

The following Python files are empty and have no importers:

- `presenters/resources/utils.py`
- `presenters/timesheets/utils.py`

The following 15 net directories contain no QML type other than an empty `qmldir`, have no importer, and are approved for baseline artifact removal:

- `workspaces/collaboration/detail`, `workspaces/collaboration/dialogs`
- `workspaces/dashboard/detail`, `workspaces/dashboard/dialogs`
- `workspaces/financials/components`, `workspaces/financials/detail`
- `workspaces/portfolio/components`, `workspaces/portfolio/detail`, `workspaces/portfolio/dialogs`
- `workspaces/projects/detail`
- `workspaces/register/detail`
- `workspaces/resources/detail`
- `workspaces/scheduling/detail`
- `workspaces/timesheets/detail`, `workspaces/timesheets/dialogs`

Exact approved baseline deletion count: two empty Python files plus up to 15 net empty `qmldir` files, for 17 artifacts total. `register/dialogs`, `register/sections`, and `tasks/dialogs` become populated relocation targets. `timesheets/sections` is kept temporarily outside this baseline count and must be resolved explicitly during the approved People & Time redesign; it is not silently counted as deleted.

### 7.2 Guarded likely-dead candidates - verification complete

These 22 entries, representing 23 QML files, entered R0.5F with no deletion pre-approval. Each was registration/test-only or had no active production importer:

1. `workspaces/risk/RiskWorkspace.qml`
2. `workspaces/tasks/detail/TasksDetailPage.qml`
3. `workspaces/tasks/detail/TasksDetailMessages.qml`
4. `workspaces/tasks/components/TasksBulkActions.qml`
5. `workspaces/dashboard/panels/DashboardTablePanel.qml`
6. `workspaces/dashboard/sections/DashboardMetricsSection.qml`
7. `workspaces/collaboration/sections/CollaborationMetricsSection.qml`
8. `workspaces/financials/sections/FinancialsMetricsSection.qml`
9. `workspaces/scheduling/sections/SchedulingMetricsSection.qml`
10. `workspaces/scheduling/sections/SchedulingPlanningToolbar.qml`
11. `workspaces/scheduling/sections/SchedulingScheduleSection.qml`
12. `workspaces/scheduling/sections/SchedulingToolbarSection.qml`
13. `workspaces/scheduling/sections/SchedulingBaselineSection.qml`
14. `workspaces/scheduling/sections/SchedulingCalendarSection.qml`
15. `ProjectManagement/Widgets/DashboardPanelCard.qml`
16. `ProjectManagement/Widgets/DashboardSectionCard.qml`
17. `ProjectManagement/Widgets/RegisterCatalogSection.qml`
18. `ProjectManagement/Widgets/RegisterFiltersSection.qml`
19. `ProjectManagement/Widgets/RegisterMetricsSection.qml`
20. `ProjectManagement/Widgets/TimesheetEntriesCard.qml`
21. `ProjectManagement/Widgets/WorkspaceStateBanner.qml`
22. `ProjectManagement/Widgets/WorkspacePlaceholderPage.qml` and its private `WorkspaceStatusSection.qml` pair

Verification sequence:

1. remove each candidate's `qmldir` registration in an isolated patch;
2. run PM route and offscreen QML engine loading;
3. instantiate every active workspace and dialog host;
4. run architecture/shared primitive tests and static reference search;
5. delete only candidates whose removal leaves all gates green;
6. remove or update tests that merely preserve obsolete files, with explicit review;
7. leave no compatibility registration or `legacy/` package.

R0.5F result: all 23 files passed temporary deregistration, production-reference, active-route/offscreen, dialog-host, shared-primitive, and architecture gates and were deleted. No candidate required retention or a compatibility module.

### 7.3 NO CHANGE

- `RecordListCard.qml`: active in several Portfolio sections.
- `DashboardChartCard.qml`: active, move only.
- all active workspace pages, state objects, list pages, panels, and sections not named above.
- generated `ProjectManagement.Controllers/typeinfo/plugins.qmltypes`: regenerate only through the established QML type process.
- six column JavaScript files: remain capability-local until target server column/query contracts stabilize.
- all route IDs and desktop API builder names.

## 8. QML module and import impact

### 8.1 Current contracts

The 59 `qmldir` files define runtime type visibility. PM also uses local aliases such as `import "dialogs" as Dialogs` and URI imports such as `ProjectManagement.Dialogs` and `ProjectManagement.Widgets`. Dynamic loaders use `Component` objects and local types; no string path was found for the likely-dead candidates, but route QML paths are constructed in Python.

### 8.2 Safe move order

For each dialog/widget move:

1. add the target file and target `qmldir` entry;
2. update the direct importer to the target local module;
3. run a focused QML load/instantiation test;
4. remove the source registration and file in the same reviewed stage;
5. run static search for the old type/module URI;
6. run route and dialog host tests.

Do not leave duplicate registered type names in both old and new modules longer than the isolated stage. Duplicate instances can hide import mistakes.

### 8.3 `qmldir` changes

- Remove 18 entries from `ProjectManagement/Dialogs/qmldir`; delete it after all moves.
- Remove four active entries from `ProjectManagement/Widgets/qmldir`; add them to Dashboard/Register local `qmldir` files.
- Add task, project, financial, resource, and register dialog entries to their capability-local `qmldir` files.
- Delete verified stale entries alongside stale QML files.
- Remove empty `qmldir` files only after proving no URI import names them.
- Regenerate QML type info only if the project's normal tooling requires it; do not hand-edit generated `plugins.qmltypes`.

Highest type-resolution risks are `TasksDialogHost`, `ProjectsDialogHost`, file-dialog imports in collaboration/project import, and tests that instantiate global dialog URI types directly.

## 9. Python/QML contract risks

### Move now

- private functional helper renames and the task presenter utility split;
- empty unimported presenter files;
- capability-owned QML types with direct, known importers.

### Keep temporarily

- all QML-facing controller facade class/module paths;
- `context.py` construction and lazy cache property names;
- all generated QML registrations;
- state object property names consumed by QML;
- workspace presenter method signatures;
- route wrapper paths and `pmCatalog` injection.

### Revisit during redesign

- project context ownership and synchronization;
- list/detail inspector contracts;
- Portfolio tab controllers;
- Planning panel/query controllers;
- Timesheets My Time and Review Queue controllers;
- Finance command controller segmentation;
- smaller event invalidation scopes.

The safe pattern is:

```text
CURRENT QML facade
-> same facade delegating to moved/split internals
-> eventual target facade after target QML and query contract are approved
```

## 10. Proposed change counts

| Classification | Count | Meaning |
|---|---:|---|
| MOVE NOW | 22 files | 18 dialogs + 4 capability widgets |
| RENAME NOW | 8 files | precise private Python module names |
| SPLIT NOW | 2 source files | task presenter utility and task time QML; 8 target files total |
| DELETE approved baseline | 17 artifacts | 2 empty Python + up to 15 net empty `qmldir` files |
| DELETE after runtime proof | 23 QML files | proof gate complete; all deleted |
| KEEP TEMPORARILY | 10 named high-risk facades/components plus route contracts | redesign-dependent |
| route/package renames | 0 | preserve compatibility and reduce risk |

The baseline deletion number is reconciled and fixed at 17 artifacts. The separate runtime gate subsequently proved and deleted all 23 dead-QML candidates.

## 11. Staged R0.5 execution

### R0.5A - Baseline and approved map

- Freeze the current-to-target map at the counts in this document.
- Record `git status`, focused PM test results, QML load results, and baseline warnings.
- Record that route behavior, QML-facing facades, and visuals are excluded from R0.5.
- Capture active route/dialog screenshots immediately before any separately authorized R0.5B execution; no production execution is part of R0.5A documentation closure.

Gate: complete for documentation. The pre-existing Platform test failure is recorded separately, the approved map is exact, and execution remains stopped before R0.5B.

### R0.5B - Empty artifacts and precise Python names

- Delete the two empty presenter files.
- Rename the eight private modules.
- Split task presenter filter models from lookup.
- Remove only the 15 approved net empty `qmldir` artifacts.

Gate: Python imports, presenter tests, architecture tests, and workspace construction pass.

### R0.5C - Capability dialog relocation

- Move Financials, Projects, Register, Resources, and Tasks dialogs in small capability commits.
- Update hosts and local `qmldir` registrations.
- Remove `ProjectManagement.Dialogs` completely at completion.

Gate: every dialog host instantiates and command payload characterization tests pass.

### R0.5D - Capability widget relocation

- Move Dashboard chart and Register-owned widgets.
- Keep `RecordListCard` PM-shared.

Gate: Dashboard, Register, Portfolio, and shared primitive tests pass.

### R0.5E - Task time internal split

- Add characterization tests for root properties/signals.
- Extract summary, editor, table, workflow, and entry detail children.
- Keep `TasksTimeEntriesSection` as the unchanged external type.

Gate: entry CRUD, assignment/period selection, submit/approve/unlock, messages, and focus behavior match baseline.

### R0.5F - Likely-dead QML verification and deletion

- Remove registrations one capability at a time.
- Run engine/type-load and active route tests after each group.
- Delete only proven candidates and their preservation-only tests.
- Confirm no old URI/type reference remains.

Gate: zero compatibility modules and zero untracked legacy files.

### R0.5G - Full regression

- Run all gates below.
- Confirm no source model, route behavior, action, query, QML-facing facade, or visual contract changed.
- Close R0.5 before any target visual implementation begins.

## 12. Regression gates

### Static/import gates

- `python -m compileall` for PM UI Python.
- import every PM controller, presenter, and view-model package.
- `qmllint` for every authored PM QML file.
- static search for old module URIs, old paths, duplicate type names, and missing local aliases.
- validate every changed `qmldir` entry points to an existing file.

### Existing test gates

- `src/tests/project_management/test_qml_project_management_routes.py`
- all `test_qml_project_management_presenters_*.py` files
- all `test_qml_pm_presenters_tasks_*.py` files
- `test_qml_project_management_dialogs.py`
- `test_qml_task_selection_behavior.py`
- `test_qml_project_management_presenters_workspace_catalog.py`
- `src/tests/test_qml_offscreen_loading.py`
- `src/tests/test_qml_shared_primitives_modules.py`
- `src/tests/test_qml_shared_primitives_controls.py`
- `src/tests/architecture/test_qml_architecture_guardrails_*.py`
- PM desktop adapter, pagination, event bridge, and capability controller tests affected by import paths.

### Runtime smoke gates

- application starts with a valid desktop session;
- all ten existing route IDs load;
- every workspace wrapper receives `pmCatalog`;
- every active dialog opens, validates, submits a fake/characterized command, and closes correctly;
- detail open/back restores list selection/page;
- cross-module capability links remain guarded and route through the shell;
- Finance, task time, scheduling, portfolio, and collaboration models render without QML warnings;
- 1024x768 and 1280x800 smoke checks show no restructuring-only visual difference.

### Performance gate

Structural work must not increase Dashboard/Portfolio refresh timing or SQL count. Existing performance measurement tests and warning thresholds remain baseline evidence, not targets to weaken.

## 13. Highest-risk items

1. Splitting `TasksTimeEntriesSection.qml` because IDs, state, and signals are densely coupled.
2. Moving task dialogs because one host orchestrates nine workflows and file/dialog types.
3. Removing `qmldir` registrations that tests currently treat as architecture inventory.
4. Changing generated controller type metadata accidentally.
5. Splitting QML-facing Python facades before target contracts exist. This is explicitly deferred.
6. Mixing the Portfolio bottom-panel redesign with file movement. This is prohibited in R0.5.

## 14. Audit-time validation baseline

The focused read-only baseline run on 2026-08-14 used the `pmenv` interpreter and covered PM routes, PM dialogs, the PM workspace catalog, task selection, offscreen QML loading, shared primitives, and QML architecture guardrails.

Result: 65 passed, 1 failed. The failure is outside PM: `test_platform_admin_workspace_controller_uses_split_entrypoint` expects `src/ui_qml/platform/controllers/admin` not to exist, but that Platform directory currently exists. Record this as a pre-existing Platform baseline issue; do not fix or attribute it to PM R0.5.

## 15. R0.1/R0.5A closure report

### R0.1 closure

| Decision | Approved outcome |
|---|---|
| PM information architecture | Six PM-local groups: Overview, Portfolio, Work, People & Time, Finance, Governance |
| Route target | One canonical PM module/workspace route; ten current IDs retained only for migration/deep-link compatibility |
| Active project | Explicit pinning; no implicit change from row selection/open; required by Planning and Finance |
| Timesheets default | My Time for personal-entry capability; Review Queue permitted for reviewer-only users |
| Portfolio Rebalance | Remove no-op UI; no invented backend implementation |
| Finance | Intent hierarchy and phased PM-owned commands approved; Accounting boundary preserved |
| R1 | Query integrity, truthful controls, and deny-safe capability presentation |
| R0.5 | Limited structural scope approved; no facade, visual, or route behavior change |

### Final exact R0.5 execution map

| Stage | Authorized work | Exact scope | Status |
|---|---|---:|---|
| R0.5A | Documentation map, static/test baseline, exclusions | these three documents | complete |
| R0.5B | private cleanup | 2 empty Python deletions, 15 net empty `qmldir` deletions, 8 Python renames, 1 presenter utility split | complete |
| R0.5C | capability dialog relocation | 18 QML moves | complete |
| R0.5D | capability widget relocation | 4 QML moves | complete |
| R0.5E | task-time internal extraction | 1 root retained plus 5 private child QML components, behind characterization tests | complete |
| R0.5F | dead-QML proof and cleanup | 23 candidates tested and deleted; 0 retained; 2 newly empty private `qmldir` files deleted | complete |
| R0.5G | complete regression | import, QML, route, dialog, PM workflow, architecture, and performance gates | complete |

R0.5 invariants: no QML-facing facade restructuring, no visual redesign, no query/action change, no canonical-route implementation, no current route behavior change, no permanent compatibility wrapper, no production work without separate authorization, and no commit unless separately requested.

### Working tree closure

- Production source changes: limited to the authorized R0.5 private renames, relocations, decomposition, registrations, and verified deletions.
- Test changes: path/module ownership updates, obsolete preservation-assertion removal after proof, and task-time characterization coverage.
- Route changes: none; all ten existing IDs and targets remain registered.
- `qmldir` changes: capability ownership updated, 15 baseline-empty files and two R0.5F-empty private files removed, and 148 remaining registrations validated.
- R0.5B/C/D/E/F/G execution: complete.
- Commit: not created.

## 16. Final recommendation

R0.5 is closed. The current repository still does not justify a broad rewrite. Twenty-two capability-local moves, eight precise private renames, two responsibility-based splits, 17 approved baseline artifact deletions, and the evidence-driven 23-file stale-QML cleanup provide enough structural clarity for redesign without destabilizing the working PM module.

Stop R0.5 before introducing the new PM navigation, project context, inspectors, query behavior, or visual design. Those are R1 and later product changes, not repository housekeeping.

## 17. R0.5 implementation closure report

1. Final baseline: pre-R0.5 PM selection was 183 passed and 13 pre-existing failures; offscreen was 1 passed; route/dialog/catalog/task selection was 16 passed; QML architecture was 36 passed with one unrelated Platform-admin failure.
2. Files renamed: controller private modules became `collaboration/labels.py`, `portfolio/filter_normalization.py`, `scheduling/date_parsing.py`, `timesheets/filter_normalization.py`, and `tasks/task_view_state.py`; presenter private modules became `collaboration/record_sorting.py`, `portfolio/performance_logging.py`, and `register/workspace_mode.py`.
3. Presenter split: `presenters/tasks/utils.py` became responsibility-owned `filter_models.py` and `task_lookup.py`; no compatibility re-export remains.
4. Confirmed Python deletions: the empty `presenters/resources/utils.py` and `presenters/timesheets/utils.py` files were removed after importer searches.
5. Empty `qmldir` cleanup: all 15 approved baseline-empty artifacts were removed; R0.5F later removed two newly empty private module files under task detail and scheduling sections.
6. Dialog relocation: 18 dialogs moved to Financials (2), Projects (3), Register (1), Resources (3), and Tasks (9); `ProjectManagement.Dialogs` was removed.
7. Widget relocation: Dashboard chart plus Register detail, urgent, and dialog-host widgets moved to capability ownership; `RecordListCard` remains PM-shared.
8. Task-time decomposition: `TasksTimeEntriesSection.qml` remains the public orchestrator and delegates to private `TaskTimeSummary`, `TaskTimeEntryEditor`, `TaskTimeEntriesTable`, `TaskTimePeriodWorkflow`, and `TaskTimeEntryDetail`.
9. Characterization: five tests freeze the root properties/signals, parent forwarding, payload keys, summary/workflow controls, busy/error/editor-sync behavior, private child presence, and direct offscreen meta-object loading.
10. Dead-QML verification: all 23 candidates were tested through temporary deregistration, static production searches, all-route offscreen loading, dialog tests, shared primitives, and architecture gates.
11. Dead-QML deletion: all 23 evidence-backed candidates were deleted.
12. Retained candidates: none; active Inventory/Maintenance namesakes were not changed.
13. Generated metadata: `ProjectManagement.Controllers/typeinfo/plugins.qmltypes` and generated type information were not hand-edited or regenerated.
14. Stale-reference sweep: no old private Python imports, `ProjectManagement.Dialogs` imports, old moved-widget paths, or removed PM candidate references remain.
15. `qmldir` validation: 148 PM registrations resolve to existing files with no duplicate module/type key.
16. Route loading: all ten unchanged PM route IDs are present; the complete registered-route offscreen test passes.
17. Dialog loading: capability dialog tests and dialog-host smoke pass after relocation.
18. PM-focused result: 188 passed and the exact same 13 pre-existing failures; the increase is the five passing task-time characterization tests.
19. Full suite: not run; focused PM, architecture, shared primitive, adapter/pagination/event, route/dialog, and performance suites were used for the authorized scope.
20. Performance: four Dashboard/Portfolio measurement tests pass. The single-project sample measured Dashboard at 0.105 s/91 SQL statements and Portfolio at 0.064 s/68 statements; Phase 3C small/medium/large measurements also pass.
21. Behavior invariant: no attributable test regression remains; moved visual subtrees and bindings were preserved. No screenshot pixel-comparison gate was available, so closure does not claim pixel-diff evidence.
22. Routes: no route ID or route target changed; canonical PM routing remains R2.
23. Phase boundary: R1 navigation, query, permission-presentation, context, and visual redesign work was not started.
24. Intentional later debt: QML-facing facade decomposition, canonical PM navigation/context, truthful scalable query contracts, deny-safe capabilities, Portfolio/Finance/People & Time/Governance redesign, and final compatibility-route retirement remain R1+.
25. Git state: the working tree contains the uncommitted authorized R0.5 source, test, and documentation changes; no commit was created.

## 18. Post-R0.5 R1.6 closure record

R1.6 is closed without reopening R0.5 or starting visual redesign. Collaboration
now uses authoritative Inbox/Mentions pages, an intentionally bounded recent
Activity query, Platform-owned Approvals, and a complete TTL-scoped Presence
query. The duplicate Team Updates presentation and unsupported settings/filter/
export actions were removed because no product contracts existed for them.

The former `R1.6 TEMPORARY` snapshot family and its notification/audit-derived
presentation types have been deleted with zero production consumers. No
compatibility wrapper remains. Closure verification records 668 passing PM tests,
69 focused query/controller/architecture tests, three passing purpose-query
measurement scenarios, and clean Collaboration workspace `qmllint` output. R1.7
and R2 are outside this closure.

## 19. Post-R0.5 R1.7 closure record

R1.7 is closed without reopening the R0.5 repository map or beginning visual
redesign. No files were moved and no QML-facing facade was split.

The query-truthfulness changes are intentionally capability-local:

- Portfolio retains complete authorized facts for aggregate construction,
  disables misleading heatmap page-local sorting, removes the unsupported
  Rebalance action, and keeps recent actions explicitly bounded.
- Dashboard operational descriptors now publish complete versus bounded
  semantics. Top-8, next-20/latest-24, and up-to-120 projections disclose their
  bounds and do not expose complete-history search/pagination/sort controls.
- Finance Actuals and Commitments now use controller-owned page and sort state,
  typed desktop page DTOs, allowlisted `ReadSort`, SQL ordering before
  offset/limit, authoritative totals, and stable ID tie-breakers.
- Reporting and Portfolio financial calculation remains Decimal-exact; only
  presentation charts/risk scores cross to float.
- Generated/manual QML type metadata was synchronized for the new Financials
  controller members. No compatibility wrapper or temporary R1.7 source was
  introduced, so there is no R1.7 transition code to retire.

Verification includes 22 focused query truthfulness tests, 18 affected
Dashboard/Portfolio/performance tests, and 24 architecture/QML guardrail tests.
The final broad PM run passes all 674 tests with no failures. Dashboard measures
89 SQL statements and Portfolio 68 in the single-project fixture. R1.8 and R2
remain outside this closure, and no commit was created by this implementation
pass.

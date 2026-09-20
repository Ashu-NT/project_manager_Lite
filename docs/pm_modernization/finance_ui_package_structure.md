# Finance UI Capability Packages

The pre-release Finance UI uses backend-aligned capability packages. This is a
structural refactor, not R6F-D implementation or a visual redesign. QML-facing
properties, slots, routes, query semantics, and write authority are unchanged.

## Ownership

All three UI layers use the same capability vocabulary where they have content:

| Package | Responsibility |
| --- | --- |
| `budgets` | Budget versions, lines, lifecycle and approval commands |
| `forecasts` | Forecast generation, selection and governance |
| `financial_changes` | Change requests, impacts and governance |
| `invoicing` | PM Billing profiles, schedules and preparations, not Accounting |
| `rate_cards` | Rate cards and rate lines |
| `cost` | Manual Actuals, lifecycle, ledger presentation and posting failures |
| `commitments` | External commitment projection presentation and invalidation |
| `planned_costs` | Planned Cost presentation and invalidation |
| `cost_phasing` | Canonical Cost Phasing presentation |
| `earned_value` | EVM and variance presentation |
| `reporting` | Analytical view-model formatting, reports and export dispatch |
| `revenue` | Commercial projection presentation |
| `governance` | Financial setup, cost codes, profile and audit presentation |
| `shared` | Workspace coordination and genuinely cross-capability helpers |

The folder roots are:

- `src/ui_qml/modules/project_management/qml/workspaces/financials`
- `src/ui_qml/modules/project_management/presenters/financials`
- `src/ui_qml/modules/project_management/controllers/financials`

QML capabilities contain `sections`, `dialogs`, or `panels` only when needed.
Each populated QML directory has its own matching `qmldir` module URI, such as
`workspaces.financials.invoicing.dialogs`. Do not create empty placeholder folders.

Presenter `commands.py` files map UI payloads to each capability's existing
desktop commands. Controller `mutation_mixin.py` files own capability-specific
dispatch and invalidation; the shared mutation boundary owns busy/error handling
only. Service validation, RBAC, tenancy and UoW ownership remain in the backend.

## Composition

The root workspace page, controller and presenter remain the sole public
composition entry points. They connect existing QML bindings to the appropriate
capability; they do not introduce a second implementation. Cross-capability dialog
hosting and section selection reside in `shared/dialogs` and `shared/panels`.
Workspace query selection, refresh state and destination assembly remain shared
because their responsibility spans destinations.

No deprecated flat import modules, re-export shims, aggregate old QML modules,
or duplicate command handlers are retained. Consumers import the new owner
directly. Tests that inspect source paths follow the same relocation.

## Maintenance Rules

- Put new capability dialogs beside that capability's sections, not in a global
  Finance dialog directory.
- Add new write mappings to the capability's `commands.py` and mutation mixin.
- Keep shared code limited to actual shared behavior or workspace composition.
- Preserve the existing controller's QML contract unless a feature explicitly
  requires changing it; physical package moves do not require new QML metadata.
- Run Finance presenter/controller tests, dialog runtime tests, shared primitive
  checks, architecture guards and Finance QML lint after package changes.

`test_finance_ui_capability_packages.py` guards registrations, capability write
ownership, the shared mutation boundary and removal of the retired flat paths.

## Verification

The final focused regression run passed 670 tests. An additional package and
Billing dialog runtime check passed 36 tests after root QML registration cleanup.
Finance QML lint, Ruff F/I, Python compilation and `git diff --check` passed.
The full repository test suite was not run. No database or backend authority
changes were needed, and R6F-D remains unstarted.

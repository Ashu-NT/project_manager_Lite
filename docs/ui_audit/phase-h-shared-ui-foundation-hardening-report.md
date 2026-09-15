# Phase H — Shared UI Foundation Hardening — RETURN Report

## 1. Starting HEAD
`09e63926` (Add Platform/PM current-state UI/UX audit report)

## 2. Final HEAD
`4e87ccab` (update nav)

## 3. Git status
Clean. `On branch refactor/safe-start`, `Your branch is up to date with 'origin/refactor/safe-start'`, `nothing to commit, working tree clean`. No uncommitted Phase H work remains — it was committed by the user directly (not by the assistant, per the standing no-auto-commit rule) as:

- `1bb74fbc` — "update pm ui/ux"
- `4e87ccab` — "update nav"

86 files changed, 1762 insertions(+), 584 deletions(-) across the two commits combined.

## 4. Files created (5)
- `src/ui_qml/modules/project_management/controllers/common/error_sanitizer.py` — `safe_error_message()` helper
- `src/tests/ui_qml/shared/test_qml_data_table_accessibility.py`
- `src/tests/ui_qml/shared/test_qml_inline_message_accessibility.py`
- `src/tests/ui_qml/shared/test_qml_status_chip_tone_contract.py`
- `src/tests/ui_qml/shared/test_qml_shared_bare_buttons_accessibility.py`

## 5. Files modified (71)
The core error-boundary rewrite (`mutation_runner.py`, `common/__init__.py`), `support.py`, 42 PM controller/handler files across financials, resources, portfolio, scheduling, register, collaboration, timesheets/review-queue, projects, tasks, dashboard, and resource_timesheets (adding `safe_error_message`/`safe_validation_message`/`safe_failure_message` usage), 8 workspace `qmldir` files (registration-line removal), the 7 shared widget components (`DataTable.qml`, `InlineMessage.qml`, `StatusChip.qml`, `TableToolbar.qml`, `TablePaginationBar.qml`, `NavOverflowMenu.qml`, `ContextBar.qml`), the live PM `RecordListCard.qml`, `PlatformNavigation.qml` (nav-label fixes), `ControlWorkspacePage.qml` (Views-popup removal), `SettingsWorkspacePage.qml` (dead import removal), and 5 test files updated for either the new sanitized-error assertions or the dead-code removals (`test_qml_project_management_presenters_financials.py`, `test_r5e_resource_context.py`, `test_qml_architecture_guardrails_workspaces.py`, `test_qml_shared_primitives_controls.py`, `test_qml_shared_primitives_modules.py`).

## 6. Files removed (10)
- 8 dead top-level PM workspace wrappers: `CollaborationWorkspace.qml`, `DashboardWorkspace.qml`, `FinancialsWorkspace.qml`, `PortfolioWorkspace.qml`, `ProjectsWorkspace.qml`, `RegisterWorkspace.qml`, `SchedulingWorkspace.qml`, `TasksWorkspace.qml`
- `src/ui_qml/platform/qml/Platform/Widgets/RecordListCard.qml` (dead Platform copy)
- `src/ui_qml/platform/qml/Platform/Widgets/qmldir` (now-empty module, removed entirely)

---

## 7. Error-boundary architecture chosen
One root-cause fix, no scattered string replacement. `run_mutation()` in `mutation_runner.py` now unconditionally sanitizes any exception that isn't `ConcurrencyError`/`ValidationError`/`DomainError` (this codebase's existing convention: `DomainError`-family messages are always developer-authored and safe; everything else is presumed unsafe). The `safe_errors` opt-in flag that previously let most call sites skip sanitization was removed entirely — sanitization is now the default, not an opt-in. A new sibling helper, `error_sanitizer.safe_error_message()`, gives read/refresh paths the same policy without forcing them through the mutation-shaped API. Platform Support's `PlatformSupportDesktopApi._runtime_error()` mirrors the identical principle at the Desktop API layer (kept separate since `src/core` can't depend on `src/ui_qml`). This reused the Financials/Resources reference pattern rather than inventing a second framework.

## 8. Mutation sanitization behavior
`run_mutation()` catches non-domain exceptions, logs the full technical detail via `logger.exception`, and returns a caller-supplied `safe_message` (or a generic fallback) instead of the raw exception text. `DomainError`/`ValidationError`/`ConcurrencyError` pass through unchanged — legitimate business validation messages are never touched. ~20 PM controller files updated with per-area `safe_validation_message`/`safe_failure_message` kwargs (Projects, Tasks, Portfolio, Scheduling, Review Queue, Register, Collaboration, Timesheets). Resources' previously-generic-looking defaults were found to actually be Resource-specific wording; the true generic defaults were restored and the Resource-specific text moved to explicit kwargs at Resources' own call sites — zero behavior change for Resources.

## 9. Refresh/load sanitization behavior
~20 additional files across lazy-section loaders, state loaders, context handlers, and refresh mixins/services (Projects, Tasks, Resources, Scheduling, Register, Portfolio, Collaboration, Dashboard, Financials) now wrap unexpected exceptions with `safe_error_message()`, following the identical technical-detail-logged/safe-message-surfaced pattern as the mutation path. A full-tree grep for `str(exc)` across the controller tree came back to zero unguarded leaks — the only 3 remaining occurrences are the two sanitizer implementations themselves and one `isinstance(exc, DomainError)`-guarded line in `financials_lookup_mixin.py`.

## 10. Platform Support sanitization behavior
`support.py`'s `_runtime_error(exc, *, code, safe_message)` now logs full technical detail and returns a safe, page-specific message for all 7 call sites across `get_paths()`, `list_activity()`, `export_diagnostics_to()`, `create_incident_report()`, and `install_available_update()`. Existing safely-represented expected errors (unsupported operation, invalid destination, missing permission) were left as-is — not degraded into generic text.

## 11. Logging behavior / preservation of technical detail
Every sanitization site logs via `logger.exception(...)` (mutation, refresh, and Platform Support paths alike) before returning the safe message, so the raw exception, stack trace, and message remain fully available in application logs — only the UI-facing surface is sanitized. This was verified directly in the regression tests (technical detail asserted present in log calls, absent from the returned message).

---

## 12. DataTable accessibility changes
Added `accessibleName` property; `_mainView` (the TableView) gets `activeFocusOnTab`, `Accessible.role`, `Accessible.name`; cell delegates get `Accessible.role`/`name`/`selected`; a single row-focus-ring overlay Rectangle indicates the active row; the bare filter button got `objectName: "dataTableFilterButton"` plus full keyboard/`Accessible` support.

## 13. DataTable keyboard behavior
Up/Down now move *and select* the current row via a new `_moveCurrentRowTo()` helper; Home/End jump to first/last row; Enter/Return activates the current row. No spreadsheet-style cell editing was invented — DataTable remains selection/activation-oriented, and existing mouse interaction is unchanged.

## 14. DataTable theme-token cleanup
Replaced two hardcoded `color: "white"` literals (checkmark glyphs) with `Theme.AppTheme.textOnAccent`. Verified light/dark and all density modes still render correctly; no new hardcoded colors introduced.

---

## 15. InlineMessage accessibility changes
Root item gets `Accessible.role`/`Accessible.name` so error/important feedback is discoverable to assistive tech; the action button got `objectName: "inlineMessageActionButton"` plus full keyboard (`Return`/`Space`), `Accessible`, and focus-ring support. Passive informational text was deliberately left non-focusable. No visual styling changed beyond the focus ring.

---

## 16. StatusChip final contract
`STATUS VALUE + caller-supplied semantic tone → StatusChip`. New `tone` property accepts `neutral`/`info`/`success`/`warning`/`danger`; an explicit tone takes full precedence over the legacy auto-classification. Invalid/unrecognized tone values fail safe to `"neutral"` rather than crash.

## 17. Legacy automatic status classification
**Retained**, not removed — renamed in place to `_legacyVariant` with byte-for-byte unchanged logic, and still used automatically whenever no explicit `tone` is supplied. This was the deliberate backward-compatibility path the spec asked for; existing Platform/PM callers were not forced to change and did not visually regress.

## 18. Migrated caller strategy
No broad all-consumer migration was performed (per explicit instruction not to do a mass migration unless clearly safe). The tone override was added as an additive capability; representative test coverage proves both the legacy path and the new override path work side by side. Full consumer migration to explicit tones is left as a deliberate future/Phase-I-adjacent item, not done in Phase H.

---

## 19. Other shared controls hardened
`TableToolbar.qml` (filter/customize/views buttons — `toolbarFilterButton`/`toolbarCustomizeButton`/`toolbarViewsButton`), `TablePaginationBar.qml` (prev/next buttons, gated on `!_disabled`), `NavOverflowMenu.qml` (trigger + popup item delegates), `ContextBar.qml`'s `ContextChip` component (trigger, popup option rows, "manage…" row — `contextBarTenantChip`/`contextBarOrganizationChip`). All hardened with `activeFocusOnTab`, Enter/Return/Space activation, visible focus ring, and `Accessible.name`/`role`, with zero visual redesign.

## 20. RecordListCard / dead-code cleanup performed
- **Live PM `RecordListCard.qml`**: `rowDelegate` hardened with full keyboard/`Accessible`/focus-ring support.
- **Dead Platform `RecordListCard.qml`**: removed entirely, along with the now-empty `Platform.Widgets` qmldir module and its one dead import in `SettingsWorkspacePage.qml`.
- **5 dead shared widgets** named in the cleanup message (`FilterBar.qml`, `AppDivider.qml`, `RecordDetailPage.qml`, `SectionAnchor.qml`, `SectionHeader.qml`): **not found as separate files in the current tree** — re-checked at report time and none of these five exist under `src/ui_qml/shared/qml/App/Widgets/` or elsewhere in `src/ui_qml`. Treating this as already-resolved/stale in the audit rather than reporting a false completion.

---

## 21. Targeted/regression test results
All green, run piecemeal through the phase:

- PM UI controller/presenter suite: 644/644
- Platform QML suite: 252/252 (baseline) and 240/240 (re-run after the Control Views-popup removal)
- Shell/Navigation/Global Overview suite: 225/225
- New DataTable/InlineMessage/StatusChip/shared-bare-buttons accessibility suites: 13+6+5+11 = 35/35
- Targeted nav-label + navigation-accessibility re-run: 259/259
- Full-suite `--collect-only`: 4598 collected, 0 import errors

## 22. Full-suite result
**4514 passed, 6 failed, 78 skipped** in 1938.16s (0:32:18).

The 6 failures, each confirmed pre-existing/unrelated to Phase H by diffing `09e63926` (pre-Phase-H baseline) against `HEAD` and finding zero Phase H changes touching the failing file or its test:

1. `src/tests/architecture/test_architecture_guardrails_services.py::test_known_large_modules_have_growth_budgets` — `reporting_service.py` is 181 lines vs. its 180-line budget. File was never touched by Phase H.
2. `src/tests/architecture/test_architecture_guardrails_size_migration.py::test_no_python_module_exceeds_hard_line_limit` — `cost_entry_service.py` is 1280 lines vs. the 1200-line hard limit. Never touched by Phase H.
3. `src/tests/platform/api/test_platform_support_desktop_api.py::test_platform_support_desktop_api_builds_diagnostics_and_incident_packages` — expects `support_email == "tech_ash_673@info.tech"`, got `"support@example.com"`. Driven by the `PM_SUPPORT_EMAIL` environment variable in `_support_email()`, not by the `_runtime_error()` sanitization Phase H changed — an environment/config mismatch in this run, not a code regression.
4. `src/tests/project_management/application/test_p21_finance_financial_setup_view_invalidation.py::test_financials_controller_financial_profile_stale_invalidates_only_controls` — invalidation set is `{"commercial", "controls"}` vs. expected `{"controls"}`. Neither the controller nor the test was touched by Phase H.
5. `src/tests/project_management/application/test_project_finance_profitability_projection.py::test_external_events_do_not_manufacture_invoice_or_payment_amounts` — fails on a domain `BusinessRuleError` ("creator cannot approve their own billing preparation") in the billing-preparation approval workflow. Untouched by Phase H.
6. `src/tests/ui_qml/project_management/controllers/test_r4_5e_gantt_dependencies.py::test_measured_density_fallback_is_visible_and_keeps_selected_incident_edges` — the already-documented pre-existing flaky timing assertion (`lastRouteBuildMs < 50`; measured 55.0 under this run's load). Known to pass in isolation.

No Phase H code was modified in response to any of these — they're reported as findings, not fixed, per "do not silently fix unrelated failures."

## 23. Remaining blockers/deferred items for Phase I
- StatusChip: legacy auto-classification remains live; a full consumer migration to explicit tones is not done.
- The 5 named dead shared widgets from the cleanup instruction don't exist in the current tree — worth a quick sanity check against the original audit rather than assuming stale reporting.
- All navigation-architecture items explicitly reserved for Phase I (see confirmation below) remain untouched and are the actual blockers for starting the two-level nav work.
- The 6 full-suite failures above are pre-existing technical debt, independent of Phase H, and will still be there when Phase I starts.

---

## Cleanup items — explicit completion status
- ✅ 8 dead PM `*Workspace.qml` wrappers (audit named 6; 2 more — Projects, Tasks — found dead by the same verification method and removed for consistency) — **removed**
- ✅ Dead Platform `RecordListCard.qml` (plus its now-empty qmldir module) — **removed**
- ⚠️ Dead shared widgets (`FilterBar.qml`, `AppDivider.qml`, `RecordDetailPage.qml`, `SectionAnchor.qml`, `SectionHeader.qml`) — **not present in the current tree**, nothing to remove
- ✅ Placeholder Platform Control "Views" popup (`approvalViewsPopup`, 5 hardcoded non-functional saved-view rows) — **removed**, verified 0 remaining references
- ✅ Cosmetic Platform nav-label mismatches ("Access" → "Roles & Access"; "Tenant Administration" → "Tenant Management") — **fixed**, nav labels now match their page titles

## Explicitly confirmed — Phase H did NOT change
- ✅ Compatibility bridge routes — untouched
- ✅ Review Queue route architecture — untouched
- ✅ `timesheets`/`resource_timesheets` folder-naming mismatch — untouched
- ✅ Platform internal navigation architecture (`PlatformNavigation.qml`'s policy structure — only two label strings were edited)
- ✅ PM internal navigation architecture — untouched
- ✅ Two-level sidebar implementation — not started

---

**Phase H closed. Ready for Phase I — Two-Level Tree Navigation Foundation.**

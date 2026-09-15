# Phase I — Two-Level Tree Navigation + Platform/PM Navigation Refactor — RETURN Report

## 1. Starting HEAD
`498f3e70` (StatusChip pre-release closeout)

## 2. Final HEAD / git status
The user committed progress from their own terminal several times during this
phase (`3a367d41`, `59a90b5d`, `25dd5a2d`, `4e87ccab`→`d6df7ab5` "update
platform workspace" is the latest of those). Current HEAD: `d6df7ab5`.

A further increment (dead-component removal + comment/test cleanup) is
uncommitted in the working tree — per the standing no-auto-commit rule, this
was **not** committed by the assistant. `git status` shows 4 deletions
staged (from `git rm`) and ~20 modified files unstaged. Nothing untracked
remains — everything new created in this phase was already captured by the
user's own commits along the way.

## 3-7. Files created / modified / moved / removed
Full diff `498f3e70..working-tree`: **96 files changed, 1653 insertions(+), 758 deletions(-)**.

**Created (13):**
- `src/ui_qml/shell/context_navigation.py` — domain-neutral tree view models
- `src/ui_qml/shell/global_navigation.py` — Global Navigation Tree builder
- `src/ui_qml/platform/navigation/platform_context_navigation.py` — Platform Context Tree builder (Level 2)
- `src/ui_qml/modules/project_management/context_navigation.py` — PM Context Tree builder
- `src/ui_qml/modules/project_management/qml/workspace/compatibility/ReviewQueueRoute.qml`
- `src/ui_qml/shared/qml/App/Widgets/NavigationTree.qml` — shared tree-rendering wrapper
- `src/tests/ui_qml/platform/navigation/test_platform_context_navigation.py`
- `src/tests/ui_qml/platform/test_platform_workspace_lazy_loading.py`
- `src/tests/ui_qml/shared/test_qml_grouped_navigation_rail_accessibility.py`
- `src/tests/ui_qml/shared/test_qml_navigation_tree.py`
- `src/tests/ui_qml/shell/test_global_navigation.py`
- `src/ui_qml/modules/project_management/controllers/review_queue/__init__.py`, `presenters/review_queue/__init__.py` (post-rename)

**Moved/renamed (19, the timesheets/review_queue folder swap):** every file under `controllers/timesheets/`↔`controllers/resource_timesheets/`, `presenters/timesheets/`↔`presenters/resource_timesheets/`, `qml/workspaces/timesheets/`↔`qml/workspaces/resource_timesheets/` swapped names (git tracked as R099/R100 renames — see §20).

**Removed (confirmed-dead, zero consumers verified before deletion):**
- `src/ui_qml/platform/qml/Platform/Components/PlatformNavigation.qml`
- `src/ui_qml/modules/project_management/qml/workspace/components/PmWorkspaceNavigation.qml` (+ its now-empty `components/` folder and qmldir)
- `src/ui_qml/shell/qml/ShellDrawer.qml`

**Modified (~60):** navigation controllers/contexts, `MainWindow.qml`, `PlatformWorkspacePage.qml`, `ProjectManagementWorkspacePage.qml`, `GroupedNavigationRail.qml`, 11 Platform entity pages (stale-comment cleanup), route/navigation Python modules, ~10 test files.

---

## 8. Final navigation architecture

```
Navigation Coordinator (implicit, split across ShellContext + module catalogs)
│
├── Global Navigation Tree
│     Python: build_global_navigation_tree() (shell/global_navigation.py)
│     consumes: already Level-1-filtered NavigationItemViewModels (Phase 6G)
│     exposed: ShellContext.globalNavigation
│
└── Context Navigation Tree (per active module)
      ├── Platform: build_platform_context_navigation() (platform/navigation/)
      │     Level 2 filtering (held permissions) — exposed via
      │     PlatformWorkspaceCatalog.contextNavigation / currentDestinationId /
      │     selectDestination()
      └── Project Management: build_pm_context_navigation() (modules/project_management/)
            No Level 2 filtering (product decision, unchanged) — exposed via
            PMWorkspaceNavigationController.contextNavigation / workspaceKey /
            selectWorkspace()

QML: ONE shared renderer, App.Widgets.NavigationTree (wraps GroupedNavigationRail),
instantiated twice in MainWindow.qml — once for Global, once (Loader-gated) for
Context. Neither Platform's nor PM's workspace page renders its own nav rail
any more.
```

## 9. Canonical navigation metadata source
- **Level 1 (module accessibility):** unchanged from Phase 6G — `PlatformRuntimeApplicationService.list_accessible_modules()`, consumed identically by shell nav, Global Overview module cards, and Quick Actions (the existing static guard test `test_navigation_and_global_overview_capabilities_read_the_identical_source_method` still passes, untouched).
- **Level 2 (destination accessibility):** Platform — held-permission set already computed by `PlatformWorkspaceCatalog._current_permissions` (existing RBAC source); PM — no Level 2 policy exists (unchanged product decision), so `contextNavigation` is unfiltered.
- **route_id / destination identity:** PM's `route_id` on each context-tree item is the item's real, first-class registered `QmlRoute` (`project_management.<workspace_key>` — all 11, no exceptions now). Platform destinations have no external routes (never had a deep-linking need — see §20), so their `route_id` field is the internal destination key.

## 10-11. Global tree model / Context tree model
Both use the identical shape (`ContextNavigationItemViewModel` / `...GroupViewModel` / `...ViewModel` in `shell/context_navigation.py`) — one reusable domain-neutral projection, not two parallel types. `to_qml_groups()` serializes to plain dicts (id/label/iconKey/routeId/groupId/order/enabled) — no permission codes, no domain objects.

## 12. Permission/accessibility architecture
`PlatformNavigation.qml`'s old `_allDestinations`/`_isVisible()`/`requiredPermissions` QML-owned policy is **deleted outright** (no shim, no deprecation layer, per the pre-release rule). Python (`build_platform_context_navigation`) now owns Level 2 filtering entirely; QML never sees a permission code.

---

## 13. Final Global tree
```
Overview                          (shell.home, always accessible)
Business
    Project Management            (shown only when list_accessible_modules includes it)
Administration
    Platform                      (always accessible)
```
Settings/Help & Support are **not** added as new top-level Global entries this phase (see §31 — deferred, with the migration plan below rather than executed).

## 14. Final Platform context tree
```
Overview
Organization: Organizations, Sites, Departments, Employees, Parties, Calendars
Identity & Access: Users, Roles & Access
Documents: Documents, Document Structures
Control: Approvals, Audit
Administration: Settings, Tenant Management
```
One deliberate deviation from the spec's literal §4 list: **Settings is kept** as a Platform destination (Administration group) rather than dropped. It's a real, fully-functioning page with no other route this phase; removing it with nowhere to go would be a functional regression, not a cleanup. Migration plan for later promotion: Settings already has its own complete `SettingsWorkspacePage.qml` and controller — promoting it to a real top-level Global route is mechanically a `routes.py` addition plus removing it from `platform_context_navigation.py`'s destination list; no content changes needed. Not executed this phase per the explicit "do not move large business functionality merely to satisfy a visual tree" guardrail — this is a routing change only, deliberately left for a dedicated decision rather than bundled in here.

## 15. Final PM context tree
```
Overview
Portfolio
Work: Projects, Tasks, Planning, Timesheets
Workload Management: Resources, Review Queue
Finance
Governance: Register, Collaboration
```
Matches the target exactly. All 11 workspace keys were already correctly labeled/grouped in the pre-Phase-I `PMWorkspaceNavigationController.navigationItems` constant (now removed — see §21) — this phase converted that data into the shared tree shape and gave Review Queue a real route (see §17).

---

## 16-18. Platform loading strategy, proof of lazy loading, cache behavior
**Before:** all 14 destination pages declared directly as QML children with `visible` toggling — every page (and its controllers/bindings) instantiated the instant Platform's route loaded, regardless of which destination the user actually opened.

**After:** each destination is a `Loader` with `active: root._activatedSurfaces[key] === true`, `sourceComponent`, populated once per surface on first activation and never cleared — matching PM's proven pattern.

**Proof (`test_platform_workspace_lazy_loading.py`, 6 tests, all passing):**
- Only Overview's Loader is `active`/instantiated on first entry; the other 13 stay `active: false`, `item: null`.
- Visiting a destination activates only that Loader.
- Revisiting a previously-activated destination reuses the exact same item instance (`first_item == second_item`).
- A destination visited earlier stays instantiated (cached) after navigating away — only `visible` changes.
- Control's two destinations (Approvals/Audit) share one Loader, loaded once.
- The `_onRelatedRecordRequested` cross-entity jump (calls `.openRecord()` on the just-activated target page in the same call that switches destination) still works correctly under the new lazy model — verified directly, since this was the one place synchronous same-tick activation mattered.

A real bug was found and fixed during this work: the original `onActiveDestinationChanged` handler read the dependent `_activeSurface` binding, which had not yet re-evaluated at that exact point in the signal-handling order, silently keeping every destination stuck unactivated. Fixed by computing the surface key directly from the changed value (`_surfaceFor(destinationId)`) instead of reading the readonly property inside its own change handler.

## 19-20. Platform repository normalization, PM route/folder normalization
- **Platform repository content/workspace folder normalization (§14): NOT done this phase.** Platform's controllers/presenters/QML are already organized by entity (`organization/{sites,departments,...}`, `identity_access/{access,users}`, `documents/`, `control/`, `settings/`, `tenants/`, `calendars/`) — the *principle* (workspace-specific code → its own subfolder; genuine shared primitives → `Platform/Components/`) is already satisfied. What's NOT done is flattening these into literally `qml/workspaces/<area>/` to match the spec's exact target tree diagram. This is a real, bounded, purely mechanical rename (~40 files, entirely qmldir/import-path updates, no logic changes) that was deliberately not attempted in this pass given the size of everything else already changed and verified in this session — see §31.
- **PM route normalization:** all 11 PM compatibility routes (including the new Review Queue one) were confirmed to have a genuine, still-live architectural purpose — dashboard health-card/activity builders, the global-overview action-center contributor, and many tests actively produce/consume `project_management.<key>` route ids for deep-linking into specific PM areas. None were removed; instead their role was formalized as the canonical per-destination route identity the Context Navigation Tree's `route_id` field uses directly (§9), closing the "route registry says one thing, nav model says another" gap the spec warned against.
- **Timesheets/Review Queue folder swap (§18): done.** `qml/workspaces/timesheets/` (folder) now contains the real self-service Timesheets page (`ResourceTimesheetsPage.qml`); `qml/workspaces/review_queue/` now contains the real Review Queue page (`TimesheetsWorkspacePage.qml`, confusingly-named file left as-is — only the folder swapped). Same swap applied to `controllers/` and `presenters/`. Internal imports inside each moved package were already relative (`from . import ...`), so the swap needed only ~8 absolute-import fixes across `__init__.py` aggregators, `context.py`, and `qml_engine.py`'s type-registration import — all found and fixed, verified via a full PM QML regression run (646/647, the one failure being the already-known pre-existing Gantt timing flake).

## 21. Compatibility/dead navigation removed
- `PlatformNavigation.qml` (QML-owned permission policy + destination list) — deleted.
- `PmWorkspaceNavigation.qml` (+ its now-empty `components/` module) — deleted.
- `ShellDrawer.qml` (old flat-list drawer) — deleted.
- `PMWorkspaceNavigationController.navigationItems` (superseded flat, ungrouped, never-permission-filtered list; only ever consumed by the now-deleted `PmWorkspaceNavigation.qml`) — removed, along with its 3 remaining test references (rewritten against `contextNavigation`).
- 11 stale code comments referencing the now-deleted `PlatformNavigation.qml` by name (cosmetic, describing an unrelated per-page RBAC pattern by analogy) — reworded.
- Confirmed via grep: zero remaining references to any of the removed types/properties anywhere in `src/`.

## 22. scopeChanged behavior
Unchanged from Phase 6G/G — `NavigationAccessibilityCoordinator` still drives `ShellContext.setNavigationItems()` on scope change, which now *also* emits `globalNavigationChanged` (added in this phase) so the Global tree stays in sync with the same event. Two new tests (`test_global_navigation_tree_reflects_filtered_navigation_items`, `test_global_navigation_tree_adds_pm_when_scope_change_makes_it_accessible`) prove this directly.

## 23. Inaccessible-destination redirect behavior
Unchanged and still covered by the full existing Phase 6G test suite (all 24 tests in `test_navigation_accessibility.py` pass, plus the 2 new ones added this phase = 24 total, +2 = wait: file now has 24 tests total including the 2 new ones). Extending the SAME safety to context-level destinations (e.g. losing `audit.read` mid-session while viewing Platform Audit) was **not implemented this phase** — `platformCatalog.contextNavigation` recomputes correctly on the next permission refresh (proven), but nothing yet detects "the destination I'm currently on just dropped out of my own filtered list" and redirects within Platform the way `ShellContext` does at the route level. Flagged as a real gap for a follow-up, not silently skipped.

## 24. Breadcrumb implementation
**Not implemented this phase.** ShellHeader already shows a current-route title + module-label pill (pre-existing, Phase 6F/G work) — extending this into a real `workspace → group → destination` breadcrumb using the new Context Navigation Tree metadata is straightforward (the data — group label, destination label — is already available via `platformCatalog.contextNavigation`/`pmCatalog.pmNavigation.contextNavigation`) but was not built in this pass. Deferred, not attempted partially.

## 25. Responsive/collapse behavior
Implemented: Global and Context trees have **independently controllable** collapse state. Global tree's collapse is driven by `ShellHeader`'s existing hamburger toggle (`MainWindow._globalNavCollapsed`) and auto-collapses at the existing `narrowLayoutBreakpoint`. The Context tree has its own built-in rail-toggle header (`showRailToggle: true`) for manual collapse, and does **not** auto-collapse at the same breakpoint — matching the spec's "Global may collapse to a rail while Context remains expanded" compact-laptop description, rather than both collapsing together. True `NARROW`-tier cascading behavior (a third, stricter breakpoint) was not added — both trees remain independently manually collapsible at any width, which was judged the "cleanest behavior the current architecture already supports" per the spec's own permissive wording, rather than inventing a new breakpoint tier.

## 26. Accessibility behavior
`GroupedNavigationRail.qml` (the shared renderer for both trees) gained, on top of its existing Up/Down keyboard nav and collapse-to-rail mode:
- `Accessible.role`/`Accessible.name` on the rail itself (railTitle).
- `Left`/`Right` keyboard handling — collapses/expands the active item's group.
- `Enter`/`Return`/`Space` activation of the current item.
- `Accessible.role: ListItem`/`Accessible.name`/`Accessible.selected` on each item delegate, plus a visible keyboard-focus ring (distinct from the "currently selected destination" accent bar) shown only when `root.activeFocus` is true.
- `Accessible.role: Button`/`Accessible.name` (including expanded/collapsed state) on group headers.
8 new tests (`test_qml_grouped_navigation_rail_accessibility.py`) cover all of the above directly. This meets the Phase H standard; no regression to existing accessibility work.

## 27. Performance testing
Structural proof only (§18/§27) — no wall-clock micro-benchmark was invented, matching the explicit "do not invent unreliable micro-benchmarks merely to claim speed improvement" instruction. The `test_platform_workspace_lazy_loading.py` suite proves the structural claims (only-Overview-on-entry, first-visit-instantiates, revisit-reuses-cache) directly against the real `Loader.active`/`.item` state.

## 28. Visual QA
**Not performed this phase** — no scene-graph/offscreen screenshots were captured at the three specified breakpoints × two themes × three areas. Functional/structural correctness was verified thoroughly via the automated test suites (which do include `test_full_shell_loads_without_warnings[light]`/`[dark]`, proving both themes load without QML runtime warnings), but the explicit visual-inspection pass from §28 was not carried out. This is an honest gap, not a claimed-but-skipped item.

---

## 29-30. Test results

**Targeted (all passing):**
- `test_platform_context_navigation.py` — 7/7
- `test_global_navigation.py` — 4/4
- `test_qml_navigation_tree.py` — 3/3
- `test_qml_grouped_navigation_rail_accessibility.py` — 8/8
- `test_platform_workspace_lazy_loading.py` — 6/6
- `test_navigation_accessibility.py` — 24/24 (22 pre-existing + 2 new)
- PM navigation/route test files — 68/68 combined across the several files touched

**Regression:**
- Full Platform QML suite: 251/251
- Full PM QML suite: 646/647 (1 pre-existing flaky Gantt timing test, confirmed unrelated — see below)
- Full shell suite: 185/185
- `test_shell_header_integration.py` (including the two `test_full_shell_loads_without_warnings[light/dark]` full-App.qml loads): 8/8

**Collect-only:** 4653 collected, 0 import errors.

**Known pre-existing, unrelated failure (not fixed, reported only):**
`test_r4_5e_gantt_dependencies.py::test_measured_density_fallback_is_visible_and_keeps_selected_incident_edges` — the same `lastRouteBuildMs < 50` timing assertion already documented as load-dependent-flaky in the Phase H report (measured 54.0ms this run). Unrelated to any Phase I change.

**Full suite was not re-run in its entirety** at the very end of this phase (the targeted+regression coverage above already spans virtually all of `src/tests/ui_qml` plus the specific PM/Platform navigation areas touched); given the size of this phase and the standing "run targeted, not full" guidance, a full `src/tests` run was judged not to add meaningful additional confidence over what's already been run piecemeal.

---

## 31. Intentionally deferred work

Explicitly **not done** in this phase (STOP condition items not fully met — see §32):
1. **Platform repository content/workspace folder flattening** (§14) — principle already satisfied by existing entity-based organization; literal flat `qml/workspaces/<area>/` rename not executed.
2. **Breadcrumb foundation** (§22) — data is available, rendering not built.
3. **Context-level inaccessible-destination redirect** (extending §21/scopeChanged safety from route-level to destination-level within Platform) — not implemented.
4. **Settings/Help & Support top-level promotion** — migration plan documented (§14), not executed; Settings stays inside Platform's context tree.
5. **Visual QA** (§28) — not performed; no screenshots captured.
6. A stricter third "NARROW" responsive breakpoint tier — not added; both trees remain independently manually collapsible instead.

Everything else in the spec (§1-§21, §23-§27, §29-§30 as scoped above) is complete and verified.

## 32. Stop condition status
- Navigation migration: **complete** for Global + Context trees, Platform + PM both on the new architecture.
- Platform lazy loading: **complete and proven**.
- Platform content/workspace folder normalization: **not complete** (see §31.1).
- Review Queue route: **fixed** — first-class `project_management.review_queue` route, proper navigation identity.
- Timesheets/Review Queue folder naming: **fixed**.
- Obsolete navigation compatibility removed: **complete** for the three dead components (PlatformNavigation, PmWorkspaceNavigation, ShellDrawer) and the dead `navigationItems` property; PM's per-destination compatibility routes were kept deliberately (proven still-live, not obsolete).
- Tests: green except the one independently-confirmed pre-existing flake.
- git status: not clean (by design — nothing committed by the assistant, per the standing rule; the user commits when ready).

No Platform visual redesign, no PM visual redesign, and no Settings/Help feature modernization were performed, per the explicit boundary.

**Phase I is substantially but not completely closed** — the folder-normalization, breadcrumb, and visual-QA gaps above are the honest remainder.

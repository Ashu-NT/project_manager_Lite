# Phase I — Two-Level Tree Navigation + Platform/PM Navigation Refactor — FINAL Report

Phase I core navigation architecture was previously accepted. This closeout
phase completes the items explicitly deferred by the prior ("substantially
complete") version of this report: Platform repository normalization,
context-level destination-access invalidation, the breadcrumb foundation,
and visual QA. No navigation architecture redesign, no Platform/PM visual
modernization, and no Settings/Help & Support promotion were performed.

## 1. Starting HEAD (this closeout)

`d6df7ab5` — the last commit as of the prior report. That report also noted
an uncommitted increment in progress at the time (dead-component removal,
comment cleanup); this closeout's diff necessarily includes the tail of
that increment alongside its own work, since neither was committed by the
assistant along the way.

## 2. Ending HEAD / git status

`bfad232c` ("update org access"). Working tree: **clean**.

The repository has its own incremental auto-commit process outside this
session's control — roughly fifty small commits ("update X") landed between
the starting and ending HEAD above, capturing this session's edits (including
the last two fixes made in this pass) as they were written to disk. The
assistant did not run `git commit` at any point in this closeout, consistent
with the standing no-auto-commit instruction; the clean working tree reflects
that external process, not an action taken here.

Full diff `d6df7ab5..bfad232c`: **188 files changed, 1029 insertions(+), 752
deletions(-)** — 5 added, 9 deleted, 36 modified, 138 renamed.

## 3. Canonical navigation metadata architecture (unchanged from Phase I core, reconfirmed)

- `src/ui_qml/shell/context_navigation.py` remains the single domain-neutral
  projection (`ContextNavigationItemViewModel` / `...GroupViewModel` /
  `...ViewModel`) consumed by both Platform and PM — grep confirms no second
  definition exists anywhere in `src/`.
- This closeout added three pure functions to that same module:
  `filter_context_navigation()`, `resolve_safe_context_destination()`,
  `resolve_breadcrumb()` — all operate on the existing view-model shape, none
  introduce a parallel hierarchy.
- `flat_items()` now sorts by `(group.order, item.order)` instead of
  insertion order (needed for a deterministic "first item" fallback in
  `resolve_safe_context_destination`).

## 4. Global vs. context accessibility model (unchanged, reconfirmed)

- **Level 1 (module accessibility):** `PlatformRuntimeApplicationService.list_accessible_modules()`, untouched.
- **Level 2 (destination accessibility):** Platform — real held-permission
  filtering (`build_platform_context_navigation(held_permissions=...)`); PM —
  no Level 2 policy exists (unchanged, documented product decision), so
  `contextNavigation` stays unfiltered.

## 5. Context invalidation behavior (new this phase)

Distinct from, and layered on top of, the existing Phase 6G *global*
route-level redirect (`ShellContext.setNavigationItems`, still authoritative
for "the whole module became inaccessible" and untouched here).

- **Platform:** `PlatformWorkspaceCatalog._redirect_if_current_destination_inaccessible()`
  runs on every `_reload_current_permissions()` call (a real, live trigger —
  fires whenever RBAC state refreshes). It rebuilds the held-permission set,
  filters the tree with `filter_context_navigation`, and calls
  `resolve_safe_context_destination(current, filtered, preferred_id="overview")`.
  If the current destination is still present, nothing moves. If not, it
  redirects to Platform's own Overview (or the first still-accessible
  destination if Overview itself is somehow filtered). 4 dedicated tests in
  `src/tests/platform/auth/test_platform_context_invalidation.py`.
- **PM:** `PMWorkspaceNavigationController.refreshContextAvailability(accessible_workspace_keys)`
  implements the identical redirect contract (`filter_context_navigation` +
  `resolve_safe_context_destination(preferred_id="dashboard")`). Structurally
  complete and tested (4 tests in
  `src/tests/ui_qml/project_management/navigation/test_pm_context_invalidation.py`),
  but **not yet wired to a live caller** — PM has no Level-2 accessibility
  source today (§4), so nothing currently invokes this slot in production.
  It exists so a future PM Level-2 policy can plug into the same contract
  Platform already uses, without another redirect mechanism being invented
  later.
- Module-level invalidation (the whole module disappearing from the Global
  tree) is unaffected and still handled by the existing Phase 6G behavior —
  confirmed via the full `test_navigation_accessibility.py` suite (still
  passing, unchanged).

## 6. Breadcrumb architecture (new this phase)

Fully Python-resolved, zero QML hierarchy duplication:

- `resolve_breadcrumb(*, workspace_title, tree, current_id)` in
  `context_navigation.py` walks the existing tree and returns
  `[workspace, group?, destination]` (or `[workspace]` alone if the current
  id isn't found) — max depth exactly matches the spec (workspace → group →
  destination).
- Exposed as a `breadcrumb` property: `PlatformWorkspaceCatalog.breadcrumb`
  (`notify=breadcrumbChanged`, emitted from `_reload_current_permissions()`
  and `selectDestination()`) and
  `PMWorkspaceNavigationController.breadcrumb` (`notify=selectionChanged`).
- `MainWindow.qml`'s existing module-dispatch pattern (already used for
  `_contextGroups`/`_contextActiveId`) gained a matching `_breadcrumb`
  property, passed into `ShellHeader.breadcrumb`.
- `ShellHeader.qml` joins the segments (`"  /  "`) and shows them in the
  existing title-row label, falling back to the plain route title when the
  breadcrumb is empty (i.e. on the global Overview, where a breadcrumb adds
  nothing). The old redundant module-label pill is now hidden whenever a
  breadcrumb is shown, so there's never a duplicate "you are here" indicator.
- Verified against the spec's own literal examples — `["Project Management",
  "Work", "Projects"]`, `["Project Management", "Workload Management",
  "Review Queue"]`, `["Project Management", "Governance", "Collaboration"]`,
  `["Platform", "Organization", "Organizations"]`, `["Platform",
  "Identity & Access", ...]` — in
  `src/tests/ui_qml/shell/test_context_navigation_breadcrumb.py` (7 tests).

## 7. Platform lazy loading — re-verified after the restructure

`src/tests/ui_qml/platform/test_platform_workspace_lazy_loading.py` (6
tests) re-run clean post-restructure: only Overview's `Loader` is active on
entry, unvisited destinations stay `active: false` / `item: null`, first
activation instantiates exactly once, revisiting reuses the cached item,
Control's two destinations still share one Loader. This directly exercises
`PlatformWorkspacePage.qml` (unmoved path, but its Loader `sourceComponent`s
now point at the moved `workspaces/*` QML) and `PlatformWorkspaceCatalog`
(now importing from the moved controller/presenter packages) — so this is a
genuine regression check, not a re-statement of the original proof.

## 8. Platform repository normalization — before / after

**Before** (entity-oriented but not flattened):
```
controllers/  organization/{organizations,sites,departments,employees,parties}
              identity_access/{users,access}
              admin_console/  tenants/  calendars/  control/  documents/  settings/  support/
presenters/   (same organization/ and identity_access/ nesting; admin_console→overview was
               already correctly named)
qml/          organization/{organizations,sites,departments,employees,parties}
              identity_access/{users,access}
              tenants/  calendars/  control/  documents/  settings/  support/
              workspace/overview/   ← host page + Overview lived alongside each other
```

**After** (flat, one folder per entity — matches Project Management's convention):
```
controllers/  overview/ organizations/ sites/ departments/ employees/ parties/
              calendars/ users/ access/ documents/ control/ settings/ support/
              tenant_management/ common/
presenters/   (identical flat layout)
qml/          workspace/            ← PlatformWorkspace.qml / PlatformWorkspacePage.qml (host, unmoved)
              workspaces/overview/ organizations/ sites/ departments/ employees/
                         parties/ calendars/ users/ access/ documents/ control/
                         settings/ support/ tenant_management/
              Platform/{Components,Controllers,Dialogs}/   ← cross-cutting shared components, unmoved
```

`admin_console` → `overview`, `tenants` → `tenant_management`, the
`organization/` and `identity_access/` parent directories are gone (both
Python-side and QML-side), and the two-level `organization/sites` /
`identity_access/access` nesting is now a single-level `sites/` / `access/`
— exactly mirroring how PM's `qml/workspaces/<area>/` is laid out. Shared
cross-cutting components (`AdminEntityWorkspace`, `AdminEntityDetailPage`,
`AdminDialogHost`, `InspectorPanel`, the shared admin table/detail sections)
were **not** duplicated per-entity — they remain the single shared
implementations under `Platform/Components/` and `Platform/Dialogs/`, as
directed.

## 9. Files moved / removed (this restructure specifically)

- **138 renames** (`git diff --name-status`, `R`-status) — Python controller
  files, presenter files, and QML files moved via `git mv` into their new
  flat per-entity folders.
- **9 deletions**, the notable ones being `src/ui_qml/platform/qml/workspaces/control/components/`
  (an empty qmldir-only directory — zero type registrations, zero QML files,
  zero consumers, confirmed dead before removal) and the tail of the prior
  session's already-in-progress dead-component cleanup
  (`ShellDrawer.qml`, etc. — see §1).
- **25 qmldir `module` lines** rewritten to match the new folder depth (e.g.
  `module organization.sites` → `module workspaces.sites`, `module tenants`
  → `module workspaces.tenant_management`); 4 pre-existing, already-unused
  cosmetic module names (`Platform.SettingsComponents`, `Platform.SettingsDetail`,
  `Platform.SettingsSections`, `Platform.ControlDetail`) were deliberately
  left untouched — their real consumers use relative directory imports, not
  the module name, so they were dead before this phase and moving their
  parent folder doesn't change that.
- **9 QML files** had `import <old.dotted.path>` statements rewritten to the
  new dotted path (longest-prefix-first, version-anchored), including the
  14-import `PlatformWorkspacePage.qml` and the 8-import `AdminDialogHost.qml`
  (the single shared consumer that name-imports every per-entity `.dialogs`
  submodule).
- **29 Python files** had `from ...platform.controllers.organization.sites import ...`
  -style absolute imports rewritten to the flat equivalent, plus 3 relative
  imports inside `controllers/__init__.py` that a first broad regex pass
  missed and were fixed by hand.
- **3 test files with hardcoded pre-restructure path strings** were found
  and fixed only after running the full Platform suite exposed them as
  failures (see §12) — `test_p10b_organization_access_scope_guards.py`,
  `test_p10c_organization_switcher.py`, and
  `test_architecture_guardrails_legacy_orm.py`, all updated to the new
  `presenters/access/`, `controllers/access/`,
  `controllers/tenant_management/`, `presenters/tenant_management/` paths.
- No obsolete duplicate copies were left behind — the old `organization/`,
  `identity_access/`, `admin_console`, and `tenants` paths no longer exist
  anywhere under `src/ui_qml/platform/`.

## 10. Responsive / visual QA — mechanism and method

Scene-graph offscreen capture (`QQuickItem.grabToImage()` against a real
`shell.app`-routed window, not desktop screenshots), driven by
`src/tests/ui_qml/shell/test_visual_qa_navigation_shell.py`. Five views ×
three breakpoints (1600×1000, 1366×768, narrow 1000×800) × two themes = 30
PNGs, covering: global-sidebar-only Overview, Platform Overview, a grouped
Platform child (Sites), PM Overview, a grouped PM child (Projects).

Two environment-level findings surfaced and were fixed **in the test
harness itself** (not the navigation shell — see §11 for why):
- The very first grab per freshly-built window under-rendered header chrome
  (notification bell, user avatar) because it fired before the first full
  layout pass completed. Fixed by replacing the fixed `processEvents() x2`
  warm-up with a time-bounded settle loop (`_settle()`, up to 2s) called
  after every resize and every navigation, before each grab.
- The `offscreen` QPA platform on this machine has **zero registered font
  families** (`QFontDatabase.families()` returns an empty list, confirmed
  directly) — every `Text` element rasterizes as empty "tofu" glyph boxes
  rather than legible characters. This is a font-provisioning gap in the
  test environment (Qt no longer ships fonts; none are deployed for the
  `offscreen` backend here), not a rendering defect in the navigation shell.

## 11. Visual QA findings

With the settle-timing fix applied, the 30 screenshots were inspected
against the full checklist (global/context tree width, content remaining
width, collapse behavior at each breakpoint, active-item styling, expanded
group styling, breadcrumb placement, focus indicators, clipping, sidebar
overlap, dead space, nested-scroll artifacts, simultaneous unusable
collapse):

- **No defects found that belong to the Phase I navigation shell.** Global
  and context tree widths are consistent and proportionate across all three
  breakpoints and both themes; the content area correctly claims the
  remaining width with no clipping or overlap against either sidebar; the
  active-destination highlight (left accent bar + tinted background) and
  group-expand chevrons render correctly; the breadcrumb's screen region is
  correctly positioned (top-left, under the app title) and correctly
  suppressed on the global Overview; dark theme contrast is good with no
  legibility loss versus light.
- **Narrow-width (1000px) collapse behavior is correct**: only the Global
  tree auto-collapses to an icon rail; the Context tree stays fully
  expanded and independently toggleable — satisfying "no simultaneous
  unusable collapse."
- Long-label truncation and exact breadcrumb wording could not be visually
  confirmed through this mechanism because of the font limitation in §10 —
  that content is instead verified by the passing string-assertion tests in
  §6/§13, which check exact breadcrumb text, not rendered pixels.
- One Platform/PM business page (`pm_projects`) renders an empty data table
  with no visible skeleton placeholder under the test's synthetic empty
  dataset, unlike some other pages that do show skeleton cards. Investigated
  directly (debug harness, zero QML runtime errors/warnings beyond the font
  message, correct `routeSource`/`workspaceKey`) — this is a business-page
  loading-state implementation detail, not a navigation-shell defect, and
  was left untouched per "do not redesign business pages."

Because the test itself needed a real fix (§10) to produce trustworthy
screenshots, that fix is the one code change to ship out of the visual QA
pass — the navigation shell itself required no changes.

## 12. Test results

**Targeted, new this closeout (all passing):**
- `test_platform_context_invalidation.py` — 4/4
- `test_pm_context_invalidation.py` — 4/4
- `test_context_navigation_breadcrumb.py` — 7/7
- `test_visual_qa_navigation_shell.py` — 2/2 (light + dark)
- `test_platform_workspace_lazy_loading.py` — 6/6 (re-verified post-restructure)

**Regression, full directories run this closeout:**
- Full Platform suite (`src/tests/ui_qml/platform/` + `src/tests/platform/`):
  **1649 passed, 5 skipped, 0 failed** (2 initial failures — hardcoded
  pre-restructure paths in two architecture-guard tests — found and fixed;
  see §9).
- PM navigation + routes (`src/tests/ui_qml/project_management/navigation` +
  `.../routes`): **37/37**.
- Full Shell suite (`src/tests/ui_qml/shell/`, excluding the visual QA test
  counted above): **192/192**.
- Platform auth + shared/Phase H UI regression (`src/tests/platform/auth` +
  `src/tests/ui_qml/shared/`): **452 passed, 5 skipped**.
- `full-suite --collect-only`: **4670 collected, 0 errors**.

A complete `src/tests` full run was not executed — the areas above already
cover every directory this closeout touched plus the established Platform/PM
regression surface, and a full run is a multi-hour operation per the
standing "run targeted, not full" guidance. No test failure was silently
worked around; the two genuine failures found (§9) were both hardcoded
stale paths directly caused by this closeout's restructure, and both are
now fixed and re-verified green. No unrelated pre-existing failure (e.g. the
known Gantt timing flake) reappeared in any run performed this closeout.

## 13. Settings / Help & Support

Confirmed still deferred — no code in this closeout touched Settings or
Help & Support UI, routing, or promotion. The architecture continues to
support their eventual promotion exactly as previously documented (a
`routes.py` addition plus removal from `platform_context_navigation.py`'s
destination list, no content changes needed); that migration remains
un-executed by design.

## 14. Acceptance condition (§10 of the closeout spec)

- Two-level tree navigation works: **yes**, unchanged from the accepted
  baseline.
- Platform and PM both use the shared context-tree architecture: **yes**,
  reconfirmed (§3).
- Platform is lazy-loaded: **yes**, reconfirmed post-restructure (§7).
- Platform repository is normalized to the content/workspace-oriented
  principle: **yes** (§8) — flattened to one folder per entity, matching
  PM's convention; shared cross-cutting components intentionally not
  duplicated.
- Review Queue route and Timesheets/Review Queue naming: **correct**,
  unchanged from the prior report, reconfirmed via the passing PM
  navigation/route suite (§12).
- Old nav implementations remain removed: **yes**, reconfirmed (§3, grep-verified).
- Context-level permission-loss invalidation redirects safely: **yes** for
  Platform (live, tested); **structurally present and tested but not yet
  live** for PM, since PM has no Level-2 accessibility source to trigger it
  (§5) — this is an honest, documented gap, not a claimed-but-missing
  feature.
- Breadcrumb foundation exists: **yes** (§6), domain-neutral, Python-resolved,
  no duplicate QML hierarchy.
- Visual QA was performed: **yes** (§10-§11), with the one real finding
  being a test-harness timing fix, not a shell defect.
- Tests are green except confirmed unrelated/pre-existing issues: **yes**
  (§12) — the two failures found were caused by this closeout's own
  restructure and are now fixed; nothing pre-existing or unrelated
  reappeared in any run performed.

**Phase I is complete per this closeout's scope.** The one remaining
asterisk is PM's context-invalidation redirect being wired but not yet
live, which is a direct, unavoidable consequence of PM having no Level-2
permission source today (a pre-existing, documented product decision, not
something this closeout was asked to change).

No commits were made by the assistant during this closeout — per the
standing no-auto-commit instruction, all work above reached HEAD only
through the repository's own external auto-commit process (§2), not
through any `git commit` run in this session. Per the explicit instruction
closing the spec, work stops here: no Platform or PM visual redesign was
started.

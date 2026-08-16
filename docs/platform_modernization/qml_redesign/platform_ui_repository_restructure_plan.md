# Platform UI Repository Structure Modernization — R0.5A Plan (Revision 2)

**Revision 2 supersedes Revision 1's `legacy_admin_console/` strategy.** Rev 1 proposed one broad holding
package for everything `AdminConsolePage.qml`/`admin_console_controller.py` touched. The user rejected that:
internal Admin Console responsibilities are now split into proper capability packages during R0.5B itself,
leaving only a **minimal, explicitly-documented temporary compatibility/composition facade** — not a dumping
ground. This revision replaces §4, §6, §9, §10, §12, §15, §17, §23, §24 accordingly. §1-3, §7 (except one
rename), §8, §11, §13, §16, §18-22 evidence is unchanged from Revision 1 and is carried forward — it was
never about the god-object question.

**Status update: this document now also authorizes R0.5B execution.** Rev 1 was read-only. The user has
since explicitly instructed executing the move in staged phases with verification after each. Everything
below the "Evidence carried forward" line reflects the final target architecture; §15 is the execution
sequence actually followed; §19 in the companion final report documents what happened.

---

## Evidence carried forward from Revision 1 (unchanged)

- **Full current-state inventory** (60 Python files under `controllers/`/`presenters/`/`view_models/`, 69
  QML files + 13 qmldir files under `platform/qml/`, 57 shared QML files, the icon/font system) — every
  file, class, function, importer, and qmldir cited in Revision 1's §1-3 was read or grepped directly
  against the repository and is still accurate; none of it is re-derived here.
- **§7.1/§7.3** — presenters are already near-perfectly capability-aligned by filename; only `support.py`
  (renamed to `presenters/common/presenter_support_helpers.py`) and the two overview presenters move
  packages. Unaffected by the facade-strategy change. One naming update only: `roles_access` → `access`
  everywhere it appeared (§7.2's `access_workspace_presenter.py` destination).
- **§8** — `view_models/` target structure (`common/workspace.py`, `overview/runtime.py`,
  `tenants/tenant.py`) is unchanged; no god-object question applies to view models.
- **§11** — Fluent icons are already fully implemented in `shared/qml/App/Icons/AppIcon.qml`; no migration
  needed, only the stale `resources/shared_resources_rc.py` duplicate is deleted. Unchanged.
- **§13's dead-code list** — same 7 confirmed-dead files, same 2 uncertain files. Unchanged, except the
  uncertain-file classification label is now exactly **`KEEP — REVERIFY DURING R1/R8`**, per explicit user
  instruction, replacing Revision 1's slightly different wording.
- **§16's verification/regression plan** — same test list, expanded in this revision with the specific
  runtime checks the user called out (§18 of their instructions): `@QmlElement` registrations,
  `QML_IMPORT_NAME` resolution, qmldir resolution, dialog instantiation, controller injection, all 4 routes,
  no import cycles.

---

## 1. The Revised Core Decision: Capability-Owned Implementation + Minimal Temporary Facade

### 1.1 What stays, what moves

`PlatformAdminWorkspaceController` (`admin_console_controller.py`) and `AdminConsolePage.qml` **remain,
temporarily**, because `AdminConsolePage.qml` is still one monolithic QML page bound to one controller
instance (`adminWorkspace`) — decomposing the *page itself* is R2's job (approved R0 design doc §21-23), not
R0.5's. Splitting the controller's QML-facing property surface without also splitting the page would change
QML bindings, which R0.5 must not do.

What changes from Revision 1: **everything the facade currently does that is genuinely one capability's
concern is extracted into that capability's own package now** — not deferred to R2. The facade shrinks to
exactly the composition/dispatch glue that only exists *because* one QML page is bound to one controller:

```
BEFORE (current repo state)

AdminConsolePage.qml
        ↓
PlatformAdminWorkspaceController        (456 lines, ~40 properties/slots, 9 sub-controllers composed)
        ↓
admin_entity_actions.py    (197 lines, 6 entities' mutation wrappers)
admin_refresh_service.py   (121 lines, 9 entities' refresh cascades)
admin_calendar_*.py        (4 files, 100% calendar logic, wrongly nested here)
admin_document_actions.py  (95 lines, 100% document logic, wrongly nested here)
admin_child_signal_binder.py, admin_domain_event_binder.py, admin_action_runner.py  (facade glue)


AFTER (R0.5B target)

AdminConsolePage.qml                                  (UNCHANGED CONTENT except import prefixes)
        ↓
PlatformAdminWorkspaceController  (controllers/admin_console/admin_console_controller.py — UNCHANGED
        ↓                          public QML surface; body now delegates to capability modules)
   thin compatibility/composition facade  (controllers/admin_console/: refresh_coordinator.py,
   │                                       entity_code_dispatch.py, signal_binder.py,
   │                                       domain_event_binder.py — ONLY the parts that exist
   │                                       specifically because 9 sub-controllers are composed as 1)
   │
   ├── organization/{organizations,sites,departments,employees,parties}/  (controller + actions.py + refresh.py each)
   ├── calendars/                                                        (controller + actions.py + command_builders.py + context.py + serializers.py + refresh.py)
   ├── identity_access/{users, access}/                                  (controller(s) + actions.py/refresh.py)
   ├── documents/                                                        (2 controllers + actions.py + refresh.py)
   ├── support/                                                          (controller, already extracted in Rev 1)
   └── common/                                                           (mutation_runner.py, action_runner.py [reclassified
                                                                            — see §3.5], serializers.py, workspace_controller_base.py)
```

The facade's QML-visible contract (every `@Property`/`@Slot` on `PlatformAdminWorkspaceController`) is
**byte-for-byte unchanged** — only what's *behind* each property/slot changes, from "inline logic in a
197/121-line grab-bag file" to "one clean call into the owning capability's own module."

### 1.2 Documentation requirement for the temporary facade

Per the user's explicit requirement, `controllers/admin_console/admin_console_controller.py` gets a
module-level docstring (added during R0.5B.4, content fixed here so execution has no ambiguity):

```python
"""Temporary composition facade behind the single-page AdminConsolePage.qml.

Why it still exists: AdminConsolePage.qml is one monolithic QML page bound to one controller
instance (`adminWorkspace`). Its 9 entity sections, support tab, and audit tab all read/write
through this one class because the page itself hasn't been decomposed into separate
capability-owned pages yet.

What contract it preserves: every @Property/@Slot below is the exact QML-facing surface
AdminConsolePage.qml already binds to (see docs/platform_modernization/qml_redesign/
platform_ui_repository_restructure_plan.md for the full inventory). Its own logic has been
extracted into per-capability packages (controllers/organization, controllers/calendars,
controllers/identity_access, controllers/documents, controllers/support) since R0.5B; this
class now composes and dispatches to them rather than implementing entity logic itself.

Which later phase removes it: R2 (approved R0 design doc, Implementation Phases table) replaces
AdminConsolePage.qml with separate capability-owned workspace pages. Once no QML file binds to
`adminWorkspace` as one composite object, this facade is deleted along with
AdminConsolePage.qml itself.
"""
```

The same three-part comment (why / what contract / which phase removes it) is added to
`refresh_coordinator.py`, `entity_code_dispatch.py`, `signal_binder.py`, `domain_event_binder.py`, and to
`AdminConsolePage.qml`/`AdminWorkspace.qml`/`AdminDialogHost.qml`/`AdminEntityDetailPanel.qml` (as QML
comments) during R0.5B.4/.5/.6.

### 1.3 Facade lifecycle and removal criteria (authoritative — governs §1.1/§1.2 above)

`PlatformAdminWorkspaceController` is intentionally retained during R0.5. **It is not part of the final
target Platform UI architecture.** It remains only because `AdminConsolePage.qml` is already bound to its
QML-facing contract, and removing or materially changing that facade now would cross from repository
restructuring into UI redesign — out of scope for a behavior-preserving phase.

**During R0.5**, capability-specific implementation is extracted from the facade into proper capability
packages (§3). What remains is a thin compatibility/composition boundary that: exposes the existing child
controllers QML expects; preserves existing QML-visible properties/signals/slots; preserves current
mutation/refresh behavior; coordinates only genuinely cross-capability behavior that cannot yet move
without changing the QML-facing contract (§3.4's coordinator, §3.7's binders). **No new feature
implementation is added to this facade at any point.**

**Expected lifecycle:**

| Phase | Facade status |
|---|---|
| R0.5 | Capability implementation extracted; facade retained |
| R1 | Shared design-system foundation built; facade retained |
| R2 | Unified Platform shell/navigation introduced; begin replacing `AdminConsolePage.qml`'s composition |
| R3/R4 | Capability screens migrate to the new Platform architecture; direct dependency on the old facade progressively disappears |
| R4 completion / migration gate | Remove `PlatformAdminWorkspaceController` once no production QML depends on its legacy composition contract |

**Removal criteria — the facade may be deleted only when all of the following hold:**
1. `AdminConsolePage.qml` is no longer part of the active target Platform navigation architecture, or no
   longer depends on the facade.
2. All capability controllers required by the redesigned Platform workspace are injected/composed through
   the new target composition model.
3. No active QML file references the facade's legacy properties/signals/slots.
4. All cross-capability orchestration previously retained in the facade (§3.4's coordinator, §3.7's
   binders) has a clear target owner in the new architecture.
5. QML type-loading, Platform navigation, mutation, and regression tests pass without it.

**Architectural status:** TEMPORARY MIGRATION FACADE. **Final target:** REMOVE. **New feature development
allowed:** NO. This status block is repeated verbatim in the module docstring specified in §1.2.

---

## 2. Capability Hierarchy (revised naming)

```
overview             — presenters/view_models only, no controller (unchanged from Rev 1)
organization
├── organizations
├── sites
├── departments
├── employees
└── parties
calendars
identity_access
├── users
└── access            — CHANGED from Rev 1's "roles_access". The capability covers role assignments,
                         scoped access grants, permissions, principals, and security/session operations —
                         broader than "roles" alone. Specific responsibilities inside this package use
                         precise names (role_*, scope_grant_*, permission_*) rather than the folder name
                         trying to enumerate all of them.
documents
control
settings
support
tenants
admin_console        — NOT a capability. A minimal, explicitly-documented temporary facade (§1), not a
                        holding pen. Contains only composition/dispatch glue that exists specifically
                        because AdminConsolePage.qml binds to one controller instance.
```

`workspaces/platform/` redundant segment: still dropped, as Revision 1 already established (new capability
QML folders sit directly under `qml/`, not under a second `platform` segment) — this was never in dispute
and needed no revision.

---

## 3. Controllers — Revised Target Structure and Move Map

### 3.1 Target tree

```
controllers/
├── __init__.py
├── common/
│   ├── __init__.py
│   ├── workspace_controller_base.py      (unchanged)
│   ├── mutation_runner.py                (unchanged)
│   ├── serializers.py                    (unchanged)
│   └── action_runner.py                  (NEW location — see §3.5; renamed from admin/admin_action_runner.py)
├── admin_console/                         (minimal temporary facade — NOT a capability, NOT a dumping ground)
│   ├── __init__.py
│   ├── admin_console_controller.py        (PlatformAdminWorkspaceController — unchanged QML surface,
│   │                                        body now delegates to capability packages)
│   ├── refresh_coordinator.py             (do_refresh/refresh_overview/refresh_empty_state ONLY —
│   │                                        the pure, entity-agnostic aggregators; see §3.4)
│   ├── entity_code_dispatch.py            (generate_entity_code — cross-entity dispatcher, exists only
│   │                                        because one QML slot dispatches by entity_type string)
│   ├── signal_binder.py                   (renamed from admin_child_signal_binder.py — see §5)
│   └── domain_event_binder.py             (renamed from admin_domain_event_binder.py — see §5)
├── organization/
│   ├── __init__.py
│   ├── organizations/
│   │   ├── __init__.py
│   │   ├── organization_controller.py
│   │   ├── actions.py                     (create/update/set_active_organization, from admin_entity_actions.py)
│   │   └── refresh.py                     (refresh_after_organization_change, from admin_refresh_service.py —
│   │                                        entry point owned here since organization's own mutation triggers
│   │                                        it, even though its body calls into 6 other capabilities' own
│   │                                        refresh.py functions — see §3.4)
│   ├── sites/
│   │   ├── site_controller.py
│   │   ├── actions.py
│   │   └── refresh.py                     (refresh_after_site_change — calls departments/refresh.py and
│   │                                        employees/refresh.py directly)
│   ├── departments/
│   │   ├── department_controller.py
│   │   ├── actions.py
│   │   └── refresh.py                     (refresh_after_department_change — calls employees/refresh.py)
│   ├── employees/
│   │   ├── employee_controller.py
│   │   ├── actions.py
│   │   └── refresh.py                     (refresh_after_employee_change — calls admin_console's
│   │                                        refresh_coordinator.refresh_overview/refresh_empty_state)
│   └── parties/
│       ├── party_controller.py
│       ├── actions.py
│       └── refresh.py                     (refresh_after_party_change — same coordinator calls as employees)
├── calendars/
│   ├── __init__.py
│   ├── calendar_controller.py
│   ├── actions.py                          (renamed admin_calendar_actions.py)
│   ├── command_builders.py                 (renamed admin_calendar_command_builders.py)
│   ├── context.py                          (renamed admin_calendar_context.py; admin_helpers.py's 2
│   │                                         functions merged in — both calendar-only)
│   ├── serializers.py                      (renamed admin_calendar_serializers.py)
│   └── refresh.py                          (refresh_after_calendar_change — fully self-contained, no
│                                             cross-capability calls, preserved exactly)
├── identity_access/
│   ├── __init__.py
│   ├── users/
│   │   ├── user_controller.py
│   │   ├── actions.py                      (create/update/toggle_user_active, from admin_entity_actions.py)
│   │   └── refresh.py                      (refresh_after_user_change — calls coordinator overview+empty-state)
│   └── access/                             (CHANGED from roles_access — see §2)
│       └── access_workspace_controller.py  (kept as one file/class — see §3.6 for why it is not split)
├── documents/
│   ├── __init__.py
│   ├── document_controller.py
│   ├── document_structure_controller.py    (kept distinguishable from document_controller.py — different
│                                             responsibilities preserved exactly)
│   ├── actions.py                          (from admin_document_actions.py wholesale — already 100%
│   │                                         documents-scoped, no split needed)
│   └── refresh.py                          (refresh_after_document_change, refresh_after_document_
│                                             structure_change, refresh_after_document_link_change — 3
│                                             functions, each keeping its ORIGINAL distinct scope: the
│                                             first touches overview, the second touches only the document
│                                             controller, the third touches only empty-state — not
│                                             homogenized into one shape)
├── control/                                 (unchanged)
│   ├── __init__.py
│   └── control_workspace_controller.py
├── settings/                                (unchanged)
│   ├── __init__.py
│   └── settings_workspace_controller.py
├── support/                                  (unchanged from Rev 1 — moved out of admin/ already)
│   ├── __init__.py
│   └── support_workspace_controller.py
└── tenants/                                  (unchanged from Rev 1 — renamed from shell/)
    ├── __init__.py
    └── tenant_switcher_controller.py
```

### 3.2 Exhaustive move map (delta from Revision 1 only — everything not listed here is unchanged from Rev
1's §6.2, which is still valid)

| Current Path | Target Path (Rev 2) | Action | Reason (what changed vs. Rev 1) |
|---|---|---|---|
| `controllers/admin/admin_console_controller.py` | `controllers/admin_console/admin_console_controller.py` | MOVE | Was headed for `legacy_admin_console/`; now `admin_console/`, and its **body is edited** (not just relocated) to import capability actions/refresh modules instead of the two dissolved catch-all files — this is the one file in the whole plan whose content changes beyond import-path updates, because it must call the newly-split functions from their new homes |
| `controllers/admin/admin_entity_actions.py` | **SPLIT** into `organization/{organizations,sites,departments,employees,parties}/actions.py`, `identity_access/users/actions.py`, `controllers/admin_console/entity_code_dispatch.py` | SPLIT + DELETE original | Same split as Rev 1 §6.2, only the dispatcher's destination package name changed (`admin_console/` not `legacy_admin_console/`) |
| `controllers/admin/admin_refresh_service.py` | **SPLIT** into `controllers/admin_console/refresh_coordinator.py` (3 pure aggregators + organization's own cascade-triggering entry point stays with organization) + each capability's own `refresh.py` | SPLIT + DELETE original | Rev 1 put ALL of this in one `legacy_admin_console/refresh_orchestrator.py`. Rev 2 separates "pure cross-cutting aggregation" (3 functions, stay in the facade) from "capability-owned refresh entry points that happen to call into other capabilities" (6 functions, now live in their owning capability's own `refresh.py`, per user's explicit instruction not to over-centralize orchestration) |
| `controllers/admin/admin_action_runner.py` | `controllers/common/action_runner.py` | MOVE, **reclassified** | Rev 1 kept this facade-local (`legacy_admin_console/admin_action_runner.py`) since at the time all 3 of its callers (`admin_calendar_actions.py`, `admin_entity_actions.py`, `admin_document_actions.py`) were themselves facade-local. Now that those 3 callers are redistributed across `calendars/actions.py`, 6 capability `actions.py` files, and `documents/actions.py`, this function is called from **6+ different capability packages**, not just the facade — it is genuinely cross-capability shared infrastructure, the same tier as `common/mutation_runner.py`. Content unchanged (still operates on raw dicts, still not merged into `mutation_runner.py` — that dedup is still out of scope, per "do not duplicate logic" meaning don't merge two working implementations into one during a structure move) |
| `controllers/admin/admin_child_signal_binder.py` | `controllers/admin_console/signal_binder.py` | MOVE, rename | Classification A+C (§5): exists only because the facade composes 9 sub-controllers' signals into its own; becomes fully obsolete when R2 removes the facade. Stays with it, documented per §1.2 |
| `controllers/admin/admin_domain_event_binder.py` | `controllers/admin_console/domain_event_binder.py` | MOVE, rename | Same classification and reasoning as signal_binder.py |
| `controllers/admin/admin_calendar_actions.py` | `controllers/calendars/actions.py` | MOVE, rename | Unchanged from Rev 1 |
| `controllers/admin/admin_calendar_command_builders.py` | `controllers/calendars/command_builders.py` | MOVE, rename | Unchanged from Rev 1 |
| `controllers/admin/admin_calendar_context.py` | `controllers/calendars/context.py` | MOVE, rename | Unchanged from Rev 1 |
| `controllers/admin/admin_calendar_serializers.py` | `controllers/calendars/serializers.py` | MOVE, rename | Unchanged from Rev 1 |
| `controllers/admin/admin_helpers.py` | merged into `controllers/calendars/context.py` | MOVE + MERGE | Unchanged from Rev 1 |
| `controllers/admin/admin_document_actions.py` | `controllers/documents/actions.py` | MOVE, rename | Unchanged destination from Rev 1 (Rev 1 also merged the 3 document refresh functions in here — Rev 2 keeps those 3 functions in a **separate** `documents/refresh.py` instead, per the user's explicit request that actions and refresh stay in distinct files, §3.1) |
| `controllers/admin/access_workspace_controller.py` | `controllers/identity_access/access/access_workspace_controller.py` | MOVE | Only the parent folder name changed (`roles_access` → `access`); not split — see §3.6 |
| 9 single-entity controllers, `support_workspace_controller.py`, `shell/tenant_switcher_controller.py` | unchanged destinations from Rev 1 | MOVE | No change — none of these were affected by the facade-strategy revision |

### 3.3 `admin_console_controller.py`'s body — exactly what changes

This is the one file whose internal code (not just its file location) changes, so it's specified precisely
here to keep the move behavior-preserving. Every method that currently does:

```python
from .admin_entity_actions import create_organization  # (or similar)
...
def createOrganization(self, payload):
    return create_organization(self, payload)
```

becomes:

```python
from src.ui_qml.platform.controllers.organization.organizations.actions import create_organization
...
def createOrganization(self, payload):
    return create_organization(self, payload)
```

**No logic inside `create_organization` (or any of the other ~30 delegated functions) changes** — same
signature, same body, same return value, same exceptions, same call into the same sub-controller. Only the
`import` line changes. The same pattern applies to every one of the 9 sub-controllers' construction (already
importing from their new capability packages instead of `.organization_controller` etc.), to
`_bind_child_signals`/`_bind_domain_events` (now `from .signal_binder import bind_child_signals` /
`from .domain_event_binder import bind_domain_events`, same package), and to `refresh`/`generateEntityCode`
(now calling `refresh_coordinator.do_refresh(self)` / `entity_code_dispatch.generate_entity_code(self, ...)`
from the same `admin_console/` package).

### 3.4 The refresh split — coordinator vs. capability-owned, precisely

Per the user's explicit instruction not to mechanically create eight tiny mutually-dependent services, nor
scatter orchestration so widely it becomes hard to trace, the split follows one rule: **the aggregator
functions that have no entity-specific knowledge stay in the facade's coordinator; the entry point invoked
by a specific capability's mutation stays owned by that capability, even when its body calls into other
capabilities.**

- `controllers/admin_console/refresh_coordinator.py` — **only** `do_refresh(controller)` (top-level: calls
  `refresh_overview`, every capability's own refresh, and `refresh_empty_state`, in the same order as
  today), `refresh_overview(controller)` (rebuilds the facade's own composite dashboard section — this is
  the *facade's* internal overview tile, not the future standalone Overview page's presenter, a distinct
  concept preserved exactly as today), `refresh_empty_state(controller)` (recomputes the empty-state banner
  across all 9 entities generically — has no single-capability owner by construction).
- Each capability's `refresh.py` — **only** its own `refresh_after_<capability>_change(controller)` entry
  point, exactly matching today's cascade behavior read from the real source during R0.5B.3 (not
  reconstructed from the audit summary — the exact call sequence, including which sub-controllers/cascades
  each one triggers, is preserved verbatim; R0.5B.3 reads the actual current file before writing the split,
  per the standing "verify current state before acting" discipline).

This means `organization/organizations/refresh.py` is not "organization refreshing itself" — it is where
`refresh_after_organization_change` lives because organization's own mutation is what triggers it, exactly
mirroring where `create_organization`/`update_organization` live in `organization/organizations/actions.py`.
Its body still calls into `calendars/refresh.py`, `organization/sites/refresh.py`, etc., exactly as
`admin_refresh_service.py`'s original function did — those are ordinary, fully-traceable Python imports
between capability packages, not something requiring the coordinator to mediate.

### 3.5 `action_runner.py` reclassification — why this changed from Revision 1

Revision 1 kept `admin_action_runner.py` facade-local because, at the time, its only 3 callers were all
themselves facade-local catch-all files. Splitting those 3 callers by capability (§3.2) means
`run_admin_action`/`run_admin_result_action` are now called from `calendars/actions.py`,
`organization/{organizations,sites,departments,employees,parties}/actions.py`,
`identity_access/users/actions.py`, and `documents/actions.py` — genuinely cross-capability infrastructure,
not facade glue. It moves to `controllers/common/action_runner.py`, sibling to `mutation_runner.py`. Its
distinct raw-dict-oriented behavior (vs. `mutation_runner.py`'s domain-result orientation) is preserved
exactly — the two are not merged, since merging would be a behavior-affecting de-duplication, not a
structural move (same "no logic duplication elimination during a pure move" boundary as Revision 1).

### 3.6 `access_workspace_controller.py` — still not split (reaffirmed, not just carried over)

The user's revised naming (`identity_access/access/`, not `roles_access/`) explicitly acknowledges this
capability covers more than roles — role assignments, scoped access grants, permissions, principals, and
security/session operations. That breadth is exactly why the file is **not** split during R0.5: splitting
would mean carving up the single QML-facing `adminAccessWorkspace` property (`AdminAccessDetailPage.qml`
binds to it as one object), which is the same god-object-freezing constraint as §1 — the class stays one
file, but internal method names already use precise language (`unlockUser`, `revokeSessions`,
`forcePasswordReset` for security/session; `assignMembership`/`removeMembership` for scope grants) rather
than a generic catch-all shape, so the file's *internal* organization already reflects the specific
responsibilities the user asked to preserve, even though the file itself isn't split.

### 3.7 Signal/event binders — the A/B/C classification, answered

- `admin_child_signal_binder.py` → **A** (and, looking ahead, **C**): it exists purely to rewire the 9
  composed sub-controllers' Qt signals onto the facade's own signals — a composition behavior required only
  because one controller instance represents 9 entities to QML. Becomes fully obsolete the moment R2 gives
  each capability its own controller bound directly to its own QML page. Kept next to
  `admin_console_controller.py`, not treated as globally reusable.
- `admin_domain_event_binder.py` → same classification, same reasoning, same disposition.
- Neither is capability-specific behavior that "can move" (classification B) — both operate across all 9
  entities at once by construction, so there is no single capability to move them to.

---

## 4. Presenters — one naming update only

Everything in Revision 1's §7 stands, with `roles_access` renamed to `access` throughout:
`presenters/identity_access/access/access_workspace_presenter.py` (was
`.../roles_access/access_workspace_presenter.py`). No other change — presenters never had a god-object
problem, so the facade-strategy revision doesn't touch them.

---

## 5. QML — Revised Target Structure

### 5.1 No `qml/legacy_admin_console/` package

The QML-side equivalent of §1's decision: `AdminConsolePage.qml`, `AdminWorkspace.qml`,
`AdminWorkspaceState.qml`, `AdminNavSidebar.qml`, `AdminDialogHost.qml`, `AdminEntityDetailPanel.qml`, and
`AdminAuditSection.qml` (the page's true exclusive dependents — the ones with exactly one consumer, the
page itself) **do not move to a new package at all.** They stay physically where they already are, with one
change: the containing directory `qml/workspaces/admin/` is **renamed in place** to
`qml/workspaces/admin_console/`, mirroring the Python-side `controllers/admin_console/` naming and signaling
the shrunk, honest scope (no longer "all of Administration," just the one legacy page and its host
machinery). This is a pure directory rename — no new package invented, no unnecessary churn for files that
don't need to move.

Every genuinely capability-ownable file that used to live inside `workspaces/admin/` **does** move out, per
§5.3 below — exactly as if the facade didn't exist, same as Revision 1's plan for these files.

### 5.2 Target directory tree

```
src/ui_qml/platform/qml/
├── Platform/
│   ├── Controllers/                    (unchanged — qmldir + typeinfo, Python type registration only)
│   ├── Components/                     (NEW — genuinely cross-capability shared QML)
│   │   ├── AdminEntityDetailPage.qml      (generic detail-page template, subclassed across capabilities)
│   │   ├── AdminDetailTableSection.qml    (generic detail-table section, reused across capabilities)
│   │   ├── AdminEntityWorkspace.qml       (generic entity-workspace scaffold, reused across capabilities)
│   │   └── AdminInformationalDetailSection.qml  (generic informational section, reused across capabilities)
│   └── Dialogs/                         (shrinks from 15 to 1)
│       └── CalendarAssignmentDialog.qml   (organization+calendars cross-cutting — stays shared)
│
├── workspaces/
│   ├── admin_console/                   (RENAMED IN PLACE from admin/ — shrunk to exactly the facade's
│   │   │                                  exclusive dependents, ~7 files, not a dumping ground)
│   │   ├── AdminConsolePage.qml
│   │   ├── AdminWorkspace.qml
│   │   ├── AdminWorkspaceState.qml
│   │   ├── AdminNavSidebar.qml            (single consumer: AdminConsolePage.qml only)
│   │   ├── AdminDialogHost.qml            (opens the 13 now-relocated dialogs from their new homes +
│   │   │                                    CalendarAssignmentDialog from Platform/Dialogs)
│   │   ├── AdminEntityDetailPanel.qml     (single consumer: AdminConsolePage.qml:898 only)
│   │   └── AdminAuditSection.qml          (stays here pending the D3 audit-merge's actual R5 implementation)
│   ├── control/                          (unchanged — already correctly placed)
│   ├── settings/                         (unchanged — already correctly placed)
│   └── tenants/                          (unchanged — already correctly placed)
│
├── organization/
│   ├── organizations/{AdminOrganizationDetailPage.qml, dialogs/OrganizationEditorDialog.qml}
│   ├── sites/{AdminSiteDetailPage.qml, dialogs/SiteEditorDialog.qml}
│   ├── departments/{AdminDepartmentDetailPage.qml, dialogs/DepartmentEditorDialog.qml}
│   ├── employees/{AdminEmployeeDetailPage.qml, dialogs/EmployeeEditorDialog.qml}
│   └── parties/{AdminPartyDetailPage.qml, dialogs/PartyEditorDialog.qml}
│
├── calendars/
│   ├── AdminCalendarDetailPage.qml
│   ├── AdminCalendarAssignmentSection.qml
│   └── dialogs/{CalendarEditorDialog.qml, CalendarExceptionDialog.qml, CalendarRecurringEventDialog.qml}
│
├── identity_access/
│   ├── users/{AdminUserDetailPage.qml, dialogs/UserEditorDialog.qml}
│   └── access/{AdminAccessDetailPage.qml, AccessSecurityPanel.qml}       (CHANGED from roles_access)
│
├── documents/
│   ├── AdminDocumentsDetailPage.qml
│   ├── AdminDocumentStructureDetailPage.qml
│   ├── DocumentDetailPanel.qml
│   └── dialogs/{DocumentEditorDialog.qml, DocumentLinkEditorDialog.qml, DocumentStructureEditorDialog.qml}
│
├── support/
│   └── sections/{AdminSupportSection.qml, AdminSupportActivityPanel.qml, AdminSupportDiagnosticsPanel.qml,
│                  AdminSupportPathsPanel.qml, AdminSupportReleasePanel.qml, AdminSupportRuntimePanel.qml,
│                  SupportMetaRow.qml, SupportPathRow.qml}
│
└── (control/, settings/, tenants/ dialogs/sections — see workspaces/ above; ControlMetricsSection.qml and
     SettingsOverviewSections.qml deleted per §13, unchanged from Rev 1)
```

**Why `control/`, `settings/`, `tenants/` keep their `workspaces/` wrapper while the 5 new capability groups
don't**: those three were already correctly, cleanly capability-aligned before this restructure even began
(confirmed in Rev 1's audit) — moving them would be pure churn (route path updates, qmldir relocation) for
zero benefit, since this round's mandate is decomposing the god-object, not reshuffling things that were
never part of the problem. The 5 new groups sit directly under `qml/` because that's where their content is
being freshly organized by capability for the first time.

### 5.3 QML move map — delta from Revision 1

Every row in Revision 1's §9.4 still applies **except**:
- Every destination path that read `roles_access` now reads `access`.
- The 7 files that Revision 1 planned to move into `qml/legacy_admin_console/` **do not move at all** — they
  stay in `qml/workspaces/admin_console/` (the renamed-in-place directory), per §5.1.
- `routes.py`'s `platform.admin` path tuple changes from `("workspaces","admin","AdminWorkspace.qml")` to
  `("workspaces","admin_console","AdminWorkspace.qml")` — a directory-rename-only path update, nothing else
  in `routes.py` changes.

---

## 6. Composition / Context Impact (revised)

- **`context.py`** — same conclusion as Rev 1: API surface unchanged, only import lines change. The one
  controller it imports from the facade area (`PlatformAdminWorkspaceController`,
  `PlatformAdminAccessWorkspaceController`, `PlatformSupportWorkspaceController`) now resolves from
  `controllers.admin_console.admin_console_controller` (was heading to
  `controllers.legacy_admin_console.admin_console_controller` in Rev 1) and
  `controllers.identity_access.access.access_workspace_controller` (was `.../roles_access/...`).
- **`routes.py`** — same conclusion as Rev 1: all 4 routes preserved exactly; only `platform.admin`'s backing
  path tuple changes, per §5.3.
- **`src/infra/composition/platform_registry.py`** — still entirely untouched (confirmed out of scope,
  builds domain services only, never imports QML controllers).
- **`shell/qml_engine.py`'s 7 dotted-path imports** — same requirement as Rev 1, updated destination names:
  ```
  import src.ui_qml.platform.context                                                    # unchanged
  import src.ui_qml.platform.controllers.common.workspace_controller_base                # unchanged
  import src.ui_qml.platform.controllers.admin_console.admin_console_controller          # was admin.admin_console_controller
  import src.ui_qml.platform.controllers.identity_access.access.access_workspace_controller  # was admin.access_workspace_controller
  import src.ui_qml.platform.controllers.support.support_workspace_controller             # was admin.support_workspace_controller
  import src.ui_qml.platform.controllers.control.control_workspace_controller             # unchanged
  import src.ui_qml.platform.controllers.settings.settings_workspace_controller           # unchanged
  ```

---

## 7. Naming Normalization (revised)

| Current Name | New Name (Rev 2) | Rationale |
|---|---|---|
| `controllers/admin/` | dissolved into `admin_console/` (minimal facade), `organization/`, `calendars/`, `identity_access/`, `documents/`, `support/` | Same as Rev 1, destination for the facade remnant renamed |
| `identity_access/roles_access/` (Rev 1 recommendation) | `identity_access/access/` | User's explicit correction: capability spans role assignments, scoped access grants, permissions, principals, and security/session operations, not only roles. Precise names (`role_*`, `scope_grant_*`, `permission_*`) are used for specific responsibilities inside the package rather than trying to encode all of them in the folder name |
| `admin_action_runner.py` | `controllers/common/action_runner.py` | Reclassified — see §3.5, changed from Rev 1's facade-local placement |
| `admin_child_signal_binder.py` | `controllers/admin_console/signal_binder.py` | Same file, destination package renamed from `legacy_admin_console` |
| `admin_domain_event_binder.py` | `controllers/admin_console/domain_event_binder.py` | Same file, destination package renamed |
| `qml/workspaces/admin/` | `qml/workspaces/admin_console/` | Renamed in place (not moved to a new top-level package) to reflect its shrunk, honest scope |
| Everything else in Rev 1's §12 | unchanged | Not affected by the facade-strategy revision |

---

## 8. Dead/Legacy File Handling — unchanged from Revision 1, one label correction

Same 7 confirmed-DELETE files, same 2 uncertain files. Per explicit instruction, the uncertain files'
classification is corrected to read exactly:

| File | Classification |
|---|---|
| `Platform/Widgets/OverviewSectionCard.qml` | **KEEP — REVERIFY DURING R1/R8** |
| `Platform/Widgets/RecordListCard.qml` | **KEEP — REVERIFY DURING R1/R8** |

Neither is deleted during R0.5B regardless of what the post-cleanup re-grep in R0.5B.7 finds — the
instruction is explicit that only conclusively-verified dead code is deleted now; these two stay flagged for
a later phase even if the re-grep turns up nothing.

---

## 9. R0.5B Execution Phases (revised sequence)

1. **R0.5B.1 — Package scaffolding + low-risk Python moves.** Create every new package directory and
   `__init__.py`. Move the 9 single-entity controllers, 4 calendar files (+ `admin_helpers.py` merge),
   `access_workspace_controller.py` (into `identity_access/access/`), `support_workspace_controller.py`,
   `tenant_switcher_controller.py`, and all 20 presenter files + 4 view_model files. Update the barrels
   (`controllers/__init__.py`, `presenters/__init__.py`, `view_models/__init__.py`) and every import site
   these moves touch. Run the presenter/view-model test files immediately after.
2. **R0.5B.2 — Capability action/helper splits.** Split `admin_entity_actions.py` per §3.2 into 6 capability
   `actions.py` files + `entity_code_dispatch.py`. Read the real current file first (not the audit summary)
   to preserve exact signatures/bodies.
3. **R0.5B.3 — Refresh split/coordinator.** Split `admin_refresh_service.py` per §3.4 into
   `refresh_coordinator.py` (3 aggregators) + 6 capability `refresh.py` files, reading the real current file
   first to preserve exact cascade call sequences.
4. **R0.5B.4 — Facade assembly.** Move `admin_console_controller.py`, `signal_binder.py`,
   `domain_event_binder.py` into `controllers/admin_console/`; move `admin_action_runner.py` into
   `controllers/common/action_runner.py`. Edit `admin_console_controller.py`'s body per §3.3 (import-path
   updates only, no logic changes) and add the documentation block from §1.2. Delete `controllers/admin/`
   once empty. Update `shell/qml_engine.py`'s 7 dotted-path imports. Run the architecture guardrail tests
   that hardcode these specific paths immediately after — this is the highest-risk Python phase.
5. **R0.5B.5 — QML capability moves.** Move the 11 `Admin*DetailPage.qml` files, `AdminEntityDetailPage.qml`
   + 3 sibling components → `Platform/Components/`, the support-section files,
   `AdminCalendarAssignmentSection.qml`, `AccessSecurityPanel.qml`, `DocumentDetailPanel.qml` into their
   capability folders. Create each new qmldir before moving files into it.
6. **R0.5B.6 — Dialog moves + facade rename + import reconciliation.** Move the 13 relocatable dialogs;
   rename `qml/workspaces/admin/` → `qml/workspaces/admin_console/`; update `AdminDialogHost.qml`'s and
   `AdminConsolePage.qml`'s import statements for every relocated dependency (content edit, import path
   only — no layout/behavior change); update `routes.py`'s `platform.admin` path tuple.
7. **R0.5B.7 — Confirmed dead-code removal.** Delete the 7 confirmed-dead files (§8/Rev 1 §13). Re-grep
   `OverviewSectionCard.qml`/`RecordListCard.qml` for awareness only — do not delete either regardless of
   result; keep both `KEEP — REVERIFY DURING R1/R8`.
8. **R0.5B.8 — Full regression + architecture guardrails.** Per §16 (Rev 1, expanded per §18 of the user's
   latest instructions — see the companion final report for actual results).

Each phase is checked (targeted tests, at minimum) before the next begins, per the user's explicit
sequencing requirement. Commits are made only if/when the user explicitly asks — no phase in this list
implies an autonomous commit.

---

## 10. Risks (revised)

Same 6 risks from Revision 1's §17 apply, with one added and one resolved:

- **Resolved**: "no honest home for the god-object" is no longer a risk — §1/§3 gives it one.
- **Added**: **`admin_console_controller.py`'s body edit (§3.3) is now the single highest-risk step in the
  whole plan**, higher than the QML import-prefix edits Rev 1 flagged, because it is the one place where
  ~30 delegated methods' import statements all change in the same file, and a mistake here (wrong function
  imported, wrong capability package) would silently misroute a mutation to the wrong entity rather than
  raising an obvious import error. Mitigated by: reading the real current file before editing (not
  reconstructing from memory), editing one delegated group at a time (all organization methods, then all
  calendar methods, etc.), and running `test_qml_platform_presenters_catalog_actions.py` /
  `test_qml_platform_presenters_catalog_admin.py` (which exercise exactly these delegated mutation paths)
  immediately after this file is edited, before moving on to any QML phase.

---

## 11. Final Recommendation (revised)

Proceed with capability-owned implementation now, per this revision, with the temporary
`controllers/admin_console/` (Python) / `qml/workspaces/admin_console/` (QML) facade retained only for the
5 files/packages that exist purely because `AdminConsolePage.qml` is still one page bound to one controller.
Every other Admin Console responsibility — all 9 entity controllers, all their actions, all their
capability-specific refresh cascades, calendar internals, document internals — is fully decomposed into its
owning capability package during this same phase, not deferred to R1/R2. This satisfies the user's stated
goal (codebase easier to navigate, R1-R8 work easier to follow) while keeping the QML-facing contract of
`AdminConsolePage.qml`/`PlatformAdminWorkspaceController` byte-for-byte unchanged.

---

## 12. Decisions Reaffirmed (no longer pending — user has ruled on each)

1. ~~`identity_access/roles_access/` vs. `access`~~ → **Decided: `access`.**
2. ~~`legacy_admin_console/` holding package~~ → **Decided: rejected. Replaced by minimal
   `admin_console/`/`admin_console` facade, documented per §1.2.**
3. ~~`workspaces/platform/` redundant segment~~ → **Decided (already, in Rev 1): dropped.**
4. ~~Split `admin_entity_actions.py`/`admin_refresh_service.py` now vs. defer~~ → **Decided: split now,
   per §3.2/§3.4.**
5. ~~`SettingsDefaultsSection.qml`/`SettingsSecuritySection.qml` fate~~ → **Decided (already, in Rev 1):
   kept during R0.5, deletion is R5/R8's job per D4.**
6. ~~`OverviewSectionCard.qml`/`RecordListCard.qml` fate~~ → **Decided: neither deleted in R0.5B regardless
   of re-check outcome; both `KEEP — REVERIFY DURING R1/R8`.**

No decisions remain pending before R0.5B execution proceeds.

---

## 13. Revision 3 — `workspaces/` wrapper dropped for consistency (post-execution finding)

During execution, review surfaced a real inconsistency Revision 2 left in place: `admin_console/`,
`control/`, `settings/`, `tenants/` stayed nested under `qml/workspaces/` while `organization/`,
`calendars/`, `identity_access/`, `documents/`, `support/` sat directly under `qml/` — an arbitrary split
with no principled reason (Revision 2 kept the four "as-is" purely to minimize churn on directories that
didn't need to move for the capability-split goal, which was the wrong tradeoff once the resulting tree was
actually compared side by side). Fixed by dropping `workspaces/` entirely: all four now sit directly under
`qml/`, as siblings of the other five capability groups. `Platform/` is unaffected and unchanged — it is not
a workspace, it is the shared-component library scoped to Platform (parallel to `shared/qml/App/` for the
whole app), holding only genuinely cross-capability primitives (`Controllers/`, `Components/`, the 1
remaining cross-cutting dialog in `Dialogs/`, and `Widgets/`).

**Final QML top level under `src/ui_qml/platform/qml/`:**
```
Platform/            (shared component library — Controllers, Components, Dialogs, Widgets)
admin_console/       (temporary facade — see §1.3)
organization/{organizations,sites,departments,employees,parties}/
calendars/
identity_access/{users,access}/
documents/
control/
settings/
support/sections/
tenants/
```

Mechanically this required: renaming `qmldir` module declarations that used a `workspaces.*` prefix
(`workspaces.admin_console.components/sections/dialogs/panels`, `workspaces.control.dialogs`,
`workspaces.settings.dialogs`) to drop the prefix; updating `routes.py`'s 4 path tuples to drop the
`"workspaces"` path segment; and updating every test file that hardcoded the old
`platform/qml/workspaces/...` paths (`test_qml_architecture_guardrails_runtime.py`,
`test_qml_platform_dialogs.py`). Re-verified with the full platform-scoped test suite: identical result to
the pre-normalization run (16 failed/843 passed/12 errors, same exact set, all matching the pre-existing
baseline) — zero new regressions from this change.

**Correction to §3-§9's module-naming scheme (a second, more fundamental fix also found during
execution):** every new qmldir's `module` declaration must exactly match its physical directory path
relative to the single registered import root (`platform/qml`) — Qt's QML engine resolves `import A.B.C`
by looking for `<import-root>/A/B/C/qmldir`, it does not do a free-text lookup of qmldir-declared module
name strings. The "logical" capability-oriented dotted names originally specified in §3/§5 (e.g.
`Platform.Organization.Sites`, `Platform.Calendars`, `Platform.ControlDialogs`) do not match their actual
directories and do not resolve. All qmldir files were corrected to plain path-matching names instead
(`organization.sites`, `calendars`, `control.dialogs`, etc.) — confirmed by offscreen-loading all 4 Platform
routes with zero QML warnings, and by the full platform-scoped regression suite passing clean against
baseline. (The original, pre-restructure codebase never surfaced this because every old mismatched-name
qmldir declaration — e.g. `Platform.AdminDetail` at `workspaces/admin/detail/` — was never actually
consumed via its dotted name; every consumer used relative folder imports like `import "detail" as Detail`
instead, so the mismatch was latent and harmless until this restructure required genuine cross-directory
dotted imports for the first time.)

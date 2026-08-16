# Platform QML — Target UX/UI Design Specification (R0)

**Status: DESIGN SPECIFICATION — not implemented. No QML changed. No backend changed. No commit made.**

**Input:** `docs/ui_audit/platform_qml_existing_state_ui_ux_audit.md` (the existing-state audit, cross-checked
directly against source for this document — see "Cross-check corrections" below for the one factual
correction that resulted).

**Purpose:** Turn the audit's "what exists today" into one coherent, approved "what we build next" target.
Per explicit instruction, this document answers the audit's 20+ open redesign questions **as one design
system**, not as 20 independent local decisions. R1 (design-system implementation) does not start until
this document is reviewed and approved.

**Scope discipline, repeated from the audit and carried forward as a hard constraint on this document
itself:** this is a specification, not an implementation. Every section below describes a *target*; it
does not modify `src/ui_qml/platform/`, `src/ui_qml/shared/`, or any Python controller/presenter. Where a
target requires new backend capability that does not exist today, that is called out explicitly and
scoped as a *dependency*, not silently assumed.

---

## 0. Cross-check corrections made to the existing-state audit

Before drafting a target design on top of the audit, its most load-bearing numeric/structural claims were
independently re-verified against source (not just re-read from the audit's own prose), since a redesign
built on a wrong number is worse than no redesign. One real inconsistency was found and fixed in the audit
document itself:

- **Workspace-width figure corrected: 468px → 469px.** The audit's executive summary and ASCII shell
  reconstruction said the global drawer (248px) + Admin local nav (220px) consume "468px" before content
  renders. Tracing the actual layout (`AppTheme.qml:108` `sidebarWidth: 248`; `MainWindow.qml:47`, a 1px
  divider `Rectangle` between `ShellDrawer` and the workspace `Loader`; `AdminNavSidebar.qml:19`,
  `implicitWidth: collapsed ? 48 : 220`) gives 248 + 1 + 220 = **469px**, which is what the audit's own
  §19 workspace-width-budget table already computed correctly — the executive summary simply omitted the
  1px divider. Fixed in place in the audit document. This specification uses **469px** throughout.
- **New finding surfaced by the cross-check, not previously called out as sharply in the audit:** the
  Admin (`AdminNavSidebar.qml:19`) and Settings (`SettingsSidebarNav.qml:17`) local-nav components both
  hardcode the identical literal `collapsed ? 48 : 220` — not just "two different collapsed widths" (52
  vs. 48, as the audit's §16/§23.11 already noted for the *global* drawer vs. *local* nav), but the *same*
  magic-number pair duplicated verbatim in two separate files, neither sourced from `AppTheme`. This
  sharpens (does not contradict) the audit's own "four separate implementations, no shared base component"
  finding (§23.11, §25) and is treated as confirmed, in-scope R1 work below.
- Every other specific claim referenced from the audit in this document (the disabled 288px inspector,
  the default landing on Organizations, the three-mechanism Roles & Access surface, the fully-duplicated
  tenant-switch UI, the lack of a visible active-organization indicator, the "four collapsible-nav
  implementations" finding, the Settings/Control fake sections) was independently re-confirmed against the
  cited source file during this cross-check and found accurate as written. No other correction was needed.

---

## 1. Executive Summary of Target Design

Platform becomes **one workspace**, not four sibling routes. Its internal navigation is reorganized around
what a user is trying to do (see the "Users vs. Employees" and "why is this split into 4" ambiguities the
audit's terminology/navigation-depth audits flagged), a persistent **Tenant/Organization context bar** makes
the two most important — and today completely unsurfaced — scopes visible everywhere, and a new **Overview**
landing page replaces "opens directly into Organizations" as Platform's entry point. The existing
list→detail and dialog patterns are *kept*, not replaced, because the audit's own "Current UX Strengths"
(§22) already identified them as the strongest thing about the current implementation; what changes is
*how you get from list to detail* (a working inline inspector between the two, using the panel that already
exists and is already fully wired, just switched on) and *what happens to functionality that only looks
real today* (§23 of the audit): implemented capability stays and gets consistent chrome; not-yet-built
capability is either genuinely deferred and removed from the UI, or clearly labeled as not-yet-available —
never left looking operational while doing nothing.

**This is explicitly a QML/UX redesign, not a backend redesign.** Every target below either (a) uses
backend capability that already exists today (confirmed by tracing the actual controller/presenter/desktop-
API layer, the same way the audit did), or (b) is called out as *blocked on new backend work* and scoped
out of the guaranteed R1–R8 implementation, to be picked up only by a separate, deliberate decision — the
same governing discipline the CQRS modernization effort used for its own P6.0 backlog.

---

## 2. Design Principles

These four rules resolve the audit's 20+ open questions as one system rather than piecemeal:

1. **Implemented capability → visible and functional.** If a controller/presenter/desktop-API call exists
   and does something real, its UI is fully interactive, with no fake disabled affordances left beside it.
2. **Backend planned but not implemented → do not expose operational-looking UI for it.** No empty tables
   with hardcoded `rows: []`, no static "Filter" popup that says filtering "will appear here." Either the
   control doesn't render at all yet, or it renders in a clearly-labeled "not yet available" state (§6 of
   this document specifies exactly which).
3. **Informational content → explicitly labeled informational/read-only.** The audit's
   `AdminInformationalDetailSection` ("governed elsewhere" boundary card, reused across 6+ detail pages) is
   a genuinely good existing pattern for this and is **kept as the target pattern**, not replaced.
4. **Placeholder/dead code → removed, not redesigned.** `AdminCatalogPanel.qml`, `SettingsOverviewSections.qml`,
   `MasterDetailLayout.qml` (superseded by the target inspector pattern below, which reuses
   `AdminEntityDetailPanel`'s already-built shape rather than adopting the unused `SplitView`),
   `WorkspaceStateBanner.qml` (Platform's own dead copy — the *other* modules' copies are out of this
   document's scope), and `ControlMetricsSection.qml` (superseded by inline `KpiStrip` usage) are deleted
   in R8, not carried forward. See §23 for the complete file-level list.

A fifth rule, specific to this redesign's governance (not a UX rule, an engineering-process rule):

5. **QML redesign ≠ backend architecture redesign.** The chain `QML → Controller → Presenter/Application
   API → Desktop API` (audit §20) is kept exactly as-is. `@QmlUncreatable` controllers, the
   `run_mutation`/`serialize_operation_result` contract, `DynamicTableModel` binding, and the `qmldir`
   module-registration model are all **preserved constraints**, not redesign targets. Where a target UX
   requires a backend contract that doesn't exist (real server-side pagination, a permission-denied result
   category, department/site headcount breakdowns), that requirement is stated as a dependency and left for
   a separate backend decision — this document does not silently expand into a second CQRS/backend effort.

---

## 3. Target Information Architecture

```
Platform (ONE workspace — one drawer entry, one internal shell)
│
├── Overview                         [NEW — see §6]
│
├── Organization                     [renamed/regrouped from Admin's ORGANIZATION + part of WORKFORCE]
│   ├── Organizations
│   ├── Sites
│   ├── Departments
│   ├── Employees
│   └── Parties
│
├── Calendars                        [promoted to its own top-level group — richest single entity today,
│                                      audit §11.2, deserves peer status with Organization, not a child of it]
│
├── Identity & Access                [NEW grouping — separates "who can log in" from "who works here"]
│   ├── Users
│   └── Roles & Access               [normalized — see §9]
│
├── Documents                        [renamed from Admin's CONTENT group]
│   ├── Documents
│   └── Structures
│
├── Control (Governance)              [absorbs today's separate "Control Center" top-level route — "Control
│   │                                  (Governance)" reflects the user's own D3 framing; the literal QML/
│   │                                  route label is still "Control", this is a descriptive subtitle, not
│   │                                  a second name — confirm exact chrome wording during R2]
│   ├── Approvals
│   └── Audit                        [DECIDED, D3: canonical, single Audit destination. Confirmed —
│                                      not just flagged — that Admin's separate "Audit" leaf and this
│                                      destination read the identical `EnterpriseAuditService.list_recent()`
│                                      data (only limit/DTO shape differed). Admin's own "Audit" leaf is
│                                      REMOVED, not duplicated — see §10.]
│
├── Settings                         [absorbs today's separate "Settings" top-level route. DECIDED, D4:
│   │                                  smaller IA than originally sketched — Platform Defaults and Security
│   │                                  are REMOVED, not relabeled-and-kept, since no card in either section
│   │                                  is backed by a real global-default value — see §11.]
│   ├── Modules                      [= today's "Module Entitlements"]
│   ├── Integrations                 [= today's "Integration Capabilities"]
│   ├── Runtime
│   └── Diagnostics                  [= today's "Support & Diagnostics"; Admin's separate "Support" leaf
│                                      (Release Mgmt/Runtime Status/Incident Diagnostics/Runtime Paths/
│                                      Support Activity) merges here too — see §11]
│
└── Tenant Administration             [absorbs today's separate "Tenant Management" top-level route;
                                       the header's TenantSwitcher pill becomes a quick-switch dropdown
                                       reading the SAME controller, not a duplicate surface — see §5, §12]
```

**Why this regrouping, specifically (not just "it looks cleaner"):**

- The audit's own terminology audit (§8 of the required outline, folded into the audit's executive summary
  and §24) flagged **"what is the difference between User and Employee"** as unclear from the current UI.
  Today, `Users` sits in Admin's `WORKFORCE` group next to `Employees`, `Parties` — implying they're the
  same *kind* of thing. They are not: `Employee` is HR/master-data (`EmployeeService`,
  `employee_controller.py`), `User` is an identity/login concept tied to `RoleGovernanceService`/RBAC
  (`user_controller.py`, `access_workspace_controller.py`). Moving `Users` next to `Roles & Access` under a
  new **Identity & Access** group and leaving `Employees` under **Organization** is a direct, structural
  answer to that exact ambiguity — not cosmetic regrouping.
- **Calendars** promoted out of the `ORGANIZATION` bucket to its own top-level group: it already has the
  richest, most self-contained detail page in all of Platform (audit §11.2 — 4–7 dynamic sections,
  including a live working-days calculator), is referenced from Site/Department/Employee detail pages via
  the shared `AdminCalendarAssignmentSection`, and conceptually spans *all* of Organization, not one part
  of it — flattening it out of a sub-list gives it appropriate visual weight and shortens its navigation
  depth by one level.
- **Control** and **Settings** stop being separate top-level *routes* and become sections *within*
  Platform — directly resolving the audit's own §24 finding that "the rationale for splitting Admin
  Console vs. Control Center vs. Settings vs. Tenant Management is not self-evident from the UI" and "there
  is no Platform home screen." They remain distinct *sections* (their content is genuinely different —
  approval/audit queue vs. module/runtime configuration) but no longer masquerade as four unrelated
  top-level modules sitting beside Project Management/Maintenance/Inventory in the *global* drawer.
- **Tenant Administration** stays as a distinct section (not folded entirely into the context bar) because
  a full tenant list with status badges is a genuinely different task from "quickly switch which tenant
  I'm in" — but the *duplication* the audit found (§14, §23.10 — the header pill and the whole workspace
  bound to the literal same controller instance, rendering the same list twice) is resolved by making the
  header/context-bar control a **quick-switch summary** that links out to this section for anything beyond
  picking from a short list, rather than being a second, independent full implementation.

---

## 4. Target Shell & Global Navigation

**Global drawer** (`ShellDrawer.qml`'s role is otherwise unchanged — still collapsible 248/52px, still
groups Project Management/Maintenance/Inventory & Procurement as separate module entries): Platform becomes
**one row**, not four. Clicking it enters the Platform workspace shell (below), which owns its own internal
navigation from that point on — exactly the same "global nav hands off to a local nav" mechanism that
already exists (`MainWindow`'s `workspaceLoader` swapping `source`), just pointed at one Platform route
instead of four.

```
Global Drawer (248/52px, unchanged)
├── ▸ Shell
│    • QML Home
├── ▸ Platform                    ← ONE entry now, not four
├── ▸ Project Management
├── ▸ Maintenance
└── ▸ Inventory & Procurement
```

**Missing-icon fix (carried over, small, in scope for R2):** the audit found `platform.tenants` has no
entry in `ShellDrawer.iconForRoute()`'s map and silently falls back to the generic "apps" glyph
(`ShellDrawer.qml:26-57`). Since Tenant Administration becomes an internal Platform section rather than a
top-level route, this specific gap is resolved structurally (there is no longer a `platform.tenants` route
needing its own global-nav icon) — but the *lesson* (icon maps must be reviewed whenever routes change)
carries into R2's implementation checklist.

**Inside Platform**, the new persistent internal shell:

```
┌────────────────────────────────────────────────────────────────────────────────────┐
│ Global Header (unchanged chrome, ShellHeader.qml)                                  │
├───────────────┬──────────────────────────────────────────────────────────────────┤
│ Global Drawer │ PLATFORM CONTEXT BAR  (NEW — see §5)                              │
│ (248/52px)    ├──────────────────────────────────────────────────────────────────┤
│               │ Platform Nav (220/48px) │ Platform Workspace (content area)      │
│ ▸ Shell       │  ▸ Overview             │                                        │
│ ▾ Platform ◀  │  ▾ Organization         │                                        │
│  (highlighted)│     Organizations       │  (varies per section — see §6-§12)    │
│ ▸ Project Mgt │     Sites               │                                        │
│ ▸ Maintenance │     Departments         │                                        │
│ ▸ Inventory & │     Employees           │                                        │
│   Procurement │     Parties             │                                        │
│               │  ▸ Calendars            │                                        │
│               │  ▾ Identity & Access    │                                        │
│               │     Users               │                                        │
│               │     Roles & Access      │                                        │
│               │  ▸ Documents            │                                        │
│               │  ▸ Control              │                                        │
│               │  ▸ Settings             │                                        │
│               │  ▸ Tenant Administration│                                        │
└───────────────┴──────────────────────────┴────────────────────────────────────────┘
```

**Width budget, target vs. current** (the audit's §19 table, extended):

| Element | Current (Admin Console) | Target |
|---|---:|---:|
| Global drawer | 248px | 248px (unchanged) |
| Divider | 1px | 1px (unchanged) |
| Local nav | 220px | 220px (unchanged — same footprint, now one nav instead of four separately-coded ones) |
| **Context bar** | *(doesn't exist)* | full-width, ~40-48px tall, not a width cost — a height cost, paid once, shared by every Platform section instead of the "no visible active-org indicator anywhere" gap the audit found |
| **Total nav chrome** | 469px (36.6% of 1280px) | **469px (36.6%, unchanged)** — this redesign does not claim to reduce the *width* cost of navigation, because the local-nav footprint is preserved (it still needs to represent ~15 destinations); what it removes is the **duplication** (four re-implementations of the same 220/48 idiom collapse into one shared `GroupedNavigationRail` primitive, composed by `PlatformNavigation` and `SectionNavigationRail`, §16 — DECIDED, D7) and the **fragmentation** (four separate top-level routes collapse into one workspace's internal nav) |

This is a deliberate, evidence-based scoping decision: the audit measured a real 469px/36.6% chrome cost,
but the fix for that is a **collapse-by-default** or **narrower-rail** visual decision (§7's density work),
not something this section can respons­ibly reduce by removing a destination — Platform genuinely has this
many things to navigate to. What *is* fixed is that today's cost is paid by four independently-coded,
inconsistent sidebars; the target pays a very similar cost through **one** shared, consistent component.

---

## 5. Tenant / Organization Context Bar

**The gap this closes, precisely (audit §21):** "The UI provides no visible indicator anywhere (header,
breadcrumb, or otherwise) of which organization is currently active outside of visiting Admin Console →
Organizations and reading the 'Active' status chip on a row." Tenant scope already has *some* visibility
(the header's `TenantSwitcher` pill, gated by `TenantSwitcherController.isMultiTenant` — invisible in
single-tenant deployments, audit §21) but Organization scope has **none**.

**Backend dependency check (done, not assumed):** both halves of this bar are backed by data that already
exists and is already wired into QML today, just not surfaced together:
- Tenant: `TenantSwitcherController`/`tenant_switcher_presenter.py`, already bound to
  `platformCatalog.tenantSwitcher` from both `TenantSwitcher.qml` (header) and
  `TenantManagementWorkspacePage.qml` today.
- Organization: `OrganizationService`/`organization_catalog_presenter.py`'s active-organization concept —
  today only *read* via the Organizations list's "Active" status chip and *changed* via "Set Active" on an
  Organization's detail page (audit §11.1). No new desktop-API call is required for a context bar to
  **display** the active organization's name; it is a UI-surfacing task, not a backend task.

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│ Platform          Tenant: TECHASH ▾          Organization: Hamburg GmbH ▾         │
└──────────────────────────────────────────────────────────────────────────────────┘
```

- **Tenant ▾** opens the same quick-switch list `TenantSwitcher.qml` renders today (bound to the identical
  controller) — hidden entirely when `isMultiTenant` is false, exactly as today.
- **Organization ▾** is **new**: a lightweight dropdown reading the same organization list
  `AdminOrganizationDetailPage`'s "Set Active" already knows how to call, letting a user switch active
  organization from *anywhere* in Platform, not only from the Organizations list. This is the single
  highest-value, lowest-backend-risk item in this whole specification: it uses an existing mutation
  (`set_active_organization` — already called by "Set Active" today) from a new, more visible location.
- Both dropdowns end with a "Manage tenants…" / "Manage organizations…" link into the respective full
  section (Tenant Administration / Organization → Organizations), so the context bar **replaces** none of
  the existing full-management UI — it only adds a fast, always-visible read+switch affordance, resolving
  the duplication finding (§14) by making the header/context version the *canonical* quick-switch surface
  and the full workspace the canonical *management* surface, rather than two independent full
  implementations of the same list.

---

## 6. Platform Overview

**What this replaces:** "opens directly into Organizations" (`AdminWorkspaceState.qml:12`,
`activeSection: "organizations"`, confirmed by direct source read). There is no neutral landing page in
Platform today — you land in a specific entity's list immediately. Overview becomes the new default route.

**Backend reality check, tile by tile — this is the most important part of this section, since the user's
own sketch intentionally included items that are not backed today and said so ("Not everything shown above
needs to ship immediately"). Here is exactly which is which, traced against real code:**

| Tile / section | Backed today? | Source |
|---|---|---|
| Employees (total), Active, Sites, Departments counts | **Yes — already computed** | `PlatformAdminWorkspacePresenter.build_overview()` (`admin_presenter.py`) — this is the exact method the CQRS modernization's **P6 pilot** (`EmployeeHeadcountReader`) optimized; it already powers Admin Console's existing overview metrics and the Admin **Audit** leaf's stat sections today (audit §11.12). Moving/duplicating this data onto a dedicated Overview page is a UI relocation, not new backend work. |
| Users count, locked-session count | **Yes** | same `build_overview()` — already computes `active_user_count`/`locked_user_count` (audit §11.12's citation of `admin_presenter.py`). |
| Documents (current-version count) | **Yes** | same `build_overview()`. |
| Pending Approvals count | **Yes** | `PlatformControlWorkspaceController`'s existing `queueCount` (already drives Control Center's tab badge today, audit §12). |
| Recent Activity feed | **Yes** | the same `ActivityFeed`-backed data already shown in Admin's **Audit** leaf and Control's **Audit** tab (audit §11.12, §12) — Overview would show a trimmed, most-recent slice of the same feed, not a new data source. |
| **Employees by Department** breakdown | **No — not backed today** | This is exactly **P6.0 discovery candidate #1** from the CQRS modernization audit ("Employees per department") — evaluated and **explicitly deferred**, not selected for CQRS remediation, precisely because no consumer needed it yet. It is backlog, tracked in `docs/platform_modernization/CQRS/platform_cqrs_existing_state_audit.md`'s "Deferred product capability backlog" section. |
| **Employees by Site** breakdown | **No — not backed today** | Same backlog list, candidate related to "Employees per site" / "People/resources by organizational unit." |

**Target layout — backed tiles ship in R3; the two breakdown tables are explicitly out of R0–R8's
guaranteed scope** (see §25):

```
┌ Platform Overview ──────────────────────────────────────────────────────────────┐
│                                                                                  │
│ Workforce                                                                       │
│ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────┐ │
│ │Employees │ │ Active   │ │ Sites    │ │Departments│ │ Users    │ │ Documents │ │
│ │   148    │ │   143    │ │    6     │ │    12     │ │   34     │ │    210    │ │
│ └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘ └───────────┘ │
│                                                                                  │
│ Access & Governance                                                             │
│ ┌ Pending Approvals ────────┐   ┌ Recent Activity ──────────────────────────┐  │
│ │ 7                — Open  │   │ User role changed for Alice Newman         │  │
│ └────────────────────────────┘   │ Organization "Hamburg GmbH" updated       │  │
│                                  │ Employee "Bob Smith" created              │  │
│                                  └─────────────────────────────────────────────┘│
│                                                                                  │
│ ┌──────────────────────────────────────────────────────────────────────────┐  │
│ │ ⚠ Organization/site breakdowns (Employees by Department, Employees by     │  │
│ │   Site) are not yet available — this requires new backend rollup work,   │  │
│ │   tracked as backlog, not part of this UI redesign. [Learn more]         │  │
│ └──────────────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────────────┘
```

Every KPI tile is clickable and navigates to its owning section (Employees tile → Organization → Employees,
etc.) — a direct, low-cost fix for the audit's finding that "no global 'recently viewed' or cross-workspace
search exists to jump directly to, say, a specific Employee" (§24); Overview's tiles are not that search,
but they at least make the *highest-traffic* destinations one click away from the landing page instead of
requiring the current minimum 3-decision path (audit's navigation-depth table).

---

## 7. List → Inspector → Detail Pattern (the master-data experience)

**Why this is cheap, not speculative — cross-checked directly:** `AdminEntityDetailPanel.qml` is, per the
audit's own §11.0 finding (independently re-confirmed above), *"fully built, fully wired"* — bound to
`detailItem`, `selectedDocument`, `documentPreviewState`, and edit/toggle/set-active handlers already. The
only thing stopping it from working today is one hardcoded line: `visible: false`
(`AdminConsolePage.qml:902`). The target pattern is therefore **switch it on and wire row selection to it
properly** — not build a new inspector panel from scratch.

```
single click  → row selection + inspector panel opens (reusing AdminEntityDetailPanel, 288px)
double click  → full detail page (reusing SectionDetailPage — unchanged from today)
"Open" button in inspector → same full detail page, explicit affordance for keyboard/no-double-click users
```

```
┌ Employees ────────────────────────────────────────────────────────────────────────┐
│ [🔍 Search employees...]  Department ▾  Site ▾  Status ▾           [+ Employee]   │
├─────────────────────────────────────────────┬───────────────────────────────────────┤
│ Name           Department      Status       │ Alice Newman                          │
│─────────────────────────────────────────────│ Product Engineer                      │
│ Alice Newman ◀ Engineering     Active        │                                       │
│ Bob Smith      Operations      Active        │ Department: Engineering               │
│ ...                                          │ Site: Hamburg                         │
│                                               │ Status: Active                        │
│                                               │                                       │
│                                               │ [Open]   [Edit]                       │
├───────────────────────────────────────────────┴───────────────────────────────────────┤
│ 1–25 of 148                                            ‹ 1 2 3 4 5 6 ›  [dependency,  │
│                                                                          see §14]     │
└─────────────────────────────────────────────────────────────────────────────────────┘
```
No Delete/overflow-menu action in the inspector (D1, DECIDED) — only `Open`/`Edit`. The
`Department ▾ Site ▾ Status ▾` filter row is an **illustrative future-state example only**
(D6, DECIDED) — master-data lists ship search-only in the first redesign release; see §14.
At the D8-decided 1024px minimum width, this inspector is the panel most likely to collapse/
close first under the graceful-degradation policy in §19 — the list and (once opened) full
detail page take priority over the inspector at reduced widths.

**What stays exactly as today (deliberately not touched):**
- `DataTable`, `TableToolbar`, `EntityDialog` (create/edit), `SectionDetailPage`/`ContextualActionToolbar`/
  `SectionNavigationRail` for full detail — all named in the audit's "Current UX Strengths" (§22) and kept
  verbatim as the target.
- The module-gated section visibility pattern in detail pages (`isModuleEnabled(...)` hiding
  `SectionNavigationRail` entries) — audit's own "genuinely useful, consistently-implemented" verdict,
  unchanged.

**What changes:**
- `visible: false` → conditional on selection (`AdminConsolePage.qml:902` and its 8 sibling instances for
  the other entity types — this is a single, mechanical property change per entity, once the inspector's
  content-binding is confirmed correct for all 9 entities, not 9 separate redesigns).
- **DECIDED, D1:** the inspector's **Delete** button, which the audit found has an *empty click handler*
  (`AdminEntityDetailPanel.qml:374-382`, `onClicked: {}`), is **removed entirely** from the panel, per
  Design Principle 4 (placeholder → removed). No delete backend capability is added as part of this
  redesign — currently **no** Admin master-data entity has a delete capability at all (audit §17), and
  none is introduced here. If delete/archive semantics are wanted later, that is a separate product/domain
  decision (cascade rules, soft-delete vs. hard-delete, tenant-admin scoping, audit-retention
  implications) made on its own merits, not implied by this UI redesign.

---

## 8. Detail Page Pattern

Unchanged from today, by deliberate choice: `SectionDetailPage` (Back + title + `SectionNavigationRail` +
scrollable content + pinned `ContextualActionToolbar`) is reused verbatim for every entity's full detail
view. The only two systemic changes:

1. **Asymmetric confirmation on state-changing and destructive actions** (D5/D14, DECIDED — replaces this
   document's earlier "uniform confirmation" framing): **activating** a record (Organization/Site/
   Department/Employee/User/Party/Document/Document-Structure "Set Active") executes directly with success
   feedback, since it is low-risk; **deactivating** the same record requires a confirmation naming the
   entity and, where known, the consequence (e.g., "Deactivate Bob Smith? He will lose access to assigned
   projects."), since deactivation can have real downstream effects (session/scope/validation consequences)
   that reactivating does not symmetrically undo. Calendar Exception/Recurring Event delete (currently
   no-confirm, audit §17) and Module Entitlement Lifecycle/Licensed/Enabled toggles (currently no-confirm,
   audit §13.2) are genuinely destructive/impactful and keep a blocking confirmation regardless of
   direction — they are not toggle-active and are not subject to the activate/deactivate asymmetry.
2. **A visible "informational, not yet available" treatment** distinct from the existing
   `AdminInformationalDetailSection` "governed elsewhere" card — used specifically for module-gated
   sections that are hidden today with no explanation (audit's navigation-depth table example: "View why a
   Party can't see 'Linked Procurement' … the tab silently doesn't exist, no explanation surfaced"). Target:
   when a module-gated section would exist but the module isn't enabled for this tenant/org, show a
   disabled (not hidden) rail entry with a tooltip/inline note ("Available when Inventory & Procurement is
   enabled") rather than omitting it — this directly answers the audit's open question about
   "Disabled/module not licensed" states (§18) needing a *visible-but-disabled* treatment instead of
   invisible-by-omission.

---

## 9. Identity & Access — Roles & Access, normalized

**The problem, exactly as the audit found it (§11.10, §23.8):** three simultaneous interaction mechanisms —
(1) an inline assignment form, (2) an inline 272px grant inspector that appears on single-click, (3) an
additive full-page `AdminAccessDetailPage` opened on double-click — for what is conceptually one task
("manage a grant"). No other entity in Platform uses more than one of these at once.

**Target: bring it into the same list → inspector → detail model as every other entity (§7), nothing
special-cased:**

```
┌ Roles & Access ─────────────────────────────────────────────────────────────────┐
│ [🔍 Search grants...]  Scope ▾  Role ▾                    [+ Assign Access]     │
├─────────────────────────────────────────────┬─────────────────────────────────────┤
│ Principal      Role         Scope           │ Alice Newman                        │
│───────────────────────────────────────────── │ Role: Project Manager               │
│ Alice Newman ◀ Project Mgr  Project X        │ Scope: Project X                    │
│ Bob Smith      Viewer       Organization     │ Assigned: 2026-06-01                │
│ ...                                          │                                     │
│                                               │ [Open]  [Revoke Access]            │
├───────────────────────────────────────────────┴─────────────────────────────────────┤
│ 1–25 of 60                                                    ‹ 1 2 3 ›            │
└───────────────────────────────────────────────────────────────────────────────────┘
```

- **"Assign Access"** becomes a dialog (`EntityDialog`-based, matching every other "+ New X" affordance in
  Platform), not a permanently-visible inline form taking up vertical space above the table on every visit.
- **Single-click → inspector** (reusing the same `AdminEntityDetailPanel`-derived inspector pattern as
  every other entity, not a bespoke 272px `Rectangle`).
- **"Open" in the inspector, or double-click → full detail** (`AdminAccessDetailPage`, unchanged content:
  Overview / Permissions / Scope / Audit).
- **Account Security & Sessions** (Unlock/Revoke Sessions/Force Password Reset) stays as its own distinct
  table below — it is a genuinely different entity (sessions, not grants) and the audit did not find this
  part of the surface problematic; only the grants-management triplication is in scope here.
- **"Revoke Access" and "Revoke Sessions"/"Force Password Reset" follow D5's deactivate-style confirmation
  policy, not the plain toggle-active path** — revoking access/sessions has direct, material security
  consequences (exactly the case D5 carves out for a blocking, entity-naming confirmation), so these are
  treated the same as Module Entitlement Lifecycle changes (§8), not as a simple activate/deactivate toggle.

This eliminates one instance of the audit's "duplicated interaction model" finding (§23.8) without touching
the underlying `access_workspace_controller.py`/`access_workspace_presenter.py` contract at all — purely a
QML-layer normalization.

---

## 10. Control (Approvals / Audit)

**Kept:** Approvals queue (`DataTable` + row activation → `ControlApprovalDetailPage` + Approve/Reject
dialog) — the audit found this fully functional and it needs no redesign beyond adopting the shared
component library (§20) and confirmation on Approve/Reject if not already present (it currently is not,
per §26's open-decision list — actually the audit did not flag Approve/Reject specifically as
no-confirm; **this needs verification during R5 implementation**, flagged rather than asserted here).

**Removed, per Principle 2 (backend planned, not implemented → don't expose operational UI) — DECIDED, D2:**
- **Escalations** and **System Events** tabs are **removed entirely** from Control's tab bar. The audit
  confirmed these are hardcoded `rows: []` with no corresponding controller property at all
  (`control_workspace_controller.py`, confirmed absent) — they are placeholder tabs with no backend
  capability and must not appear as operational product surfaces. Control's tab-bar architecture (a plain
  horizontal list of `{id, label, count}` entries, §3 of the audit) does not structurally foreclose adding
  tabs back later — nothing about this removal prevents Escalations/System Events reappearing once real
  backend/product semantics exist for them; they simply do not ship as placeholders in this redesign.

**Merge DECIDED, D3:** Control's own "Audit" tab and Admin's separate "Audit" leaf (audit §11.12) are
**confirmed** (not just suspected) to read the identical `EnterpriseAuditService.list_recent()` data —
traced during the R0.1 closure pass to `control_queue_presenter.py:54-62`'s `build_audit_feed()` (calling
the desktop API's `list_recent(limit=25)`) and `admin_presenter.py:97`'s call to the desktop API's
`list_for_overview(limit=50)`, which itself does nothing but call the same
`EnterpriseAuditService.list_recent(limit=limit)` and reshape the result for `ActivityFeed`. Only `limit`
and DTO shape differ — not the data source. **Target: one canonical `Control (Governance) → Audit`
destination** (§3); **Admin's separate "Audit" leaf is removed**, not kept as a duplicate. Per the user's
explicit constraint alongside this decision: this is a **UI-layer read-contract normalization only** —
standardizing on one desktop-API method/limit for the merged destination — **not** a broader merge of
`control_queue_presenter.py` and `admin_presenter.py` themselves, which remain separate presenters serving
their own distinct sections (Control's queue metrics vs. Admin's workforce/master-data overview); only the
audit-feed read path is deduplicated, not the presenter layers wholesale.

---

## 11. Settings (Modules / Integrations / Runtime / Diagnostics)

**Kept as-is, functionally:** Module Entitlements (→ **Modules**) and Integration Capabilities
(→ **Integrations**) are real, backed, working today and need no functional change beyond the shared
component library.

**Runtime** stays as a read-only info panel (theme mode, API status, workspace summary) — but see §17/§18:
once density and dark-mode controls are real, this is also the natural home for their **user-facing
setting toggles** (today `themeMode`/`densityMode` are tracked but have no UI control anywhere, audit §16 —
Runtime is where a control belongs once one exists).

**Diagnostics** absorbs today's Admin **Support** leaf (Release Management, Runtime Status, Incident
Diagnostics, Runtime Paths, Support Activity) — these are all fixed dashboards, not entity lists, and
conceptually belong with Settings' other "how does this installation behave" content rather than sitting
inside the master-data-focused Organization/Identity area. **The Install-Update flow that quits the app**
(audit §11.11) is preserved verbatim — a genuinely working, if unusual, capability.

**Removed — DECIDED, D4:** **Platform Defaults** and **Security** sections are, per the audit, "100%
hardcoded static display data" with zero controller binding and zero edit affordance (§13.3, §13.5). D4's
decision rule is not a blanket "delete" or "keep" — it is per-value: **if a displayed value is available
from a real runtime/configuration/backend source, expose it as a clearly read-only value; if it is not
backed by authoritative application data, remove it.** No new settings backend is built merely to preserve
the old cards.

**Verification done during this update, per value, before applying the rule (not assumed):**
- *"Locale & Fiscal" card* (Default timezone, default currency): the closest real capability is
  `Organization.timezone_name`/`Organization.base_currency` (`organization.py:20-21`) — genuinely real,
  configurable fields — but they are **per-organization**, already visible and editable today on each
  Organization's own record (audit §11.1's Organization Editor Dialog), not a single platform-wide
  "default." Showing a fixed platform-level value here would misrepresent that model (organizations can
  and do have different timezones/currencies) rather than merely being stale. **Removed**, not relabeled —
  the real, authoritative version of this data already lives on each Organization record.
- *"Session Policy" card*: a real, per-user session-timeout override capability exists
  (`AuthService.set_user_session_policy`, `session_service.py:89-106`) — but it is per-user, set via
  `session_timeout_minutes_override`, not a single readable platform-wide default value. No global default
  is exposed anywhere to display. **Removed** — the real capability is a per-user feature outside this
  Settings screen's scope, not a platform default this card could truthfully show.
- *"Data Management", "Approval Workflow", "Notification Defaults", "Compliance & Governance" (remaining
  Platform Defaults cards), "Password Policy", "RBAC Defaults", "Approval Thresholds" (remaining Security
  cards)*: no corresponding backend value of any kind was found (confirmed absent, both in the original
  audit and re-checked here). **Removed.**

**Net effect: both sections are removed from Settings in the first redesign release**, giving Settings a
smaller, entirely-truthful IA:
```
Settings
├── Modules                (Module Entitlements)
├── Integrations           (Integration Capabilities)
├── Runtime
└── Diagnostics             (Support & Diagnostics)
```
Real, authoritative Platform Defaults and Security Policies can be **added later**, as genuinely new
Settings sections, once a real backend contract exists for them — not resurrected from today's hardcoded
cards. This is not a permanent ceiling on Settings' scope, only a statement that nothing is added without
a real contract behind it.

---

## 12. Tenant Administration

Single list, unchanged functionally (status badges, Switch action) — the redesign's only change is
*structural*: it moves from a standalone top-level route to a Platform-internal section, and its
relationship to the header/context-bar quick-switch is now explicit (§5: context bar = quick-switch,
canonical source of truth for "what's my active tenant"; Tenant Administration section = full list +
status, canonical source of truth for "manage/review all tenants"), resolving the audit's "fully duplicated
capability, two skins" finding (§14, §23.10) by giving each surface a distinct job instead of both doing
the same job twice.

**Not in scope for R0–R8** (no tenant create/edit/provision UI exists today, audit §14, and none is
proposed here) — tenant lifecycle management remains an explicit product decision, not assumed as part of
this UI redesign.

---

## 13. Forms & Dialogs

**Kept verbatim:** `EntityDialog`'s contract (subtitle + priority messages + scrollable form + footer
[destructive? / spacer / busy / Cancel / Primary]), the dual-mode `mode: "create"|"edit"` pattern, and the
`submitDialog()` stay-open-on-error / close-on-success behavior (audit's own "Current UX Strengths" #4).
This is good, working UX and is the target for every dialog, unchanged.

**Fixed:** dialog width standardization. The audit found 15 dialogs across 8 distinct literal pixel widths
(420–660px) with no shared token (§19, §26). Target: a small enum/token set —
`Theme.dialogWidth.compact` (~440px, e.g. `ApprovalDecisionDialog`, `ModuleLifecycleDialog`),
`Theme.dialogWidth.standard` (~560px, e.g. most entity editors), `Theme.dialogWidth.wide` (~660px, e.g.
`DocumentEditorDialog`, `PartyEditorDialog`'s 18-field form) — three sizes instead of eight literals, chosen
by content need rather than per-dialog guesswork. This is R1 (design-system) scope, not a per-dialog R6
change, since it's a token addition, applied to existing dialogs mechanically once it exists.

---

## 14. Filters, Search, Pagination, Actions

**Filters — DECIDED, D6:** Principle 2 applies directly. The audit found Filter/Views buttons across
Admin/Control/Settings universally open a static "will appear here" popup (§17, §23.4). Cross-check during
R0.1 found this precisely: `showFilter: true` is set today only on `AdminAuditSection.qml:67`,
`AdminSupportSection.qml:93`, and Control's Approvals/other tab (`ControlWorkspacePage.qml:170, 284`) — never
on any master-data entity list — and `EnterpriseAuditService.list_recent()` already accepts
`entity_type`/`operation`/`severity` filter parameters today, with no equivalent found on any master-data
list method. **Target, sequenced by what's actually backed:**
- **Audit / Control (Governance)**: real filter controls, wired to the existing `entity_type`/`operation`/
  `severity` parameters — in scope for **R6**, requires no new backend work.
- **Master-data lists** (Organizations/Sites/Departments/Employees/Users/Parties/Documents/Structures,
  Roles & Access grants): **no Filter button at all** in the first redesign release — search-only,
  matching what's genuinely backed today. The `Department ▾ Site ▾ Status ▾` filter row shown in this
  document's §7/§9 wireframes is illustrative of a *possible future* state, not part of R6's guaranteed
  delivery, and must not be read as already scoped. **Future master-data filtering, if pursued, is added
  deliberately through new desktop-API/query-contract parameters — never by client-side filtering of an
  already-fully-materialized collection**, which would silently reintroduce the same full-materialization
  cost the CQRS modernization's Reader work has been eliminating elsewhere.

**Pagination — explicit backend dependency, not assumed solvable in QML alone.** The audit found
`TablePaginationBar` is unconditionally hidden for every Admin entity list specifically *because* those
lists bind a Python `DynamicTableModel` with a code comment reading "server-side pagination pending"
(`AdminEntityWorkspace.qml:139`). This is not a QML bug — real pagination requires a paginated backend read
path, which is exactly the kind of aggregate/projection-shaped capability the CQRS modernization's Reader
pattern (P1 `ModuleEntitlementReader`, P6 `EmployeeHeadcountReader`) was built to establish precedent for.
**Recommendation:** any entity list expected to regularly exceed a page's worth of rows (Employees, Users,
Documents are the most likely candidates given typical org sizes) should get a dedicated paginated Reader
following that exact precedent, as a **separate backend-scoped follow-on**, not folded into this QML
redesign's guaranteed phases. Until then, the target UX for lists is: **either show the real full list with
no pagination affordance at all** (honest about current behavior) **or add pagination only once a real
Reader backs it** — never leave a pagination bar visible-but-inert as today.

**Destructive/impactful actions — DECIDED, D5 (asymmetric, not uniform):**
- **Genuinely destructive/impactful, blocking `ConfirmationDialog` regardless of direction:** Calendar
  Exception/Recurring Event delete (currently no-confirm), Module Entitlement Lifecycle/Licensed/Enabled
  changes (currently no-confirm), Roles & Access "Revoke Access"/session Unlock-Revoke-Force-Reset actions
  (§9). Delete itself has no shared `ConfirmationDialog` case yet since no delete capability exists (D1) —
  this list applies once/if one does.
- **Toggle-active on the 9 master-data entities (Organizations/Sites/Departments/Employees/Users/Parties/
  Documents/Document-Structures' "Set Active"): asymmetric, not a blanket confirmation.** **Activate**
  executes directly with success feedback (an `InlineMessage`-style toast) — low risk, since it only makes
  a record eligible for use again. **Deactivate** requires a `ConfirmationDialog` naming the entity and, where
  known, its consequence (e.g., "Deactivate Bob Smith? He will lose access to assigned projects.") — since
  deactivation can trigger validation/session/scope consequences that reactivating does not symmetrically
  reverse. **No generic Undo is introduced for either direction** — the backend does not guarantee the
  inverse mutation is safe, and toast-with-undo is reserved for genuinely reversible, presentation-only
  actions elsewhere (none identified in Admin Console's current action set; this is a pattern held in
  reserve for future use, not applied to toggle-active). A single shared `ConfirmationDialog` component
  (§16) backs the deactivate/destructive cases; the activate path uses the existing success-toast mechanism,
  not a new component.

---

## 15. Permission States

**Current state (audit §18, §21):** no "permission denied" UI state exists anywhere; RBAC enforcement is
presumed entirely server-side, surfacing through the same generic `errorMessage` channel as any other
failure; the `serialize_operation_result` contract carries only `category`/`code`/`message` strings, with
no QML file branching on a permission-specific category.

**Target — explicitly split into what QML can do alone vs. what needs a backend contract change:**
- **QML-only, in scope for R6:** a generic **"restricted" empty/disabled state** component (visually
  distinct from a normal `EmptyState` — a lock icon, "You don't have access to this section" messaging)
  that a section can render *if* its underlying data call fails with any error, as a friendlier fallback
  than the raw `errorMessage` banner for what's likely a permission issue. This does not require knowing
  *for certain* it was a permission failure — it's a UX improvement to the existing generic-error path.
- **Requires backend work, out of R0–R8's guaranteed scope:** true permission-aware UI (e.g., proactively
  disabling a button *before* the user clicks it, or genuinely distinguishing "permission denied" from
  "record locked" from "validation failed") requires `serialize_operation_result` to carry a real
  `category === "permission"` (or similar) value the backend actually populates — today it does not
  (confirmed absent, audit §18). This is a backend/desktop-API change, and this document does not propose
  making it as part of a QML redesign; it is listed here so the distinction between "we can improve this
  today" and "this needs a backend decision first" is explicit rather than glossed over.

---

## 16. Component-Reuse-First Redesign Order (R1 before pages)

Per the explicit instruction not to hand-beautify 69 files individually, R1 redesigns/consolidates the
shared layer **first**; every Platform page in R2–R6 then composes those components rather than each
inventing its own chrome. Target shared component set, with disposition:

| Component | Disposition |
|---|---|
| `AppTheme` | **Extended**, not replaced — add dark-mode branch (§17), density-control wiring (§18), dialog-width tokens (§13), and **canonical navigation-rail dimension tokens** (`Theme.nav.expandedWidth`/`collapsedWidth`, replacing the duplicated hardcoded `collapsed ? 48 : 220` literals in `AdminNavSidebar.qml:19`/`SettingsSidebarNav.qml:17`, plus reconciling the global drawer's separate 248/52 pair, §0) — **DECIDED, D7**. |
| `GroupedNavigationRail` (**new name, replaces the earlier "`NavigationRail`" placeholder — DECIDED, D7**) | **New, low-level primitive.** Owns: expanded/collapsed state, selected state, icon/label layout, grouped sections, badges/counts, keyboard/focus behavior, and the canonical expanded/collapsed dimensions sourced from `AppTheme` (not a fourth hardcoded literal pair). This is the shared engine `ShellDrawer`, `AdminNavSidebar`, and `SettingsSidebarNav` each hand-roll today — closing the audit's "four separate implementations" finding (§23.11, §25) at the root. **`SectionNavigationRail` is *not* replaced by this primitive — see the next row.** |
| `SectionNavigationRail` (detail-page-internal rail) | **Kept as a named, semantically-scoped specialization**, re-implemented on top of `GroupedNavigationRail` rather than either (a) becoming the universal base itself, which the user's D7 decision explicitly rejected — its responsibility is specifically "navigate sections inside a detail record," not general workspace navigation — or (b) staying a wholly separate, un-migrated component perpetuating the duplication. It already has its own grouping engine (`_groups`/`_groupLabel`/`groupsCollapsedByDefault`, confirmed during R0.1) that the new primitive should absorb, not discard; what it currently lacks (collapse-to-icon-rail) is added via the shared primitive, not hand-rolled a second time. |
| `PlatformNavigation` (**new**, the target IA's own top-level rail, §3/§4) | Composed from `GroupedNavigationRail`, replacing `AdminNavSidebar.qml` and `SettingsSidebarNav.qml` (both deleted, §22) — a sibling of `SectionNavigationRail` under the same primitive, not a rename of it. |
| `PageHeader` / `WorkspaceHeader` | **Kept** (`shared/qml/App/Widgets/PageHeader.qml`, already used via `WorkspaceFrame`) — extended to optionally host the new **ContextBar** (§5) as a slot beneath the title, rather than every workspace page reinventing header layout. |
| `ContextBar` | **New** — the Tenant/Organization bar (§5). |
| `DataTable` | **Kept, unchanged** — audit's own "Current UX Strengths" #6 (centralized column-type rendering). |
| `TableToolbar` | **Extended** — real filter-control slot (§14) replacing the static `AnchoredPopup` placeholder; `showFilter` becomes meaningful instead of dead. |
| `FilterBar` | **New** (or a `TableToolbar` extension, decided during R1 implementation) — the real Department/Site/Status-style filter row shown in this document's wireframes. |
| `TablePaginationBar` | **Kept**, but its "hide when `DynamicTableModel` bound" behavior becomes conditional on whether a *paginated* Reader actually backs the model (§14), not a blanket hide. |
| `MasterDetailLayout` (`SplitView`) | **Deleted** (§0's Principle 4) — the target inspector pattern (§7) reuses `AdminEntityDetailPanel`'s already-built fixed-width shape, not this unused resizable scaffold. If resizable panes are wanted later, that is new work building on the deleted file's *concept*, not a resurrection of the file itself. |
| `InspectorPanel` | **New name for, effectively, `AdminEntityDetailPanel.qml`'s pattern** — generalized so every entity (not just Admin's 9) can bind to it, and actually turned `visible: true` (§7). |
| `SectionDetailPage` / `ContextualActionToolbar` | **Kept, unchanged** — audit's "Current UX Strengths" #1, #5. (`SectionNavigationRail` itself is addressed in the dedicated row above — re-based on `GroupedNavigationRail`, not left unchanged, per D7.) |
| `MetricCard` / `KpiStrip` | **Kept**, reused for Overview's tiles (§6). |
| `EmptyState` | **Kept**, extended with the new "restricted" variant (§15). |
| `StatusChip` | **Kept, unchanged** — audit's own finding that this is already centralized and consistent. |
| `Dialog` (`EntityDialog`) | **Kept**, extended with the width-token set (§13). |
| `FormField` / `CodeFieldRow` | **Kept, unchanged.** |
| `ConfirmationDialog` | **New** — backs genuinely-destructive actions (Calendar Exception/Recurring Event delete, Module Entitlement Lifecycle/Licensed/Enabled) and **deactivate**-direction toggles (naming the entity and the consequence), per D5 (§8, §14) — **DECIDED, D5**. **Not** used for the **activate**-direction toggle, which stays a direct action confirmed only by a toast/`InlineMessage` (no blocking dialog, no generic undo). |
| `PermissionState` | **New** (the QML-only "restricted" variant of `EmptyState`, §15) — not a full permission system. |
| `WorkspaceOverviewPage` | **New** — generalizes the `admin_presenter.build_overview()`-style KPI+sections pattern (already proven in today's Admin Console overview and Control/Settings' own KPI strips) into one reusable Overview-page shell, backing §6. |

---

## 17. Theme: Dark Mode

**Current state (audit §16, independently re-confirmed):** `AppTheme.qml` is a single fixed light palette
with zero conditional branching; `themeMode` is tracked in `ShellContext` and displayed in Settings → Runtime
but never consumed to change a single color — a fully dead lever.

**Target:** `AppTheme` gains a light and dark token set, switched on `themeMode`, exposed as a real toggle in
Settings → Runtime (§11). This is **pure QML/token work** — `themeMode` already exists and is already
plumbed from `ShellContext` into QML (`SettingsRuntimeSection.qml:90` already reads it); the gap is
entirely on the token-definition side, not the plumbing side. In scope for **R7**.

## 18. Density

Same shape as dark mode: `densityMode` (`compact`/`comfortable`/`spacious`) already drives real tokens
(`AppTheme.qml:8-12, 67-116`) but has no UI control anywhere. Target: a real setter in Settings → Runtime,
same location as the dark-mode toggle. **R7** scope, pure QML/token work, no backend dependency.

## 19. Responsive / Window-Resize Behavior

**Current state (audit §19, re-confirmed):** `ApplicationWindow` has a fixed *initial* size (1280×800,
`App.qml:14-15`) but no `minimumWidth`/`minimumHeight` guard anywhere, and no breakpoint logic exists — the
audit correctly could not determine what happens below some width without runtime verification.

**Target — DECIDED, D8:** 1024px is adopted as the minimum target window width for the redesign, treated as
an R0 design constraint with **mandatory runtime validation in R8** (not merely a design-time assumption).
This is a decision, not yet a measurement — if R8's runtime testing proves 1024px unusable for required
workflows, the minimum is revised based on the measured layout behavior at that point, not asserted again
here without evidence.

- Add an explicit `minimumWidth: 1024` (`minimumHeight` value still to be confirmed in R8) guard to
  `App.qml` — the 469px nav chrome (§0) plus a legible minimum content width at 1024px total.
- **The layouts must degrade intentionally at the 1024px minimum — not every pane is guaranteed
  simultaneously visible:**
  - The **inspector** (§7) is the panel most likely to collapse or close first, since it is the third of
    three panes in the list→inspector→detail pattern.
  - Labels may reduce (icon-only nav, abbreviated column headers).
  - Table columns may adapt (lower-priority columns hidden first, per existing `DataTable` column-priority
    conventions where they exist).
  - `GroupedNavigationRail`-based navigation (§16, D7) may auto-collapse to its icon-only width below a
    defined breakpoint, rather than only via manual user toggle as today — the exact breakpoint is defined
    precisely during R7 implementation, not asserted here as a specific pixel number without verification.
- No `SplitView`/resizable-pane work is in scope (§16 — `MasterDetailLayout` is deleted, not revived).
- This degradation behavior, and the 1024px figure itself, are validated at runtime in R8 (§23); this
  document specifies the *intent* (graceful, prioritized collapse) but not final per-breakpoint pixel
  values.

---

## 20. Target Component Library — see §16 (consolidated there to avoid duplicating the same table).

---

## 21. Old → New QML Component Mapping

| Old | New | Notes |
|---|---|---|
| `ShellDrawer.qml` | Unchanged (global nav only, now routes to 1 Platform entry instead of 4) | |
| `AdminNavSidebar.qml`, `SettingsSidebarNav.qml` | `PlatformNavigation` (new top-level rail, composed from the shared `GroupedNavigationRail` primitive, §16) — **DECIDED, D7** | Both deleted, replaced by one component instance configured for Platform's full target IA (§3); their duplicated hardcoded `collapsed ? 48 : 220` literals are replaced by `AppTheme`'s canonical nav tokens (§0, §16) |
| `SectionNavigationRail.qml` (detail-page-internal) | **Kept as a named specialization**, re-implemented on top of `GroupedNavigationRail` — **DECIDED, D7 (not** turned into the universal navigation base itself, and **not** left as a third, un-migrated hand-rolled implementation) | |
| `AdminEntityDetailPanel.qml` | `InspectorPanel` (generalized, `visible` wired to selection) | Content bindings largely reused, not rewritten |
| `AdminConsolePage.qml`, `ControlWorkspacePage.qml`, `SettingsWorkspacePage.qml`, `TenantManagementWorkspacePage.qml` | Merged into one Platform workspace shell + per-section content panels | The 4 pass-through `*Workspace.qml` files and the routes registering them (`platform/routes.py`) collapse into 1 |
| `AdminWorkspaceState.qml`, `ControlWorkspaceState.qml` | One shared Platform workspace state object (activeSection now spans the full target IA, not just Admin's 11 leaves) | |
| `AccessSecurityPanel.qml` | Normalized into the standard list+inspector+detail composition (§9) — file likely still exists but restructured internally, not a 1:1 survivor | |
| `ControlWorkspacePage.qml`'s Escalations/System Events tab markup | **Deleted entirely** (§10) — **DECIDED, D2** | The tab-bar architecture is not structurally closed to re-adding these later once real backend/product semantics exist; nothing is added now that only *simulates* future availability |
| `SettingsDefaultsSection.qml`, `SettingsSecuritySection.qml` | **Deleted** — **DECIDED, D4**, per-value: Locale & Fiscal's real per-org fields (`organization.py:20-21`) and Session Policy's real per-user override (`session_service.py:89-106`) are **not** relabeled/kept on these pages (no genuine *global default* backend exists for either); the remaining cards on both pages have zero backend today | Settings IA shrinks to Modules/Integrations/Runtime/Diagnostics (§11); genuine global Locale/Fiscal and Session-Policy defaults are explicit non-goals of this redesign (§25), addable later through their own real backend contract |
| `MasterDetailLayout.qml` | **Deleted** | dead code today, stays dead |
| `AdminCatalogPanel.qml`, `SettingsOverviewSections.qml` | **Deleted** | confirmed dead code today |
| `WorkspaceStateBanner.qml` (Platform's copy only) | **Deleted** | Platform's own unused copy; the other modules' separate copies are out of this document's scope |
| `sections/ControlMetricsSection.qml` | **Deleted** | superseded by inline `KpiStrip` usage, per audit's "Inferred unused/legacy" finding |
| `TenantSwitcher.qml` (header) | Becomes the **Tenant** half of the new `ContextBar` (§5) | Same controller binding, new visual host |
| `TenantManagementWorkspacePage.qml` | Kept as the "Tenant Administration" section (§12), decoupled from being a duplicate of the header control | |
| All 15 `*EditorDialog.qml` files | Kept, mechanically updated to use the new dialog-width tokens (§13) | No content/field changes |
| `DataTable.qml`, `TableToolbar.qml`, `EntityDialog.qml`, `SectionDetailPage.qml`, `ContextualActionToolbar.qml`, `StatusChip.qml`, `InlineMessage.qml`, `EmptyState.qml`, `CodeFieldRow.qml`, `FormField.qml`, `KpiStrip.qml`, `MetricCard.qml`, `ActivityFeed.qml`, `LazySectionLoader.qml`, `LazyObjectLoader.qml` | **Kept, unchanged or additively extended only** | The audit's "reused well" list (§25) — explicitly not redesign targets |

---

## 22. Files: Reuse / Redesign / Delete

**Reuse verbatim (no change needed):** `DataTable.qml`, `TableToolbar.qml` (until filter-slot extension,
§14), `EntityDialog.qml`, `SectionDetailPage.qml`, `ContextualActionToolbar.qml`, `StatusChip.qml`,
`InlineMessage.qml`/`SectionScopedInlineMessage.qml`, `EmptyState.qml` (until §15 extension),
`CodeFieldRow.qml`, `FormField.qml`, `SectionCard.qml`, `SectionHeading.qml`, `ActivityFeed.qml`,
`LazySectionLoader.qml`/`LazyObjectLoader.qml`, `AdminInformationalDetailSection.qml`,
`AdminDetailTableSection.qml`, `AdminCalendarAssignmentSection.qml`, all 15 `Platform/Dialogs/*.qml` files
(content unchanged, width tokens applied), all 11 `Admin*DetailPage.qml` files (unchanged content, adopt
the shared `GroupedNavigationRail`/`InspectorPanel` primitives only where their *own* internal nav is
concerned, which today they don't have — no change needed there either), every per-entity
controller/presenter/view-model file listed in the audit's §4 (`organization_controller.py` through
`document_structure_controller.py` and their presenters) — **zero backend/controller changes are in scope
for this redesign** except where a specific section above calls one out as a dependency.

**Redesign (structure/behavior changes, content/logic mostly preserved):** `ShellDrawer.qml` (route count
only), `AdminNavSidebar.qml` + `SettingsSidebarNav.qml` → deleted, replaced by new `PlatformNavigation`
(composed from the new `GroupedNavigationRail` primitive, §16 — **DECIDED, D7**),
`SectionNavigationRail.qml` → re-implemented on top of the same new `GroupedNavigationRail` primitive
(kept as a named specialization, not replaced or left as a third hand-rolled implementation — **DECIDED,
D7**), `AdminEntityDetailPanel.qml` → `InspectorPanel.qml` (turn on + generalize), `AdminConsolePage.qml` +
`ControlWorkspacePage.qml` + `SettingsWorkspacePage.qml` + `TenantManagementWorkspacePage.qml` → merged
Platform workspace shell, `AccessSecurityPanel.qml` (normalize interaction model, §9),
`TenantSwitcher.qml` (rehost into `ContextBar`), `platform/routes.py` (4 routes → 1),
`platform/context.py` (catalog wiring adjusted for one workspace, controller set unchanged),
`AppTheme.qml` (extended with dark-mode/density/dialog-width/nav-dimension tokens, not replaced),
`AdminAuditSection.qml`/Control's audit surface (read-contract normalized into the single Control →
Governance → Audit destination, §10 — **DECIDED, D3**; the underlying `control_queue_presenter.py` and
`admin_presenter.py` service layers are *not* merged, only the UI-facing read contract is normalized).

**Delete:** `MasterDetailLayout.qml`, `AdminCatalogPanel.qml`, `SettingsOverviewSections.qml`,
`WorkspaceStateBanner.qml` (Platform's copy), `sections/ControlMetricsSection.qml`, the 4 pass-through
`*Workspace.qml` wrapper files (superseded by the merged shell), the duplicate Admin Audit destination
superseded by the D3 merge, and — **DECIDED, no longer pending** — `SettingsDefaultsSection.qml`,
`SettingsSecuritySection.qml` (D4), and the Escalations/System-Events markup inside
`ControlWorkspacePage.qml` (D2).

---

## 23. Implementation Phases (R1–R8)

| Phase | Scope | Depends on |
|---|---|---|
| **R1 — Design-system foundation** | `AppTheme` extension (dark-mode tokens, density-control wiring, dialog-width tokens, centralized `GroupedNavigationRail` dimension tokens replacing the duplicated `collapsed ? 48 : 220` literals, §0/§16 — **DECIDED, D7**); new shared components: `GroupedNavigationRail` (new low-level primitive), `PlatformNavigation` (composed from it), `ContextBar`, `InspectorPanel` (generalized from `AdminEntityDetailPanel`), `ConfirmationDialog` (scoped per D5's asymmetric activate/deactivate split, §16), `PermissionState`; `TableToolbar` filter-slot extension. **No Platform page is touched yet.** | This document (R0), approved |
| **R2 — Shell + Platform navigation** | Collapse the 4 top-level routes into 1 (`platform/routes.py`), build the merged Platform workspace shell using R1's `PlatformNavigation` + `ContextBar`, wire the target IA (§3) as navigation data, missing-icon audit for the new single entry | R1 |
| **R3 — Platform Overview / Admin home** | New Overview page using R1's `WorkspaceOverviewPage` shell, wired to already-backed data only (§6's "Yes" rows); the two breakdown tiles explicitly excluded pending backend backlog | R1, R2 |
| **R4 — Master-data list/detail experience** | Turn on `InspectorPanel` for all 9 Admin entities (§7); Delete button/`[•••]` removed from the inspector per D1 (**DECIDED** — no backend delete added; future delete/archive is a separate product/domain decision) | R1, R2 |
| **R5 — Access / Control / Settings / Tenant experiences** | Roles & Access normalization (§9), including D5's deactivate-style confirm on Revoke-Access/session actions; Control Escalations/System-Events removed per D2 (**DECIDED**); Settings Defaults/Security removed per D4 (**DECIDED** — Settings IA shrinks to Modules/Integrations/Runtime/Diagnostics); Support merges into Diagnostics (§11); Tenant Administration decoupled from header duplication (§12); Control/Admin Audit merge per D3 (**DECIDED** — UI read-contract normalization only, service layers not merged) resolved and applied | R1–R4 |
| **R6 — Forms, dialogs, actions, filtering, pagination** | Dialog width tokens applied to all 15 dialogs; `ConfirmationDialog` wired per D5 (genuinely-destructive actions + deactivate-direction toggles only; activate stays direct+toast); real filter controls sequenced per D4 (**DECIDED** — Audit/Control surfaces first, since `showFilter`+backend params already exist; master-data lists remain search-only in this release, no client-side filtering of materialized collections); pagination either removed-until-backed or wired to a real paginated Reader if that backend work is separately prioritized | R1–R5 |
| **R7 — Theme, density, accessibility, responsive behavior** | Dark-mode toggle wired end-to-end; density toggle wired end-to-end; `minimumWidth: 1024`/`minimumHeight` added per D8 (**DECIDED**); `GroupedNavigationRail` auto-collapse breakpoint defined and implemented, along with the other §19 degradation behaviors (inspector collapse, label reduction, column adaptation) | R1 (tokens), can run partly in parallel with R2–R6 once R1 lands |
| **R8 — Cleanup, migration, visual/regression testing** | Delete all files listed in §22's Delete list; remove the 4 old pass-through workspace files and old routes; full visual regression pass across every screen in §24's ASCII catalogue; confirm no `qmldir` breakage from folder reorganization (audit §26's constraint); **mandatory runtime validation of the 1024px minimum-width decision and its degradation behavior (§19, D8)** — if unusable for required workflows, revise the minimum based on measured behavior rather than this document's assumption | R1–R7 |

Each phase should close with the same discipline the CQRS backend modernization used: a baseline
measurement where relevant (e.g., R4's before/after click-to-inspect interaction count), an explicit
regression check against the existing test suite plus any new QML-behavior tests, and no phase silently
expanding into the next.

---

## 24. Target-State ASCII Wireframe Catalogue

### A. Platform Overview

```
┌────────────────────────────────────────────────────────────────────────────────────┐
│ Global Header                                                                       │
├───────────────┬──────────────────────────────────────────────────────────────────┤
│ Global Drawer │ Platform      Tenant: TECHASH ▾    Organization: Hamburg GmbH ▾     │
│               ├──────────────────────────────────────────────────────────────────┤
│ ▸Shell        │ Platform Nav  │ Overview                                          │
│ ▾Platform◀    │ ▸Overview◀    │ ┌ Workforce ─────────────────────────────────────┐│
│ ▸Project Mgt  │ ▸Organization │ │[Employees 148][Active 143][Sites 6][Depts 12] ││
│ ▸Maintenance  │ ▸Calendars    │ │[Users 34][Documents 210]                       ││
│ ▸Inventory &  │ ▸Identity &   │ └─────────────────────────────────────────────────┘│
│  Procurement  │  Access       │ ┌ Access & Governance ───────────────────────────┐│
│               │ ▸Documents    │ │ Pending Approvals: 7      Recent Activity:     ││
│               │ ▸Control      │ │                            • Role changed...   ││
│               │ ▸Settings     │ │                            • Org updated...    ││
│               │ ▸Tenant Admin │ └─────────────────────────────────────────────────┘│
│               │               │ ⚠ Department/Site breakdowns not yet available    │
└───────────────┴───────────────┴──────────────────────────────────────────────────────┘
```

### B. Organization → Employees (list + inspector)

See §7's wireframe verbatim — applies identically to Organizations/Sites/Departments/Parties, columns
varying per the audit's §11.1-11.9 column lists (unchanged from today).

### C. Identity & Access → Roles & Access (normalized)

See §9's wireframe verbatim.

### D. Identity & Access → Users

```
┌ Users ──────────────────────────────────────────────────────────────────────────┐
│ [🔍 Search users...]  Status ▾                                     [+ User]     │
├─────────────────────────────────────────────┬─────────────────────────────────────┤
│ Display Name    Username     Status         │ Jane Doe                            │
│───────────────────────────────────────────── │ jane.doe                            │
│ Jane Doe    ◀   jane.doe     Active           │                                     │
│ ...                                          │ Status: Active                      │
│                                               │ Security: Sessions active           │
│                                               │                                     │
│                                               │ [Open]  [Edit]                      │
└───────────────────────────────────────────────┴─────────────────────────────────────┘
```
(No Delete/`[•••]` action — removed per D1, DECIDED. No backend delete capability exists for this or any of
the 9 master-data entities; adding one is a separate product/domain decision, not part of this redesign.)

### E. Calendars (own top-level group)

```
┌ Calendars ──────────────────────────────────────────────────────────────────────┐
│ [🔍 Search calendars...]                                       [+ Calendar]     │
├─────────────────────────────────────────────┬─────────────────────────────────────┤
│ Calendar        Working Days   Status        │ Standard 5-Day                      │
│───────────────────────────────────────────── │ GLOBAL · Default                    │
│ Standard 5-Day◀ Mon-Fri        Active          │                                     │
│ Hamburg Plant   Mon-Sat        Active          │ [Open]  [Edit]                      │
└───────────────────────────────────────────────┴─────────────────────────────────────┘
```
(Full detail page — Overview / Working Rules / Exceptions / Recurring Events / Assignments / Calculator /
Audit — unchanged from `AdminCalendarDetailPage.qml` today, per §8.)

### F. Documents

Unchanged list+inspector shape; detail page keeps the rich `DocumentDetailPanel`-based Overview
(§8/audit §11.8), unchanged.

### G. Control (Governance) → Approvals

```
┌ Control (Governance)                                                             │
│ [Approvals 7] [Audit]                                                            │
├ Approvals ────────────────────────────────────────────────────────────────────────┤
│ [🔍 Search...] Status ▾                                                          │
├───────────────────────────────────────────────────────────────────────────────────┤
│ Request          Type          Status       Requested                            │
│─────────────────────────────────────────────────────────────────────────────────── │
│ PO-4821       ◀  Purchase Ord  Pending      2026-08-10                            │
├───────────────────────────────────────────────────────────────────────────────────┤
│ 1–25 of 7                                                                         │
└───────────────────────────────────────────────────────────────────────────────────┘
```
(Confirmed, DECIDED: Escalations/System Events tabs removed entirely per D2 — not a tentative or
pending-decision state. Audit tab is the merged `Control → Governance → Audit` destination per D3 —
Admin's separate Audit leaf is removed, not duplicated. "Control (Governance)" is a descriptive framing;
the literal route/tab label remains "Control" per §3 — exact copy confirmed in R2.)

### H. Settings → Modules

Unchanged from today's `SettingsModulesSection.qml`/`SettingsModuleDetailPage.qml` (§13.2), now reached via
`Platform → Settings → Modules` instead of a separate top-level "Settings" route.

### I. Tenant Administration

```
┌ Tenant Administration ──────────────────────────────────────────────────────────┐
│                                                                    [Refresh]     │
├───────────────────────────────────────────────────────────────────────────────────┤
│ ● TECHASH (Current)                                                              │
│ ● Northwind Retail                                            [Switch]          │
│ ○ Suspended Co.                                    Suspended  [Switch — disabled]│
└───────────────────────────────────────────────────────────────────────────────────┘
```
(Unchanged content from today's `TenantManagementWorkspacePage.qml`; only its relationship to the header
context bar changes, §12.)

---

## 25. Explicit Non-Goals / Backend Dependencies (do not silently absorb into R1–R8)

The following are named *in* this design document because the user's own sketch referenced them, but are
**not** part of this QML redesign's guaranteed scope, per Design Principle 5:

- **Employees-by-Department / Employees-by-Site breakdowns** (§6) — needs new backend rollup work; tracked
  as backlog in the CQRS modernization audit, explicitly deferred there, not re-opened by this document.
- **Real server-side pagination** (§14) — needs a paginated Reader (P1/P6-style precedent), a backend
  decision, not a QML change.
- **True permission-category-aware UI** (§15) — needs `serialize_operation_result` to carry a real
  permission category; today it doesn't.
- **Tenant create/edit/provision UI** (§12) — no such capability exists in the backend-facing UI layer
  today; not proposed here.
- **A real Delete capability for the 9 Admin master-data entities** (§7, §14) — currently doesn't exist at
  all. **DECIDED, D1 (§26):** the inspector's Delete button is removed, unconditionally; this document does
  not add delete capability, and any future delete/archive semantics are a separate product/domain decision.
- **A genuine platform-wide Locale & Fiscal default** (§11) — the only backend data found (`organization.py:
  20-21`'s `timezone_name`/`base_currency`) is per-org, not a genuine global default; **DECIDED, D4 (§26):**
  `SettingsDefaultsSection.qml` is deleted rather than relabeled to display the per-org value as if it were
  a global one. A real global default, if ever needed, is a separate backend effort.
- **A genuine global Session Policy default** (§11) — the only backend data found
  (`session_service.py:89-106`'s `session_timeout_minutes_override`) is per-user, not a genuine global
  default; **DECIDED, D4 (§26):** `SettingsSecuritySection.qml` is deleted for the same reason as above.

---

## 26. Decisions — DECIDED (user-approved 2026-08-13)

**Status: all 8 items below are DECIDED.** The user reviewed the R0.1 closure pass's recommendations and
approved 5 as recommended (D1, D2, D3, D6, D8 — each with an added constraint, noted below) and changed 3
substantially (D4, D5, D7 — the actual decided outcome differs from what R0.1 recommended; see each item's
"FINAL DECISION" callout in the R0.1 section below for the full reasoning). R1 may now begin.

1. **Inspector Delete button** (§7) — **DECIDED: remove entirely** from the inspector until a real delete
   capability exists. *Added constraint:* do not add delete backend functionality as part of this QML
   redesign; if delete/archive semantics are introduced later, that is a separate product/domain decision.
2. **Control Escalations/System Events tabs** (§10) — **DECIDED: remove both entirely.** *Added
   constraint:* the tab-bar architecture may leave room for these to return later, but only once real
   backend/product semantics exist — nothing simulating future availability is added now.
3. **Control Audit tab vs. Admin Audit leaf** (§10) — **DECIDED: same underlying data source, confirmed;
   merge into one `Control → Governance → Audit` destination**, removing the duplicate Admin Audit
   destination. *Added constraint:* do not unnecessarily merge unrelated service layers just to achieve the
   UI consolidation — normalize the read contract only, not `control_queue_presenter.py`/`admin_presenter.py`
   themselves.
4. **Settings Platform Defaults / Security sections** (§11) — **DECIDED (changed from R0.1's
   recommendation): delete both sections**, per-value, not relabeled wholesale. Real per-org/per-user data
   that exists (Locale & Fiscal, Session Policy) is not kept on these pages merely by relabeling — there is
   no genuine *global default* backend for either. See D4's FINAL DECISION callout below.
5. **Toggle-active confirmation UX** (§14) — **DECIDED (changed from R0.1's recommendation): asymmetric,
   not a universal toast-with-undo.** Activate = direct action + toast. Deactivate = blocking confirmation
   naming the entity and the consequence. Genuinely destructive actions (Calendar Exception/Recurring Event
   delete, Module Entitlement Lifecycle/Licensed/Enabled) keep blocking confirmation regardless of
   direction. See D5's FINAL DECISION callout below.
6. **Filter scope** (§14, §16) — **DECIDED: Audit/Control first** (backend already supports it via
   `showFilter`/`list_recent(entity_type, operation, severity)`); master-data lists stay search-only in the
   first redesign release, with no client-side filtering of materialized collections. Future master-data
   filtering is added deliberately through a real desktop API/query contract.
7. **`SectionNavigationRail` vs. shared navigation** (§21) — **DECIDED (changed from R0.1's
   recommendation): do NOT turn `SectionNavigationRail` itself into the universal navigation base.** Extract
   a new, lower-level primitive (`GroupedNavigationRail`) that both `SectionNavigationRail` (kept as a named
   detail-page specialization) and a new top-level `PlatformNavigation` compose from. See D7's FINAL
   DECISION callout below.
8. **Minimum window width** (§19) — **DECIDED, provisionally: 1024px**, treated as an R0 design constraint
   with mandatory runtime validation in R8. Layouts must degrade intentionally at this minimum (inspector
   may collapse/close, labels may reduce, columns may adapt, navigation may collapse) — not every pane is
   guaranteed simultaneously visible. If R8's runtime testing proves 1024px unusable for required workflows,
   the minimum is revised based on measured behavior.

All 8 decisions are now propagated consistently throughout §§0–25 and §27 above. R1 (design-system
foundation) may begin.

---

## R0.1 — Design Decision Closure

Every item from §26 turned into an explicit, evidence-backed decision. This section's per-item numbered
write-ups (1-8 below) are preserved as originally written — **each still carries this pass's original
recommendation and reasoning as an audit trail**, since three of the eight decisions were subsequently
**changed** by the user rather than approved as recommended. Investigating these also surfaced sharper
evidence than §26 itself had (in particular D3's audit feeds and D6's filter-backend readiness, detailed
below) — no *new* decisions were created; every item maps 1:1 onto §26's original 8.

**Update — user decisions received and applied 2026-08-13:** D1, D2, D3, D6, D8 were approved substantially
as recommended (each with an added constraint, see §26). D4, D5, D7 were **changed** — the user's actual
decision differs from this pass's original recommendation. Each changed item's write-up below ends with a
**FINAL DECISION** callout stating the actual outcome; the original recommendation/reasoning above each
callout is kept for context, not as the operative decision. §26 above holds the authoritative current
status for all 8.

### Compact decision table

| ID | Decision | Original recommendation | **Final decision (2026-08-13)** | Blocks |
|---|---|---|---|---|
| D1 | Inspector Delete button | Remove the button until a real delete capability exists | **DECIDED as recommended** — remove; no backend delete added as part of this redesign | R4, R7 (file list), R8 (cleanup) |
| D2 | Control Escalations/System Events tabs | Remove both tabs entirely | **DECIDED as recommended** — remove both entirely | R5, R8 (file list) |
| D3 | Control Audit tab vs. Admin Audit leaf | Merge into one `Control → Audit` destination | **DECIDED as recommended** — merge into `Control → Governance → Audit`; UI read-contract normalization only, service layers not merged | R5, R3 (Overview's Recent Activity source) |
| D4 | Settings Platform Defaults / Security | Keep, relabeled as read-only reference (not deleted) | **CHANGED — delete both, per-value** (no relabel-and-keep); no genuine global-default backend exists for either section's content | R5, R8 (file list) |
| D5 | Toggle-active confirmation UX | Toast-with-undo, not a blocking dialog | **CHANGED — asymmetric**: activate = direct + toast; deactivate = blocking confirm naming entity + consequence; genuinely-destructive actions keep blocking confirm regardless of direction | R6 |
| D6 | Filter scope | Audit/Control queues get real filters first; master-data entity lists get search-only | **DECIDED as recommended** | R6 |
| D7 | `SectionNavigationRail` vs. new `NavigationRail` | Extend `SectionNavigationRail` with collapse behavior; make it the shared base | **CHANGED — reject `SectionNavigationRail` as universal base.** Extract new low-level `GroupedNavigationRail` primitive; `SectionNavigationRail` stays a named specialization built on it; new `PlatformNavigation` is the top-level rail, also built on it | R1 (foundation), R7 (responsive collapse) |
| D8 | Minimum window width | 1024px, pending runtime confirmation in R8 | **DECIDED as recommended, provisionally** — 1024px, mandatory R8 runtime validation, graceful degradation (not all panes guaranteed visible) | R7, R8 |

---

### D1 — Inspector Delete button

**1. Decision, restated:** When the master-data inspector (`InspectorPanel`, §7/§16) is switched on, its
**Delete** button today does nothing. Should it be wired to a real delete capability, or removed?

**2. Current behavior, file:line:** `AdminEntityDetailPanel.qml:374-382` — the Delete button exists in the
QML tree with `onClicked: {}`, an explicitly empty handler. Audit §17, independently re-confirmed: **no**
delete action exists anywhere in Admin Console for any of the 9 master-data entity types (Organizations,
Sites, Departments, Employees, Users, Parties, Documents, Document Structures, Calendars) — not on the
inspector, not on the full detail page, not on the list. The only real delete capability in all of
Platform is Calendar Exceptions/Recurring Events (a sub-record, not a master-data entity), and it fires
with zero confirmation.

**3. Why it matters to R1–R8:** the moment the inspector is switched `visible: true` (R4), a
previously-invisible dead button becomes newly visible and clickable, actively demonstrating Principle 1/2's
violation in a place users will now actually see, rather than passively existing unseen as today.

**4. Alternatives:**
- (a) Remove the button entirely from `InspectorPanel` until a real delete exists.
- (b) Wire it to a genuinely new delete capability, added as part of this redesign.
- (c) Leave it present but visibly disabled with a tooltip ("Delete is not available for this record type").

**5. Recommended: (a) Remove.**

**6. Reasoning:**
- *Enterprise UX consistency:* an action that appears identical to every other enabled action but does
  nothing is worse than no action at all — enterprise users learn to distrust chrome that doesn't work.
- *Usability:* zero cost — nothing today depends on this button doing anything, since it never has.
- *Information architecture:* unaffected either way.
- *Safety:* removing is strictly safer than adding untested delete capability for 9 entity types with
  unknown cascade/referential-integrity implications (Organizations cascade to Sites, Departments,
  Employees, etc. — a real delete feature is a significant, separate backend design question, not a QML
  afterthought).
- *Implementation complexity:* (a) is a one-line removal; (b) is an entire new backend capability
  (cascade rules, RLS/tenant-scope checks, confirmation UX, audit-trail requirements) explicitly out of
  this redesign's scope per Design Principle 5 and §25's Non-Goals.
- *Reuse of existing capability:* none exists to reuse — this is the crux of why (b) is disproportionate
  to a UI redesign.
- *Impact on future web/SaaS UI:* a genuine delete-with-cascade feature is exactly the kind of decision
  that should be made once, deliberately, with the eventual web/SaaS surface in mind (soft-delete? audit
  retention? tenant-admin-only?) — not implicitly decided by which button a Platform QML redesign happened
  to wire up first.

**7. Phases affected:** R4 (inspector goes live — this is where the dead button would otherwise become
newly visible), R7 (file-list impact if `InspectorPanel` needs the button removed vs. added), R8 (cleanup
verification that no dead handler remains).

**8. Spec sections that change if approved:** §7 (state explicitly that Delete is omitted from the
inspector), §14 (remove Delete from the destructive-action confirmation list — nothing to confirm), §22
(remove the conditional file-list language), §25 (already lists "a real Delete capability" as a Non-Goal —
becomes unconditional rather than conditional on this decision).

> **FINAL DECISION (user, 2026-08-13) — DECIDED as recommended**, with an added constraint: do not add
> delete backend functionality as part of this QML redesign; if delete/archive semantics are introduced
> later, that is a separate product/domain decision, not an implicit side effect of this redesign.

---

### D2 — Control Escalations / System Events tabs

**1. Decision, restated:** Control Center's **Escalations** and **System Events** tabs currently render
populated-looking empty tables that are permanently empty by construction, not by real state. Remove them,
or keep them with an explicit "not yet available" treatment?

**2. Current behavior, file:line:** `ControlWorkspacePage.qml:259-271` (Escalations) and `:290-302` (System
Events) each instantiate a `DataTable` with a literal `rows: []` array (not a controller-bound property)
and hardcoded `emptyText` strings ("No active escalations — all requests are within SLA", "No system
events recorded in this session"). Confirmed: `control_workspace_controller.py` has **no** property for
either concept at all — not a stubbed-empty one, an **absent** one. Both tabs also already have
`showFilter: true` set (`ControlWorkspacePage.qml:284` for one of them, confirmed during this closure
pass), compounding the appearance of functionality with none behind it.

**3. Why it matters:** these two tabs are the clearest single instance in all of Platform of "looks
100% real, is 0% real" — the empty-state text is deliberately worded as if real monitoring exists ("all
requests are within SLA" implies SLA tracking that doesn't exist).

**4. Alternatives:**
- (a) Remove both tabs entirely from the target Control section.
- (b) Keep both tabs, replace the fake populated-empty-state text with an explicit "Escalations is not yet
  available" / "System Events is not yet available" treatment (visually distinct from a genuine empty
  state).

**5. Recommended: (a) Remove entirely.**

**6. Reasoning:**
- *Enterprise UX consistency:* a tab bar item that always says "not available" is itself confusing chrome
  — users will ask why it's there at all if it can never do anything today.
- *Usability:* removing reduces the tab bar from 4 to 2 real items (Approvals, Audit), which is a clearer,
  more honest surface, not a diminished one.
- *Information architecture:* two fewer nodes in Control's IA, consistent with Design Principle 2.
- *Safety:* no risk either way — these are read-only stubs today.
- *Implementation complexity:* (a) is strictly less work than (b) — deleting markup vs. building a new
  "not available" state component that then has to be un-shipped later once real backend work exists.
- *Reuse of existing capability:* neither tab reuses anything today; nothing is lost by removing them.
- *Impact on future web/SaaS UI:* if/when real escalation or system-event monitoring is scoped as its own
  backend effort, it should get its own fresh IA placement decision at that time, informed by whatever that
  feature actually turns out to need — not resurrect a placeholder tab that was speculative from the start.

**7. Phases affected:** R5 (Control section build-out), R8 (file-list cleanup — the markup inside
`ControlWorkspacePage.qml` for both tabs is deleted, not migrated).

**8. Spec sections that change if approved:** §10 (state removal as final, not conditional), §21 (mapping
table's "pending §26 decision" line becomes definitive), §22 (Delete list gains the Escalations/System
Events markup unconditionally), §24.G (wireframe already shows them removed — becomes the confirmed target,
not a tentative one).

> **FINAL DECISION (user, 2026-08-13) — DECIDED as recommended**, with an added constraint: the
> architecture may leave room for Escalations/System Events to return later, but they should only reappear
> once real backend/product semantics exist for them — nothing simulating future availability is added now.

---

### D3 — Control Audit tab vs. Admin Audit leaf

**1. Decision, restated:** Should Control's "Audit" tab and Admin Console's separate "Audit" leaf merge
into one `Control → Audit` destination in the target IA (as §3 tentatively proposed), or stay as two
distinct screens?

**2. Current behavior, file:line — resolved decisively during this closure pass, going further than R0
could:** both ultimately call the **same** application-service method.
- Control's Audit tab (`ControlWorkspacePage.qml:226-227`, `AppWidgets.ActivityFeed`) is fed by
  `control_queue_presenter.py:54-62`'s `build_audit_feed()`, which calls
  `self._audit_api.list_recent(limit=25)` — the desktop API's `list_recent`
  (`api/desktop/history/audit/audit_enterprise.py:33-51`).
- Admin's Audit leaf (`AdminAuditSection.qml`) is fed by `admin_presenter.py:97`'s
  `self._audit_api.list_for_overview(limit=50)` — a **different desktop-API method**
  (`audit_enterprise.py:53-59`) that itself does nothing but call
  **`self._service.list_recent(limit=limit)`** (line 56 — the exact same
  `EnterpriseAuditService.list_recent()` Control's path eventually reaches too) and reshape the result into
  feed-item dicts for the QML `ActivityFeed` widget.
- **Conclusion: same underlying data, same query method, same audit_entries table — the only differences
  are the `limit` (25 vs. 50) and the DTO shape (raw `AuditEntryDto` tuple vs. pre-formatted feed dicts),
  both cosmetic at the desktop-API layer, not different data sources.** This was genuinely unconfirmed in
  R0 (flagged as an open question, not assumed) and is now confirmed by tracing both call chains to their
  shared root method.

**3. Why it matters:** merging removes a real instance of the audit's "Platform is 4 sibling areas with
duplicated concepts" finding (§24) at near-zero cost, now that the data-source question is settled.

**4. Alternatives:**
- (a) Merge into one `Control → Audit` destination, standardizing on one limit/DTO shape.
- (b) Keep both, now knowingly duplicating the same data through two different desktop-API methods.

**5. Recommended: (a) Merge.**

**6. Reasoning:**
- *Enterprise UX consistency:* one "Audit" destination instead of two answers the audit's own §8/§24
  "why are these split" ambiguity directly, for this specific pair.
- *Usability:* one place to check recent audit activity instead of two, each showing a different-sized
  slice of the identical feed — currently a user who checks Admin's Audit and doesn't see something might
  reasonably (and wrongly) think Control's Audit would show something different.
- *Information architecture:* removes one duplicate leaf node from the target IA (§3).
- *Safety:* none — read-only data in both cases.
- *Implementation complexity:* low — standardize on one desktop-API method (recommend `list_for_overview`'s
  shape since it's already feed-ready for `ActivityFeed`, or expose a single new method with an explicit
  `limit` parameter instead of two fixed ones) and remove the now-redundant call site. This is a **small,
  in-scope QML/thin-wrapper change**, not new backend logic — `list_for_overview` already exists and
  already wraps `list_recent`; no new application-service method is required. Per Design Principle 5, this
  stays within "one method calls another that already exists," not a new backend capability.
- *Reuse of existing capability:* maximal — this decision's entire value is *not* building a second feed
  when one already serves both needs.
- *Impact on future web/SaaS UI:* a single canonical "recent audit activity" concept is easier to expose
  consistently on a future web surface than two parallel ones with different limits and no documented
  reason for the difference.

**7. Phases affected:** R3 (Overview's Recent Activity tile, §6, should point at this same merged source),
R5 (Control section build-out).

**8. Spec sections that change if approved:** §3 (target IA — Control's Audit becomes definitively the
one Audit destination), §10 (resolve the "requires confirming" language to "confirmed same source, merged"),
§6 (Overview's Recent Activity explicitly cites the merged source), §21 (mapping table entry finalized).

> **FINAL DECISION (user, 2026-08-13) — DECIDED as recommended**, with an added constraint: target UX is
> Platform → Control / Governance → Approvals → Audit, removing the duplicate Admin Audit destination; do
> not unnecessarily merge unrelated service layers just to achieve the UI consolidation — normalize the
> read contract only where it reduces genuine duplication, not `control_queue_presenter.py` and
> `admin_presenter.py` themselves.

---

### D4 — Settings Platform Defaults / Security sections

**1. Decision, restated:** Settings' **Platform Defaults** and **Security** sections show fixed,
non-editable cards with no backend binding. Delete them, or keep the content but relabel it as read-only
reference material?

**2. Current behavior, file:line:** `SettingsDefaultsSection.qml:53-89` — a literal JS array of 5 cards
(Locale & Fiscal, Data Management, Approval Workflow, Notification Defaults, Compliance & Governance) with
fixed label/value rows (e.g., "Default timezone" → "UTC+00:00 (configurable per org)"). Confirmed absent:
any corresponding property on `PlatformSettingsWorkspaceController`. Same pattern,
`SettingsSecuritySection.qml:54-78`, 4 cards (Password Policy, Session Policy, RBAC Defaults, Approval
Thresholds).

**3. Why it matters:** unlike D2's Control tabs (which represent a feature that plausibly doesn't exist
yet), these two sections' *content* (documenting default timezone conventions, password policy values,
etc.) may have genuine ongoing informational value even without becoming editable — the decision is really
about *labeling*, not necessarily about deletion.

**4. Alternatives:**
- (a) Delete both sections entirely.
- (b) Keep the content, relabel as explicitly read-only reference/documentation, remove any visual
  implication of editability (currently the section icon and card styling suggest configuration, per audit
  §13.3/§13.5).
- (c) Build real backend-backed editable settings behind them (out of scope — a backend effort, not a QML
  redesign task, per Design Principle 5).

**5. Recommended: (b) Keep, relabeled as read-only reference.**

**6. Reasoning:**
- *Enterprise UX consistency:* enterprise settings screens commonly do include a "these are our current
  policy defaults, contact an administrator to change them" reference block — the *problem* the audit found
  isn't that this information exists, it's that it's presented with Settings-editability visual language
  (cards, section icons implying configuration) it doesn't back up. Fixing the *labeling* addresses the
  actual UX problem without discarding content that may be genuinely useful reference for an admin.
- *Usability:* deleting removes potentially-useful reference information a user might actually want (e.g.,
  "what's our password expiry policy") with no replacement; relabeling preserves the information while
  fixing the misleading affordance.
- *Information architecture:* stays in Settings (or could move to a "Reference"/"Documentation" grouping if
  one exists elsewhere in the app — not investigated here, out of this redesign's traced scope), clearly
  distinguished from **Modules**/**Integrations** (which *are* genuinely editable).
- *Safety:* no behavior change either way.
- *Implementation complexity:* (b) is lower complexity than (a) done "properly" (a) still requires
  confirming nothing else references these sections before deleting, whereas (b) is a labeling/visual
  change to existing files, no removal risk.
- *Reuse of existing capability:* (b) reuses the existing content and layout almost entirely — only the
  section header/icon/framing changes.
- *Impact on future web/SaaS UI:* if these values genuinely become tenant-configurable later (a real
  product decision, not this one), having them already presented as "current defaults, documented" rather
  than deleted gives a natural place to wire in real editability later, rather than having to reinvent the
  screen from nothing.

**7. Phases affected:** R5 (Settings section build-out).

**8. Spec sections that change if approved:** §11 (resolve to "(b), relabeled" rather than open),
§21/§22 (mapping and file lists: both sections move from "possibly deleted" to "kept, relabeled" — remove
from the Delete list, note the relabeling in the Redesign list).

> **FINAL DECISION (user, 2026-08-13) — CHANGED from the recommendation above: delete both sections,
> per-value, not a wholesale relabel-and-keep.** The user's instruction: "Do NOT keep hardcoded Platform
> Defaults and Security pages merely by relabelling." The actual rule applied: for each individual value on
> both pages, check whether genuine backend data exists — if it does (Locale & Fiscal's per-org
> `organization.py:20-21` `timezone_name`/`base_currency`; Session Policy's per-user
> `session_service.py:89-106` `session_timeout_minutes_override`), it is **not** kept on these two Settings
> pages, because in both cases what exists is a **per-org/per-user** value, not a genuine **global default**
> — displaying it here under a "Platform Defaults" label would still misrepresent it. Where no backend data
> exists at all (Data Management, Approval Workflow, Notification Defaults, Compliance & Governance,
> Password Policy, RBAC Defaults, Approval Thresholds), the card is removed outright. No new backend is
> built solely to preserve any of these cards. **Net effect: `SettingsDefaultsSection.qml` and
> `SettingsSecuritySection.qml` are both deleted; Settings' target IA shrinks to Modules/Integrations/
> Runtime/Diagnostics only (§11).** A genuine platform-wide Locale & Fiscal default and a genuine global
> Session Policy default are explicit non-goals of this redesign (§25) — addable later through their own
> real backend contract, not resurrected here by relabeling.

---

### D5 — Toggle-active confirmation UX

**1. Decision, restated:** Toggling a record's active state (Organizations/Sites/Departments/Employees/
Users/Parties/Documents/Document-Structures' "Set Active", Module Entitlements' Licensed/Enabled) currently
fires immediately with zero confirmation. Should the target design add a blocking confirmation dialog
(consistent with how delete/lifecycle changes are being designed), or something lighter?

**2. Current behavior, file:line:** Audit §17, re-confirmed: direct one-click mutation, no confirmation
dialog anywhere for any toggle-active action. `SettingsModuleDetailPage.qml:129-136` — Licensed/Enabled
toggle buttons mutate immediately on click, no confirm step, for Module Entitlements specifically.

**3. Why it matters:** this is the **most frequent** mutation type in all of Admin Console (every one of
the 9 master-data entities has one), so the confirmation-UX choice here has an outsized effect on perceived
friction across the whole redesign — getting this wrong in either direction (too heavy, or genuinely unsafe)
affects more interactions than any other single decision in this closure pass.

**4. Alternatives:**
- (a) Blocking confirmation dialog (`ConfirmationDialog`, §16/§20) before every toggle, matching the
  treatment given to delete and module-lifecycle changes.
- (b) No confirmation step, but a toast/snackbar with an "Undo" action for a few seconds after the toggle
  fires, reusing the existing `InlineMessage`("success") pattern with an added action slot.
- (c) No change from today (no confirmation, no undo).

**5. Recommended: (b) Toast-with-undo.**

**6. Reasoning:**
- *Enterprise UX consistency:* delete and irreversible-by-inspection actions (module lifecycle changes,
  which can affect what other users see) reasonably warrant a blocking confirm; toggling a record active/
  inactive is trivially and immediately reversible by toggling it back — treating it with the same UX
  weight as delete would make the *whole redesign* feel heavier without a matching safety benefit,
  undermining the "enterprise feels substantially more mature" goal from a different direction (excessive
  modal-ness is its own audit finding category, "Enterprise administration semantics"/"Desktop ergonomics"
  in the original audit brief).
- *Usability:* a blocking dialog on the single most frequent Admin mutation would measurably slow down
  routine admin work (deactivating/reactivating records is a common bulk-adjacent task); undo-after-the-fact
  preserves speed while still giving a safety net.
- *Information architecture:* unaffected.
- *Safety:* toggle-active is not destructive in the way delete is (no data loss — the record persists,
  fully intact, either state), so the safety bar for "did the user really mean this" is genuinely lower;
  undo directly addresses the realistic failure mode (misclick) without the cost of a dialog for every
  correct click too.
- *Implementation complexity:* the toast/undo pattern reuses `InlineMessage`'s existing success-banner
  mechanism (audit §22's own praised pattern) plus one new "Undo" action slot and a re-invocation of the
  same toggle mutation in reverse — smaller than building and wiring a second `ConfirmationDialog` use case
  distinct from delete's.
- *Reuse of existing capability:* high — `InlineMessage`, `run_mutation` (call the toggle again with the
  opposite value on Undo) are both already-proven mechanisms.
- *Impact on future web/SaaS UI:* toast-with-undo is a very standard, well-understood web/SaaS interaction
  pattern (more so, arguably, than desktop blocking dialogs), so this choice ages well if/when a web surface
  is built later.

**7. Phases affected:** R6 (forms/dialogs/actions).

**8. Spec sections that change if approved:** §8 ("Confirmation on destructive/impactful actions" — split
into "blocking confirm: delete, module lifecycle" vs. "toast-with-undo: toggle-active"), §14 (same split
applied to its action-by-action list), §16 (`ConfirmationDialog`'s scope narrows to genuinely destructive
actions only; toast/undo may not need a new named component at all if `InlineMessage` is extended instead).

> **FINAL DECISION (user, 2026-08-13) — CHANGED from the recommendation above: not a universal
> toast-with-undo.** The user's instruction: "Do not make 'toast with undo' the universal behavior." The
> actual rule applied is **asymmetric by direction, not uniform by action type**:
> - **Activate** (turning a record back on) — direct action, confirmed only by a toast/`InlineMessage`. No
>   blocking dialog, no generic undo.
> - **Deactivate** (turning a record off) — a **blocking confirmation dialog** naming the specific entity and
>   the consequence of deactivating it (e.g., "Deactivate Jane Doe? She will lose access immediately."), not
>   a toast.
> - **Genuinely destructive actions** (Calendar Exception/Recurring Event delete, Module Entitlement
>   Lifecycle/Licensed/Enabled changes) keep a blocking confirmation **regardless of direction** — D5 only
>   governs the plain active/inactive toggle on the 9 master-data entities and Roles & Access-adjacent
>   Revoke-Access/session actions (§9), not lifecycle-affecting mutations.
> - **No generic "toast with undo"** is introduced as a standing pattern; that mechanism is reserved for a
>   future, genuinely lightweight/reversible/presentation-only action if one is identified later — it does
>   not become this redesign's default toggle-active treatment.
> This changes §16's `ConfirmationDialog` scope narrowing differently than recommended above: it backs
> **deactivate** and genuinely-destructive actions, not neither.

---

### D6 — Filter scope

**1. Decision, restated:** Which entities/screens get real filter controls in R6, and which ship with
search-only, given the audit found every Filter button today opens a static "will appear here" popup?

**2. Current behavior, file:line — sharper than R0 had it, from this closure pass's direct grep:**
`showFilter: true` is currently set on exactly four call sites: `AdminAuditSection.qml:67`,
`AdminSupportSection.qml:93`, and **two** places in `ControlWorkspacePage.qml` (line 170 — Approvals; line
284 — one of Escalations/System Events, moot per D2). **Zero** master-data entity lists
(Organizations/Sites/Departments/Employees/Users/Parties/Documents/Structures) or the Roles & Access grants
table set `showFilter` at all — `TableToolbar.qml:17`'s `property bool showFilter: false` is simply never
overridden for any of them. Separately: `EnterpriseAuditService.list_recent()`
(`enterprise_audit_service.py:98-121`) **already accepts** `entity_type`/`operation`/`severity` filter
parameters today — confirmed, not inferred. No equivalent filter parameters were found on any master-data
entity's list method during this pass (their `list_for_organization`-style methods take only
`active_only`, no richer filter surface).

**3. Why it matters:** this closure pass's evidence changes the shape of the decision from "design filters
for the entities that would benefit" (R0's framing) to "the backend readiness itself already tells you
where to start" — Audit/Control already has both the UI intent (`showFilter: true`) *and* the backend
capability (`entity_type`/`operation`/`severity` params) sitting unused; master-data lists have neither.

**4. Alternatives:**
- (a) Build real filters for Audit/Control first (near-zero new backend work — wire the existing
  `entity_type`/`operation`/`severity` params to the existing `AnchoredPopup` slot, replacing static text
  with real controls); leave master-data lists search-only until/unless a future backend effort adds filter
  parameters to those list methods.
- (b) Build filters everywhere at once, including inventing new backend filter parameters for master-data
  lists as part of this redesign.
- (c) Remove all Filter buttons everywhere (including Audit/Control) until a uniform filter treatment can
  ship for all of them simultaneously.

**5. Recommended: (a).**

**6. Reasoning:**
- *Enterprise UX consistency:* shipping Audit/Control's real filters first, and removing (not fake-keeping)
  master-data lists' filter buttons in the meantime (since none currently even have one — nothing to remove
  there, they simply don't get one added yet) keeps every visible Filter control genuinely functional at
  every point in the rollout — never a mix of "some fake, some real" simultaneously.
- *Usability:* Audit/Control's filter-by-severity/type/operation is a real, common task ("show me only
  critical events"); master-data list filtering (by Department/Site/Status, as R0's own wireframes showed)
  is also genuinely useful but not yet backed — shipping the backed one first delivers real value sooner
  rather than waiting to design all filters uniformly.
- *Information architecture:* unaffected.
- *Safety:* none.
- *Implementation complexity:* (a) is a small, mostly-QML change (wire existing backend params into the
  existing `AnchoredPopup`/`TableToolbar` filter slot) with **zero new backend work**; (b) requires
  scoping, designing, and building new backend filter parameters for up to 9 entity types — a
  disproportionately large addition to a QML redesign, and exactly the kind of scope creep Design
  Principle 5 exists to prevent; (c) throws away Audit/Control's already-backed capability for no benefit.
- *Reuse of existing capability:* (a) is the only option that uses what already exists on both the UI-intent
  side (`showFilter: true`) and backend side (`list_recent`'s params) rather than building net-new or
  discarding working intent.
- *Impact on future web/SaaS UI:* proves out one real, working filter pattern (Audit/Control) that a future
  master-data filter effort can extend, rather than inventing filter UX twice.

**7. Phases affected:** R6.

**8. Spec sections that change if approved:** §14 (filter section rewritten to state the Audit/Control-
first sequencing and the master-data search-only interim state explicitly, replacing the "per-entity
usefulness" framing with this evidence-based one), §7/§9's wireframes (the `Department ▾ Site ▾ Status ▾`
filter row shown there is retitled as an *illustrative future-state* example, not part of R6's guaranteed
delivery, to avoid the spec itself implying master-data filters ship in the same phase as Audit/Control's).

> **FINAL DECISION (user, 2026-08-13) — DECIDED as recommended**, with explicit added constraints: do not
> show a Filter button on master-data lists until corresponding backend query/filter semantics exist;
> future master-data filtering is added deliberately through desktop API/query contracts, not client-side
> filtering of fully materialized collections.

---

### D7 — `SectionNavigationRail` vs. the new shared `NavigationRail`

**1. Decision, restated:** Should the new shared `NavigationRail` (§16/§21, consolidating `ShellDrawer`/
`AdminNavSidebar`/`SettingsSidebarNav`) be built by extending the existing detail-page-internal
`SectionNavigationRail.qml`, or built as a wholly separate component, leaving `SectionNavigationRail`
untouched?

**2. Current behavior, file:line — resolved with more precision than R0 had it:**
`SectionNavigationRail.qml` **already implements** a grouping engine near-identical in shape to what
`AdminNavSidebar`/`SettingsSidebarNav` hand-roll: `property var sections: []`,
`property bool groupsCollapsedByDefault: true`, and a computed `_groups`/`_groupLabel` (lines 13-54)
that buckets flat section entries into labeled groups — this is the same underlying idea as
`AdminNavSidebar`'s 5 hardcoded groups (ORGANIZATION/WORKFORCE/CONTENT/ACCESS/SYSTEM). **What it does
not have**, confirmed by grep for `collapsed`/width-toggling logic: any collapse-to-icon-rail behavior —
it is fixed at `Theme.AppTheme.detailRailWidth` (220px) always, with no narrow/icon-only state, unlike
`ShellDrawer`/`AdminNavSidebar`/`SettingsSidebarNav`, which all toggle between an expanded and a
collapsed-icon width.

**3. Why it matters:** this determines whether R1's `NavigationRail` is "extend a proven, already-grouped
component with one new capability" or "build two components' worth of logic from scratch, duplicating the
grouping engine `SectionNavigationRail` already has right."

**4. Alternatives:**
- (a) Extend `SectionNavigationRail` with an optional collapse-to-icon-rail mode; use the extended component
  for both the new top-level `NavigationRail` and (optionally, since its existing detail-page callers don't
  need collapse) the existing detail-page rail use case.
- (b) Build `NavigationRail` as a new, separate component; leave `SectionNavigationRail` exactly as-is,
  accepting the resulting duplication of grouping logic between the two.

**5. Recommended: (a) Extend `SectionNavigationRail`.**

**6. Reasoning:**
- *Enterprise UX consistency:* one grouping/selection visual language across both top-level and
  detail-page navigation, rather than two components that happen to look similar but are independently
  maintained (exactly the "four separate implementations" problem this whole effort is trying to close,
  §23.11/§25 of the audit — building a *fifth*, even a well-intentioned one, would be self-defeating).
- *Usability:* unaffected directly, but consistency of behavior (e.g., keyboard navigation, if ever added)
  benefits from one implementation.
- *Information architecture:* unaffected.
- *Safety:* none.
- *Implementation complexity:* extending is smaller than building fresh — the grouping engine, the
  hardest and most bug-prone part of either component, already exists and is presumably already tested by
  virtue of being in production use in every detail page today. Adding collapse behavior is a bounded,
  well-understood addition (the exact same expand/collapse mechanic `ShellDrawer`/`AdminNavSidebar` already
  demonstrate, just not yet present in this file).
- *Reuse of existing capability:* this is the entire point of the recommendation — maximal reuse of
  already-working, already-in-production code.
- *Impact on future web/SaaS UI:* one navigation-rail component with one set of behaviors (grouping +
  optional collapse) is a cleaner thing to port or reference than two.

**7. Phases affected:** R1 (this is foundational — every later phase's navigation depends on which base
`NavigationRail` is built from), R7 (responsive collapse behavior, §19, is easier to define once/if
`SectionNavigationRail` already supports collapse, since detail-page rails may also want to collapse on
narrow windows — currently an open question in §19, now informed by this decision rather than separate
from it).

**8. Spec sections that change if approved:** §16 (`NavigationRail`'s entry updated to state it extends
`SectionNavigationRail`, not a from-scratch component), §21 (mapping table's `SectionNavigationRail` row
updated from "kept as-is, *or* re-based… decided during R1" to "extended with collapse support, shared
base confirmed"), §19 (note that detail-page rail collapse becomes a natural, not speculative, extension
once this is in place).

> **FINAL DECISION (user, 2026-08-13) — CHANGED from the recommendation above: do NOT turn
> `SectionNavigationRail` itself into the universal navigation base.** The user's instruction: "Do NOT turn
> SectionNavigationRail itself into the universal navigation base." The reasoning: `SectionNavigationRail`
> has a specific, named semantic responsibility — "navigate sections inside a detail record" — and
> stretching it to also serve as the app's top-level navigation conflates two different concerns under one
> component identity, even though they can share an underlying engine. The actual decision applied:
> - Extract a **new, lower-level primitive**, `GroupedNavigationRail` (§16), that owns the shared engine:
>   expand/collapse state, selection, grouped sections, badges/counts, keyboard/focus behavior, and the
>   canonical expanded/collapsed dimensions (sourced from `AppTheme`, not a hardcoded literal).
> - `SectionNavigationRail` is **re-implemented on top of** `GroupedNavigationRail` but **kept as a named
>   specialization** — its existing grouping engine (`_groups`/`_groupLabel`/`groupsCollapsedByDefault`)
>   is absorbed into the shared primitive rather than duplicated, but the component itself is not renamed,
>   removed, or promoted into a generic universal base.
> - A new component, `PlatformNavigation`, is the top-level rail composed from the same
>   `GroupedNavigationRail` primitive, replacing `AdminNavSidebar.qml` and `SettingsSidebarNav.qml` — a
>   sibling of `SectionNavigationRail` under the shared primitive, not a rename or extension of it.
> - The duplicated hardcoded `collapsed ? 48 : 220` literals in `AdminNavSidebar.qml:19` and
>   `SettingsSidebarNav.qml:17` are eliminated — canonical dimensions are sourced from `AppTheme`'s new
>   nav-rail tokens instead of being hand-written a third or fourth time.
> This is composition-over-universal-component: three names (`GroupedNavigationRail`,
> `SectionNavigationRail`, `PlatformNavigation`), one shared engine — not one component stretched to cover
> every navigation use case in the app.

---

### D8 — Minimum window width

**1. Decision, restated:** `App.qml` sets a fixed *initial* window size (1280×800) but no
`minimumWidth`/`minimumHeight` floor. What floor should the target design set?

**2. Current behavior, file:line:** `App.qml:14-15` — `width: 1280`, `height: 800`, no
`minimumWidth`/`minimumHeight` property anywhere in the file (confirmed absent by direct read, both in the
original audit and re-confirmed here). Audit §19 explicitly flagged this as **Unable to determine from
static analysis** what happens below some width — this closure pass does not claim to resolve that
uncertainty (it requires runtime verification, which is out of scope for a docs-only pass), but a
*recommended target number* can still be reasoned about from the same static evidence.

**3. Why it matters:** the target nav chrome is 469px (§0/§4) regardless of window size (fixed-width,
non-flexible, confirmed in §4/§19); below some width, either content becomes illegibly narrow or the fixed
rails would need to start overlapping/collapsing automatically (§19's proposed auto-collapse behavior, D7).
Without a floor, the OS-default resize behavior applies with no protection.

**4. Alternatives:**
- (a) No explicit minimum (status quo) — simplest, but leaves the uncertainty the audit already flagged
  unresolved.
- (b) A conservative floor sized to guarantee legible content even with both nav levels expanded (roughly
  469px chrome + a genuinely usable content minimum, e.g. ~555px for a 3-column list+inspector layout at
  reduced density) → **≈1024px**, a widely-recognized desktop-app minimum-width convention independent of
  this app's own specifics.
- (c) A narrower floor (e.g. 800px) that assumes `NavigationRail` auto-collapses below a breakpoint (§7,
  §19) before content becomes illegible, allowing a smaller absolute floor since chrome shrinks
  dynamically.

**5. Recommended: (b), 1024px, explicitly pending runtime confirmation in R8.**

**6. Reasoning:**
- *Enterprise UX consistency:* 1024px is a long-standing, widely-recognized minimum for desktop business
  applications (older but still-common convention), giving a defensible, unsurprising floor rather than an
  app-specific guess.
- *Usability:* guarantees the worst case (both nav levels expanded, no auto-collapse yet implemented) still
  leaves a legible content column, rather than depending on R7's auto-collapse behavior (D7) landing before
  a floor is set — (c) is more elegant *once* auto-collapse exists but is riskier to ship *before* it does.
- *Information architecture:* unaffected.
- *Safety:* none.
- *Implementation complexity:* trivial either way — a single property addition to `App.qml`. The
  complexity difference is entirely in *which number* to pick, not in adding the property.
- *Reuse of existing capability:* n/a.
- *Impact on future web/SaaS UI:* a fixed-pixel minimum-width concept is desktop-specific and does not
  port to a responsive web surface at all — this decision is explicitly scoped to the desktop app only, a
  reminder (not a new finding) that any future web UI needs its own, separately-designed responsive
  breakpoints rather than reusing this number.
- **Explicit caveat carried forward, not resolved by this pass:** the audit's own "Unable to determine from
  static analysis" flag on sub-minimum-width behavior stands — this recommendation picks a *reasonable
  starting number*, not a *verified-safe* one; R8's runtime verification (§23) is where this gets confirmed
  or adjusted, exactly as R0 already scoped it.

**7. Phases affected:** R7 (implementation), R8 (runtime verification/adjustment).

**8. Spec sections that change if approved:** §19 (states 1024px as the target, still flagged pending
runtime confirmation rather than final), §23's R8 entry (explicitly includes verifying this specific
number).

> **FINAL DECISION (user, 2026-08-13) — DECIDED as recommended, provisionally.** Adopt 1024px as the
> minimum target window width, treated as an R0 design constraint with mandatory runtime validation in R8.
> Layouts must still degrade intentionally around that minimum — not every three-pane layout is assumed to
> remain simultaneously visible at exactly 1024px (inspector may collapse/close, labels may reduce, table
> columns may adapt, navigation may collapse). If R8's runtime testing proves 1024px unusable for required
> workflows, the minimum is revised based on measured layout behavior, not this document's assumption.

---

## Final Decisions (approved 2026-08-13)

All 8 decisions below are **DECIDED** — this replaces the earlier "pending approval" framing. Where the
final decision differs from this pass's original recommendation, that is called out explicitly (see each
item's FINAL DECISION callout above for full reasoning).

**D1 — Inspector Delete button** — **DECIDED as recommended.** Remove the button until a real delete
capability exists; no delete backend added as part of this redesign.

**D2 — Control Escalations/System Events tabs** — **DECIDED as recommended.** Remove both tabs entirely;
may return later once real backend/product semantics exist.

**D3 — Control Audit tab vs. Admin Audit leaf** — **DECIDED as recommended.** Merge into one
`Control → Governance → Audit` destination (confirmed same underlying data source); read-contract
normalization only, service layers not merged.

**D4 — Settings Platform Defaults / Security sections** — **CHANGED.** Delete both sections, per-value —
not a wholesale relabel-and-keep. No genuine global-default backend exists for either section's content;
Settings' target IA shrinks to Modules/Integrations/Runtime/Diagnostics.

**D5 — Toggle-active confirmation UX** — **CHANGED.** Asymmetric: activate = direct + toast; deactivate =
blocking confirmation naming entity + consequence. Genuinely-destructive actions keep blocking confirmation
regardless of direction. No universal toast-with-undo.

**D6 — Filter scope** — **DECIDED as recommended.** Real filters for Audit/Control first (backend already
supports it); master-data lists stay search-only until a backend filter capability exists for them.

**D7 — `SectionNavigationRail` vs. shared navigation** — **CHANGED.** Do not turn `SectionNavigationRail`
into the universal navigation base. Extract a new `GroupedNavigationRail` primitive; `SectionNavigationRail`
stays a named specialization built on it; new `PlatformNavigation` is the top-level rail, also built on it.

**D8 — Minimum window width** — **DECIDED as recommended, provisionally.** 1024px, explicitly pending
runtime confirmation during R8, with mandatory graceful degradation.

---

## 27. Summary of What Must Not Change (carried forward from the audit's Technical Constraints, §26 of the
audit)

- QML import-path/`qmldir` module-registration model.
- `@QmlUncreatable` controller injection via `PlatformWorkspaceCatalog`/`context.py`.
- `DynamicTableModel` binding contract for any list wanting Python-side data.
- The global `domain_events` bus auto-refresh mechanism.
- The `run_mutation`/`serialize_operation_result` `{ok, category, code, message}` contract.

None of R1–R8 requires touching any of the above. If a specific R-phase implementation discovers it
*does* need to, that is a signal to stop and re-scope, not to proceed silently — consistent with Design
Principle 5.

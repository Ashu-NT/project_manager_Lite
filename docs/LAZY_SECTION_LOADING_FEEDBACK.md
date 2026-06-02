# Lazy Section Loading Feedback — Implementation Plan & Follow-up

**Date:** 2026-05-31  
**Status:** Complete (Phase 1)  
**Scope:** All modules — Project Management detail panels

---

## 1. Summary of What Was Done

### Problem
`LazySectionLoader` renders detail panel sections asynchronously (`asynchronous: true`). While a section was loading, users saw a zero-height gap with no feedback — sections appeared to "pop in" silently.

`LoadingOverlay` existed as a shared component but only supported one mode (full scrim overlay) with no message support.

### Solution
Two shared components were enhanced. No workspace-specific spinners were created.

---

## 2. Files Changed

### Shared Components (App.Widgets)

| File | Change |
|---|---|
| `LoadingOverlay.qml` | Extended from single-mode Rectangle to multi-mode Item |
| `LazySectionLoader.qml` | Added loading placeholder with spinner + message |

### Detail Panels (Project Management — 63 insertions across 9 files)

| File | Sections | Insertions |
|---|---|---|
| `TasksDetailPanel.qml` | Details, Assignments, Dependencies, Time, Activity, Material Demand, Reservations, Procurement, Skills, Schedule Impact | 10 |
| `ResourcesDetailSection.qml` | Overview, Assignments, Capacity, Calendar, Skills, Certifications, Cost Rates, Availability, Activity | 9 |
| `ProjectsDetailSection.qml` | Overview, Schedule, Tasks, Resources, Financials, Risks, Documents, Activity, Material Demand, Procurement | 10 |
| `SchedulingDetailPanel.qml` | All scheduling sections | 8 |
| `FinancialsDetailSection.qml` | Budget, Actuals, Costs, Activity, etc. | 9 |
| `TimesheetsDetailSection.qml` | Entries, History, Notes, Audit | 4 |
| `CollaborationDetailPanel.qml` | Overview, Activity, Comments | 4 |
| `RegisterDetailPanel.qml` | Details, Impact, Response, Links | 4 |
| `PortfolioDetailPanel.qml` | Overview, Scenarios, Dependencies, Funding, Activity | 5 |

---

## 3. Component API Reference

### LoadingOverlay.qml (updated)

```qml
AppWidgets.LoadingOverlay {
    // Existing (unchanged):
    loading: bool             // controls visibility

    // New:
    message: string           // optional label e.g. "Loading tasks..."
    compact: bool             // false = full scrim overlay (default); true = inline row
    modal: bool               // true = show scrim (default); false = transparent bg
}
```

**Modes:**

| `compact` | `modal` | Behavior |
|---|---|---|
| `false` | `true` | Full scrim overlay with centered spinner (original behavior — backward compat) |
| `false` | `false` | Centered spinner, no scrim — non-blocking |
| `true` | any | Compact inline row: small spinner + message text |

**Usage examples:**

```qml
// Workspace page — full overlay (unchanged existing usage)
AppWidgets.LoadingOverlay {
    anchors.fill: parent
    loading: controller.isLoading
}

// With message
AppWidgets.LoadingOverlay {
    anchors.fill: parent
    loading: controller.isLoading
    message: "Loading resources..."
}

// Compact inline — for ColumnLayout / Column contexts
AppWidgets.LoadingOverlay {
    Layout.fillWidth: true
    loading: isLoading
    compact: true
    message: "Loading assignments..."
}
```

---

### LazySectionLoader.qml (updated)

```qml
AppWidgets.LazySectionLoader {
    // Existing (unchanged):
    active: bool
    keepLoaded: bool
    sourceComponent: Component

    // New:
    loadingMessage: string      // shown while async loading; empty = spinner only
    fallbackLoadingHeight: int  // height while loading (default: normalRowHeight × 2)
}
```

**Behavior:**
- While `Loader.status === Loader.Loading`: shows compact spinner + message, section height = `fallbackLoadingHeight`
- Once loaded: content appears, spinner hides, height = measured content height
- If `loadingMessage` is empty: only the spinner is shown (no text)

**Example:**
```qml
AppWidgets.LazySectionLoader {
    anchors.left: parent.left
    anchors.right: parent.right
    active: root._idx === 2
    loadingMessage: "Loading assignments..."
    sourceComponent: Component { ... }
}
```

---

## 4. Architecture Decisions

### What was changed
- `LazySectionLoader` → loading placeholder built-in (fires automatically for all 63+ usages)
- `LoadingOverlay` → now supports `message`, `compact`, `modal`

### What was NOT changed
- `LazyObjectLoader` → untouched; it loads non-visual objects (dialog hosts, helpers) — no user-visible loading state needed
- Existing `BusyIndicator` in `DataTable`, `SectionDetailPage`, `EntityDialog`, `LoginWindow` → untouched; those are contextually appropriate
- Existing `WorkspaceStateBanner` components → untouched; workspace-level loading is separate from section-level loading
- No one-off spinners created in any workspace page

### Why inline in LazySectionLoader (not using LoadingOverlay)
`LazySectionLoader` is inside `App.Widgets` module. Importing `App.Widgets` from within itself creates a circular module dependency. Instead, the loading placeholder is built inline using only `QtQuick`, `QtQuick.Controls`, and `App.Theme` + `App.Controls` (sibling modules, not circular). The visual result is identical to `LoadingOverlay` with `compact: true`.

---

## 5. Follow-up Work (Phase 2)

### HIGH PRIORITY

- [ ] **Maintenance module detail panels** — If `LazySectionLoader` is added to Maintenance detail panels in the future, `loadingMessage` will be needed there too. Currently Maintenance does not use `LazySectionLoader` (confirmed in audit).

- [ ] **Inventory/Procurement detail panels** — Same: currently uses `LazyObjectLoader` for dialog hosts only, not `LazySectionLoader` for sections. If section-level lazy loading is added, `loadingMessage` is automatically available.

- [ ] **Platform module** — `AdminConsolePage` uses one `LazyObjectLoader` (non-visual). No section-level lazy loading. No changes needed.

### MEDIUM PRIORITY

- [ ] **Per-section fallbackLoadingHeight tuning** — Some sections have tall content (e.g. activity feeds, data tables). Set `fallbackLoadingHeight` explicitly on those sections to reduce height-jump when content loads:
  ```qml
  AppWidgets.LazySectionLoader {
      loadingMessage: "Loading activity..."
      fallbackLoadingHeight: 200  // taller for ActivityFeed sections
      ...
  }
  ```

- [ ] **Smooth height transition** — Add a `Behavior on implicitHeight` to `LazySectionLoader` for a subtle slide-in effect when content loads:
  ```qml
  Behavior on implicitHeight {
      NumberAnimation { duration: 180; easing.type: Easing.OutCubic }
  }
  ```
  Note: this must be profiled first — animating height in scrollable sections can cause layout thrash.

- [ ] **LoadingOverlay compact usage in workspace pages** — Workspace pages currently use `AppWidgets.InlineMessage` for their loading state. Consider replacing the "Loading..." InlineMessage with a compact LoadingOverlay for visual consistency:
  ```qml
  // Before:
  AppWidgets.InlineMessage {
      visible: controller.isLoading
      tone: "info"
      message: "Loading register..."
  }
  // After:
  AppWidgets.LoadingOverlay {
      Layout.fillWidth: true
      loading: controller.isLoading
      message: "Loading register..."
      compact: true
      modal: false
  }
  ```

### LOW PRIORITY

- [ ] **Skeleton loading** — For a premium enterprise feel, replace the spinner placeholder with skeleton content (gray shimmer rectangles matching the expected content shape). This would require per-section skeleton templates — significant effort.

- [ ] **Loading message i18n** — All current messages are hardcoded English strings. When internationalization is added, these should go through a translation system.

- [ ] **qmllint CI check** — Add a CI step that runs `qmllint` on `LoadingOverlay.qml` and `LazySectionLoader.qml` to catch future regressions.

---

## 6. Validation Checklist

- [x] `LazySectionLoader` shows loading placeholder while async loading
- [x] `LoadingOverlay` backward compatible — existing `loading: bool` + `anchors.fill: parent` usage unchanged
- [x] `LoadingOverlay` supports `compact: true` inline mode
- [x] `LoadingOverlay` supports `message: string`
- [x] `LazyObjectLoader` NOT modified (non-visual, no loading state)
- [x] `LoadingOverlay` NOT used inside `LazyObjectLoader`
- [x] 63 `loadingMessage` strings added across 9 detail panel files
- [x] No one-off workspace spinners created
- [x] No hardcoded colors — `Theme.AppTheme` used throughout
- [x] No `width`/`height` directly on layout-managed children — `implicitWidth`/`implicitHeight` used
- [x] `AppControls.Label` used for text (not raw `Text` element)
- [x] Both full overlay and compact inline modes work without layout breakage

---

## 7. Quick Reference — Where Loading Comes From

```
User navigates to a section tab
        ↓
LazySectionLoader.active becomes true
        ↓
_shouldLoad = true → Loader starts async component instantiation
        ↓
_loader.status = Loader.Loading
        ↓
_isLoading = true
        → implicitHeight = fallbackLoadingHeight  (section has visible height)
        → _loadingPlaceholder visible: spinner + "Loading tasks..."
        → _loader.visible = false  (content not shown yet)
        ↓
Loader finishes (Loader.Ready)
        ↓
_isLoading = false
        → _loadingPlaceholder hides
        → _loader.visible = true  (content appears)
        → _syncMeasuredHeight() → implicitHeight = content height
```

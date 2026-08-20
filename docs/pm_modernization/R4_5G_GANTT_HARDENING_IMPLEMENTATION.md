# R4.5G Gantt Hardening Implementation

**Status:** Complete

**Scope:** Responsive behavior, durable UI preferences, essential keyboard
navigation, and measured large-project hardening. No scheduling semantics, PM
business command, R5 capability, or broad R8 accessibility work was added.

## 1. Responsive Contract

The Gantt resolves layout from the width actually allocated to
`SchedulingGanttSurface`, after shell and Inspector space have been consumed.
The user-requested mode remains separate from the temporary effective mode.

| Panel viewport | Inspector | Secondary controls | Effective requested Split |
|---|---|---|---|
| 1024 x 640 | Slide-over | Overflow | Grid fallback; Grid and Timeline remain selectable |
| 1280 x 720 | Slide-over | Overflow | Split |
| 1366 x 768 | Inline | Direct | Split when the resulting surface remains wider than 1024 |
| 1440 x 900 | Inline | Direct | Split |
| 1920 x 1080 | Inline | Direct | Split |

Final geometry rules:

- minimum grid width: 420 px;
- minimum timeline width: 360 px;
- splitter width: 6 px;
- structural split minimum: 786 px;
- compact surface rule: width at or below the established 1024 px compact
  breakpoint does not force Split;
- inline Inspector rule: panel width must preserve 1024 px for the Gantt after
  `inspectorWidth + spacingSm` is removed;
- secondary toolbar controls are direct at 1360 px and wider and use overflow
  below that threshold;
- pane widths are never persisted or corrected during window resize.

Requested Split is not overwritten when effective mode falls back to Grid.
When sufficient width returns, Split returns automatically. The persisted split
ratio is clamped to 0.44 through 0.62. Runtime geometry additionally clamps it
against the actual 420/360 pane minimums. Only a completed splitter drag emits a
persistence request; resize frames do not write settings.

## 2. Toolbar and Inspector

Search, filters, Critical only, Today, and view mode remain directly reachable.
At constrained widths, the established `AppWidgets.AnchoredPopup` exposes:

- Highlight Critical Tasks;
- Dependency Lines;
- selected baseline;
- Day/Week/Month/Quarter timescale;
- zoom out, reset, and zoom in.

Direct and overflow copies are mutually exclusive at a given width. Both copies
bind to the same controller/axis state and preserve enabled state. The Inspector
keeps its existing content and uses one inline instance or one slide-over
instance, never both. Opening, closing, or resizing the Inspector does not alter
selection, requested mode, baseline, dependency preference, critical highlight,
timescale, zoom, hierarchy state, or timeline center.

## 3. Preference Contract

Generic Gantt preferences remain local UI state in `AppSettingsStore`; no Task,
Project, Dependency, Baseline, or scheduling table is written. The organization-
scoped QSettings key is:

`tenant/{organization_id}/ui/project_management/gantt/view_state`

Schema version 1 stores:

```json
{
  "version": 1,
  "requestedViewMode": "split",
  "splitRatio": 0.5,
  "timescale": "week",
  "zoomMultiplier": 1.0,
  "dependencyLinesEnabled": true,
  "highlightCriticalTasks": true
}
```

Validation is deny-safe:

- unknown mode becomes `split`;
- non-numeric/non-finite ratio becomes `0.5`, and finite values clamp to
  `0.44..0.62`;
- unsupported timescale becomes `week`;
- zoom accepts only `0.75`, `0.875`, `1.0`, `1.25`, or `1.5`; otherwise it
  becomes `1.0`;
- malformed booleans use `true` defaults;
- malformed/non-object JSON uses the complete defaults.

Preferences follow the existing organization-scoped desktop setting rule.
There is no separate established user settings scope in this application, so G
does not invent one. Column visibility/order/width remains under the existing
table-column setting contract and is not mixed into Gantt state.

Selected baseline uses a separate organization- and project-scoped map:

`tenant/{organization_id}/ui/project_management/gantt/project_baselines`

The controller restores a baseline only after the current authorized project
options are available. Missing, deleted, unauthorized, or another project's ID
resolves to None and is removed from that project's local preference. Baseline
selection remains an ID preference only; baseline snapshots and baseline truth
remain authoritative backend data.

The implementation deliberately does not persist selected task, focus, hover,
Inspector state, hierarchy expansion, errors/loading, vertical or horizontal
scroll, route cache, Canvas state, or visible row window.

## 4. Keyboard Essentials

The one vertical `ListView` remains the keyboard authority:

- Up/Down selects the previous/next effective visible row;
- Home/End selects and positions the first/last effective row;
- Enter/Return emits the existing Open Task activation;
- Right expands a collapsed summary;
- Left collapses an expanded summary, then moves a child selection to its
  visible parent on a subsequent press.

Navigation uses O(1) model index/ID/parent/summary lookups and
`ListView.positionViewAtIndex`. It does not locate offscreen delegates, query the
database, run CPM, or maintain a second grid/timeline current index. Existing
filter behavior continues to clear a selection that is no longer visible.

## 5. Measurements

Measurements were captured on Windows in the `pmenv` environment with the Qt
offscreen runtime. They are regression characterizations, not claims about every
production GPU or a replacement for final integrated profiling.

### Core viewport

| Rows | Model attach | First viewport | Delegates | Selection | Scroll | Local filter | Mode switch |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 100 | 2.375 ms | 23.475 ms | 20 | 0.033 ms | 5.810 ms | 2.277 ms | 0.130 ms |
| 1,000 | 22.013 ms | 24.438 ms | 20 | 0.037 ms | 5.629 ms | 3.268 ms | 0.130 ms |
| 5,000 | 109.137 ms | 21.758 ms | 20 | 0.038 ms | 5.275 ms | 9.350 ms | 0.074 ms |

### Combined Month/zoom/baseline/dependency scenario

| Rows | Projection | Model | First viewport | Delegates | Scroll | Zoom | Visible edge candidates |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 100 | 4.940 ms | 0.201 ms | 104.298 ms | 32 | 13.664 ms | 5.298 ms | 35 |
| 1,000 | 36.803 ms | 1.706 ms | 113.126 ms | 32 | 15.139 ms | 4.896 ms | 36 |
| 5,000 | 268.657 ms | 11.269 ms | 107.665 ms | 32 | 10.280 ms | 5.050 ms | 36 |

The 5,000-row combined case includes Month scale, zoom 0.875, baseline active,
dependency lines active, critical highlighting, nested rows, selection,
vertical scroll, horizontal scroll, and zoom. Active delegates remain 32 rather
than approaching 5,000.

Python-visible projection/model allocation was approximately:

| Rows | Current | Peak |
|---:|---:|---:|
| 100 | 0.163 MiB | 0.419 MiB |
| 1,000 | 1.488 MiB | 4.084 MiB |
| 5,000 | 7.082 MiB | 20.357 MiB |

Baseline merge remains one bulk snapshot read plus indexed merge. At 5,000 rows,
the measured overlay build/index/visible lookup was 19.581/1.296/0.044 ms.

Visible dependency lookup remains bounded by the row window: 29 edges at 100,
1,000, and 5,000 rows in approximately 0.10-0.12 ms. The raw characterization
for 5,000 visible routes is 147 ms and is not used unchecked in the interactive
high-density path. At 9,800 project edges, measured density protection retained
392 selected-task routes and completed routing/paint in 24/1 ms with a truthful
suppression message. Continuous 120-frame scroll repaint characterization was
1.874 ms in the offscreen harness without rebuilding routes.

Project-switch stress replaces the 5,000-row projection, baseline index,
dependency indexes, and axis with a 100-row project; old task IDs are absent and
active delegates remain bounded.

## 6. DPI and Rendering Safety

The R4.5E Canvas coordinate fix remains authoritative. Runtime probes pass at
DPR 1.0, 1.25, 1.5, and 2.0 for connector endpoints, row centers, scroll, and
painted output. Bars, milestone diamonds, baseline shapes, header, and dependency
Canvas share logical QML coordinates; no component manually applies DPR.

No permanent QML object was added per task, baseline snapshot, timeline day, or
dependency edge. The architecture remains one recycled row viewport, one
horizontal authority, and one bounded Canvas.

## 7. Targeted Corrections

Only measured or contract-proven changes were made:

- model O(1) hierarchy lookup slots support keyboard navigation without delegate
  searches;
- axis configuration can be restored atomically before projection/rendering;
- preference setters compare before/after axis state, preventing duplicate
  writes for accepted but unchanged timescale/zoom requests;
- splitter persistence occurs only on drag completion;
- responsive fallback is derived and never persisted;
- stale project baseline IDs are rejected after authoritative option loading.

No cache, alternate row model, business write, CPM path, or DB query was added.

## 8. R4.5H Handoff

R4.5H owns only final integrated validation and cleanup:

1. run the full relevant PM scheduling/domain/shared-QML regression matrix;
2. repeat changed-QML lint and runtime import/qmldir guardrails;
3. verify no dead renderer, compatibility shim, stale import, or obsolete test
   contract remains;
4. reconcile all R4.5A-G closure documents and the final R4.5 exit gate.

No known R4.5G correctness defect is deferred to H. R5 resource/workload
features and broad R8 accessibility remain untouched. Nothing was committed by
this implementation run.

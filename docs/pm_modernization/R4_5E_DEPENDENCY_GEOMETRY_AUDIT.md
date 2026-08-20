# R4.5E Dependency Geometry Audit

## Status and Scope

**Status: FIX IMPLEMENTED / VERIFIED**

The first revision of this document was the requested read-only coordinate
audit. The approved follow-up has now implemented the narrowly scoped Canvas
coordinate correction. No dependency semantics, task dates, CPM behavior,
persistence, scheduling engine, Gantt read model, or resource-leveling code was
changed.

## Implementation Closure

The dependency Canvas now uses logical QML dimensions and logical drawing
coordinates. The manual DPR-sized `canvasSize` and `context.scale(DPR, DPR)`
were removed together, leaving Qt Quick as the single logical-to-physical pixel
mapping authority.

Routes remain cached in content space. Horizontal paint still applies
`xContent - timelineContentX`. Vertical paint now applies
`yContent - rowScrollOffset`, where `rowScrollOffset = contentY - originY`.
Horizontal and vertical scroll changes call `requestPaint()` directly; route
rebuild coalescing remains unchanged for model, visible-window, row-height,
axis, zoom, selection, and dependency-state changes.

Painted-output verification uses the approved deterministic geometry:

```text
range start       = 2026-08-01
pixelsPerDay      = 12
FS content        = 144 -> 168
contentX = 100    = 44 -> 68
contentX = 250    = -106 -> -82, naturally clipped
row centers       = 18 -> 54
vertical offset 12 = 6 -> 42
```

The rendered output passes at DPR `1`, `1.25`, `1.5`, and `2`. All five zoom
multipliers and Day/Week/Month/Quarter densities retain shared bar/dependency
anchor math. First, middle, and last effective-row endpoint pixels align with
`(index + 0.5) * rowHeight`, including effective-order rather than construction-
order indexing.

Focused R4.5E result: **33 passed**. Combined targeted R4.5B/C/D/E/F and
Planning IA result: **100 passed**. Direct QML lint with application import roots
is silent, and Python compilation passes. A 120-frame horizontal/vertical
scroll characterization completed in approximately `2.1 ms` of dispatch work
without rebuilding the route cache. No full repository suite was run.

## 1. Observed Defects

The reported defects are reproducible as a display-coordinate problem on a
scaled display:

1. connectors do not track horizontally with task bars reliably;
2. connector endpoints and middle-to-middle Y distance diverge from row/bar
   centers;
3. the defect is absent at device pixel ratio (DPR) 1 in an offscreen pixel
   probe and appears at DPR 2;
4. continuous scroll painting is additionally timer-coalesced, so the old Canvas
   bitmap can remain visible until the queued paint executes.

No evidence indicates an FS/SS/FF/SF, lag, schedule, task-date, or effective-row
mapping defect.

## 2. Current QML Coordinate Hierarchy

```text
SchedulingGanttSurface (surface coordinates)
|-- SchedulingGanttHeader
|     x = 0, y = 0, height = 2 * 28 = 56
|-- SchedulingGanttRowsViewport
|     y = ganttHeader.bottom
|     `-- ListView (row viewport / vertical authority)
|           contentY = vertical scroll offset
|           `-- SchedulingGanttRow delegates (row content)
|                 `-- timelineLane x = surface.timelineX
|                       `-- SchedulingGanttBar
|-- SchedulingGanttDependencyLayer
|     x = surface.timelineX
|     y = ganttHeader.height
|     width = visible timeline width
|     height = row viewport height
|     `-- Canvas anchors.fill: parent
`-- timelineAxis Flickable
      x = surface.timelineX
      y = ganttHeader.height
      contentX = horizontal scroll authority
      contains no task rows or dependency Canvas
```

The dependency layer is a sibling of the row viewport and timeline Flickable.
It is fixed over the visible timeline viewport; it is not inside timeline
content.

## 3. Timeline Content Coordinates

The full calendar content uses logical QML pixels. For day ordinal `d`:

```text
dayStartX(d) = (d - axisStartDay) * pixelsPerDay
dayCenterX(d) = dayStartX(d) + pixelsPerDay / 2
```

For a normal task:

```text
inclusiveWidth = (finishDay - startDay + 1) * pixelsPerDay
taskWidth       = max(12, inclusiveWidth)
taskStartX      = dayStartX(startDay)
taskFinishX     = taskStartX + taskWidth
```

These are content-space coordinates and do not contain `timelineContentX`.

## 4. Timeline Viewport Coordinates

Because the bar lane and dependency Canvas are viewport-fixed, visible X must
be:

```text
xViewport = xContent - timelineContentX
```

`SchedulingGanttBar.qml` performs this directly in its `x` binding. The Canvas
paint loop also subtracts `timelineContentX` from every cached route X.

## 5. Row Content Coordinates

Rows use one fixed theme-derived height and `ListView.spacing: 0`:

```text
rowPitch = rowHeight
yContent(i) = i * rowHeight + rowHeight / 2
```

Production `rowHeight` is bound from
`Theme.AppTheme.compactRowHeight`: compact `30`, comfortable `34`, spacious
`36`. The dependency component's standalone fallback is `36`, but production
overrides it with the exact row viewport value.

## 6. Row Viewport Coordinates

The correct visible row center is:

```text
yViewport(i) = (i + 0.5) * rowHeight - verticalContentY
```

No spacing term applies. For unusual `ListView.originY` states, the generalized
scroll offset should be `contentY - originY`; current normal model/reset behavior
uses origin zero, but a future fix test should explicitly verify this.

## 7. Canvas Coordinate Space

The Canvas item is fixed to the dependency viewport. `_routes` stores timeline
and row **content coordinates**. `onPaint` converts them to viewport coordinates
by subtracting horizontal and vertical scroll offsets.

This architecture is valid and is the preferred model. The defect occurs after
that correct transform, in Canvas device-pixel handling.

## 8. Current Bar X Formula

Normal task:

```text
bar.x = dayStartX(startDay) - timelineContentX
bar.width = max(12, inclusiveWidth(startDay, finishDay))
```

Milestone, based only on explicit `isMilestone`:

```text
milestoneCenterContentX = dayCenterX(startDay)
milestone.x = milestoneCenterContentX - 14 / 2 - timelineContentX
milestone.width = 14
```

The visible diamond itself is 12 pixels inside the 14-pixel anchor item.

## 9. Current Bar Y Formula

Each row delegate has `height = rowHeight`. The current bar item has height 18
and is vertically centered in the row. Its normal shape is 14 high and its
milestone shape is 12 high, both centered in that item. Therefore:

```text
barCenterContentY(i) = (i + 0.5) * rowHeight
barCenterViewportY(i) = barCenterContentY(i) - verticalContentY
```

The abstract row center and visible current bar/milestone center are identical.

## 10. Current Dependency Anchor Formula

`_buildRoute()` uses the same `GanttGeometry.js` functions as task bars:

```text
sourceX = start or finish content anchor selected by relation
targetX = start or finish content anchor selected by relation
sourceY = (predecessorEffectiveIndex + 0.5) * rowHeight
targetY = (successorEffectiveIndex + 0.5) * rowHeight
```

The cache then stores `sourceX`, `sourceOuterX`, `channelX`, `targetOuterX`,
`targetX`, `sourceY`, and `targetY` in content coordinates.

## 11. FS Anchor Math

```text
sourceContentX = predecessor.taskFinishX
targetContentX = successor.taskStartX
```

## 12. SS Anchor Math

```text
sourceContentX = predecessor.taskStartX
targetContentX = successor.taskStartX
```

## 13. FF Anchor Math

```text
sourceContentX = predecessor.taskFinishX
targetContentX = successor.taskFinishX
```

## 14. SF Anchor Math

```text
sourceContentX = predecessor.taskStartX
targetContentX = successor.taskFinishX
```

For an explicit milestone, start and finish choose the left/right sides of the
same 14-pixel milestone anchor around the authoritative day center. No date or
duration heuristic determines milestone identity.

## 15. Horizontal Scroll Transform

The logical transform in `onPaint` is correct:

```text
sourceViewportX = route.sourceX - timelineContentX
targetViewportX = route.targetX - timelineContentX
```

The later `context.scale(DPR, DPR)` incorrectly scales those already-logical
coordinates a second time relative to task bars.

## 16. Vertical Scroll Transform

The logical transform is also correct:

```text
sourceViewportY = route.sourceY - verticalContentY
targetViewportY = route.targetY - verticalContentY
```

Again, the Canvas context's manual DPR scaling enlarges the transformed values
while normal QML row/bar geometry is scene-scaled only once.

## 17. Row Middle-to-Middle Formula

For source row `i`, target row `j`, and row height `H`:

```text
deltaY = (j - i) * H
absoluteDeltaY = abs(j - i) * H
```

At `H = 36`, rows 2 to 3 are 36 pixels apart and rows 2 to 7 are 180 pixels
apart. At the production compact default `H = 30`, the corresponding distances
are 30 and 150 pixels.

## 18. Header and Row Offset Analysis

The header is 56 logical pixels high. Both `SchedulingGanttRowsViewport` and
`SchedulingGanttDependencyLayer` begin at `ganttHeader.bottom`. Consequently the
Canvas's local `y = 0` is the first row's top. Adding 56 inside route math would
be a bug; the current code correctly does not add it.

Both components also subtract the same bottom margin. No missing or duplicate
header offset and no row-spacing mismatch exists.

## 19. Route Cache Coordinate Space

The route cache is content-space, not viewport-space. This is confirmed by the
existing tests: changing `timelineContentX` or `verticalContentY` intentionally
does not change `visibleRoutes`. Zoom, axis start, row height, effective window,
selection, and model changes rebuild content-space routes.

Keeping content-space routes is recommended. Scroll should alter only the paint
transform.

## 20. Repaint and Invalidation Analysis

Current handlers are:

```text
timelineContentX changed -> _schedulePaint()
verticalContentY changed -> _schedulePaint()
pixelsPerDay changed      -> _scheduleRebuild()
row/window/model changed  -> _scheduleRebuild()
```

The logical invalidation distinction is correct: scrolling needs repaint only;
zoom and row/model changes need route rebuild. However `_schedulePaint()` restarts
a shared zero-delay Timer. During continuous input this is asynchronous and can
coalesce/restart repeatedly while bars move immediately, allowing visible lag or
an apparently fixed old bitmap. Existing tests verify only that the content-space
cache stays unchanged; they do not verify painted pixels move.

The high-DPI error is independent and definitive: `canvasSize` is manually set
to `width * DPR`/`height * DPR`, and `onPaint` also executes
`context.scale(DPR, DPR)`. Qt Quick already maps logical item coordinates to the
window's device pixels. The context scale therefore applies DPR twice relative
to ordinary QML bars.

## 21. Numeric Reproduction of Horizontal Bug

Let range start be August 1 and `pixelsPerDay = 12`:

```text
predecessor Aug 10..12: start = 9*12 = 108, width = 3*12 = 36, finish = 144
successor   Aug 15..18: start = 14*12 = 168, width = 4*12 = 48, finish = 216
```

Correct content anchors:

| Relation | Source | Target |
|---|---:|---:|
| FS | 144 | 168 |
| SS | 108 | 168 |
| FF | 144 | 216 |
| SF | 108 | 216 |

Correct viewport anchors:

| Scroll X | FS | SS | FF | SF |
|---:|---|---|---|---|
| 0 | 144 -> 168 | 108 -> 168 | 144 -> 216 | 108 -> 216 |
| 100 | 44 -> 68 | 8 -> 68 | 44 -> 116 | 8 -> 116 |
| 250 | -106 -> -82 | -142 -> -82 | -106 -> -34 | -142 -> -34 |

At DPR 2, bars retain those logical coordinates and Qt maps them once to device
pixels. The Canvas additionally scales its context by 2. For FS at scroll 100,
the connector is drawn at logical `88 -> 136` rather than `44 -> 68`, before the
scene's normal device mapping. It therefore drifts from the bars and can be
clipped so severely that the old/remaining segment appears fixed.

## 22. Numeric Reproduction of Vertical Bug

With `H = 36`, rows 0 and 1 have logical centers 18 and 54. Correct DPR-2 device
centers are approximately 36 and 108 physical pixels after Qt Quick's one scene
mapping. The Canvas's extra context scale makes its effective logical centers 36
and 108 before scene mapping, yielding approximately 72 and 216 physical pixels.

The offscreen probe measured:

```text
DPR 1 route cache: sourceY=18, targetY=54
DPR 1 painted bounds: y=17..57
after contentY=12: y=5..45 (exact -12 shift)

DPR 2 same route cache: sourceY=18, targetY=54
DPR 2 painted bounds: y=68..231
expected approximately: y=36..108 physical
```

This proves the row-index and logical Y formulas are correct and the divergence
is introduced by Canvas device scaling.

## 23. Zoom Verification

Changing zoom changes `pixelsPerDay`. Both bars and dependency anchors call the
same `GanttGeometry.js` functions, and `onPixelsPerDayChanged` rebuilds routes.
No dependency-specific zoom math exists. The DPR defect multiplies the otherwise
correct result at every zoom level. The approved fix must preserve this route
rebuild and verify every discrete multiplier (`0.75`, `0.875`, `1.0`, `1.25`,
`1.5`): connector start/finish anchors must move by the same scale ratio as the
corresponding task or milestone anchors.

## 24. Timescale Verification

Day, Week, Month, and Quarter all expose a different authoritative
`pixelsPerDay`; relation semantics and anchor-side selection remain unchanged.
The shared formulas are valid for all four scales. The defect is Canvas device
scaling, not timescale logic. At neutral zoom the current base densities are:

```text
Day     = 40 logical pixels/day
Week    = 12 logical pixels/day
Month   = 4 logical pixels/day
Quarter = 1.5 logical pixels/day
```

For each scale, bars and dependency anchors must independently derive from that
same density. A scale change must rebuild content-space routes; it must not merely
stretch a stale Canvas image. Horizontal scrolling after the rebuild must still
apply exactly `-timelineContentX` in logical pixels.

## 25. Hierarchy Verification

`GanttListModel.dependencyWindow()` builds `taskId -> index` from the current
`_effective_rows` slice. Expansion/collapse changes effective rows and model/window
signals rebuild routes. If either endpoint is hidden or outside the bounded
render window, the complete edge is not returned. No database or stale WBS index
is used.

## 26. Flat-Sort Verification

Flat sorting rebuilds `_effective_rows` and its task-ID index. Dependency task
dates and X anchors stay unchanged; predecessor/successor row indices are emitted
from the new effective order. Existing tests verify the endpoints change Y order
without changing dependency identity or semantics.

## 27. Root Cause - Horizontal

Primary root cause: **DPR is manually applied in the Canvas context in addition
to Qt Quick's normal logical-to-device mapping**. This puts connector paint in a
different effective scale from bars and makes clipping/position drift severe on
scaled Windows displays.

Secondary presentation risk: scroll changes use a restartable zero-delay Timer,
so Canvas repaint can lag continuous bar movement. There is no missing
`timelineContentX` subtraction and no need to rebuild the content-space cache on
scroll.

## 28. Root Cause - Vertical

Primary root cause: the same duplicate DPR application scales route Y centers and
their distance while rows/bars are scene-scaled only once. Effective row index,
row height binding, row spacing, header origin, and bar center are correct in the
current production hierarchy.

For robustness, a fix test should also use `contentY - originY` as the generalized
ListView scroll offset, although `originY` is currently zero and did not cause the
observed defect.

## 29. Recommended Mathematical Contract

Retain content-space route caching:

```text
startContentX  = Geometry.dayStartX(...)
finishContentX = Geometry.taskFinishX(...) or milestone side
yContent(i)    = (i + 0.5) * rowHeight

xPaint = xContent - timelineContentX
yPaint = yContent - rowScrollOffset
```

Use logical QML coordinates throughout Canvas drawing. Let Qt Quick perform the
single device-pixel conversion. Relation type selects only start/finish anchor
sides. Lag remains metadata and is not added to endpoint X.

## 30. Implemented Minimum Fix

The renderer and route cache were not rewritten.

1. `SchedulingGanttDependencyLayer.qml` had `context.scale(DPR, DPR)` and the
   manual DPR-sized `canvasSize` removed together, allowing Qt Quick to own
   device mapping.
2. Horizontal and vertical scroll now call `dependencyCanvas.requestPaint()`
   directly while rebuild coalescing remains in place for model/zoom changes.
3. Content-space `_routes` were preserved; scroll offsets are not cached.
4. Painted-output regression coverage now verifies DPR 1/1.25/1.5/2, exact X/Y
   shifts, first/middle/last row centers, all five zoom levels, Day/Week/Month/
   Quarter, scale-then-scroll behavior, hierarchy, flat-sort, and vertical
   scrolling. Connector anchors are checked against the shared
   `GanttGeometry.js` bar/milestone geometry.
5. Existing semantic, density, selection, and performance tests remain intact.

Files modified by the approved fix:

- `src/ui_qml/modules/project_management/qml/workspaces/scheduling/components/gantt/SchedulingGanttDependencyLayer.qml`
- `src/ui_qml/modules/project_management/qml/workspaces/scheduling/components/gantt/SchedulingGanttRowsViewport.qml`
- `src/ui_qml/modules/project_management/qml/workspaces/scheduling/components/gantt/SchedulingGanttSurface.qml`
- `src/tests/project_management/test_r4_5e_gantt_dependencies.py`
- `docs/pm_modernization/R4_5E_GANTT_DEPENDENCY_VISUALIZATION.md` for closure evidence
- this audit document

No changes were made to FS/SS/FF/SF semantics, lag handling, CPM, task dates,
dependency persistence, the scheduling engine, the Gantt model, row
virtualization, or the approved R4.5 architecture.

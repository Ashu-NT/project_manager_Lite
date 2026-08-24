# R4.5D Gantt Time Axis Implementation

**Status:** COMPLETE
**Next phase:** R4.5E - Gantt dependency visualization
**Commit:** D production source was committed by the user as `67d4ba77`; no commit was created by the assistant

## Boundary

R4.5D introduces deterministic timeline range, scale, zoom, header, Today, and
calendar-shading presentation. It does not calculate schedule dates, compress
non-working days, render dependency or baseline layers, redesign milestones,
run CPM, add scheduling commands, or begin R5.

The canonical scheduling engine remains business truth. The Gantt projection
and axis are disposable read/display models and can be rebuilt from
authoritative project, task, schedule, and calendar facts.

## Implementation

The project-wide unpadded range is calculated once by the desktop scheduling
projection from all planned start/finish dates, actual start/finish dates, and
explicit project bounds. A task outside the nominal project dates extends the
range rather than being clipped. Search, filter, sort, hierarchy collapse,
selection, and viewport state never alter that base range.

`GanttTimeAxisController` owns display state only:

- Week is the default scale;
- Day, Week, Month, and Quarter use 40, 12, 4, and 1.5 pixels/day;
- zoom multipliers are exactly 0.75, 0.875, 1.0, 1.25, and 1.5;
- scale padding is 3 days, 7 days, 1 calendar month, or 3 calendar months;
- timescale changes reset zoom to neutral;
- ticks and shading descriptors are bounded to the visible window plus
  scale-specific overscan;
- extreme content width exposes a truthful safety warning;
- Today is unavailable outside the padded range and never expands it.

The QML surface retains one `timelineAxis.contentX` authority. The two-band
header, recycled bars and milestones, Today marker, and non-working shading all
consume the same `rangeStartDay` and `pixelsPerDay`. Zoom, scale, and responsive
resize preserve the viewport center transactionally so intermediate Flickable
clamping cannot overwrite the saved date.

Normal bars use inclusive day geometry:

```text
x = (startDay - rangeStartDay) * pixelsPerDay
width = max(12, (finishDay - startDay + 1) * pixelsPerDay)
```

Milestones use the center of their authoritative start-day cell. Unscheduled
rows remain in the grid with truthful text and no fabricated bar.

## Calendar Authority

The scheduling desktop API resolves the project-bound enterprise calendar
through the established scheduling engine. The projection bulk-materializes
coalesced non-working intervals over the largest possible padded range.

Shading is enabled only when the resolved calendar exposes authoritative bulk
working dates or an authoritative `is_working_day` predicate. Calendar
exceptions are respected, including configured working weekends and weekday
holidays. If no authoritative calendar is available, no weekend assumption or
shading is fabricated.

## Files

Created:

```text
docs/pm_modernization/R4_5D_GANTT_TIME_AXIS_IMPLEMENTATION.md
src/tests/project_management/test_r4_5d_gantt_time_axis.py
src/ui_qml/modules/project_management/controllers/scheduling/gantt_time_axis_controller.py
```

Modified:

```text
docs/pm_modernization/R4_5_GANTT_ENGINEERING_AUDIT.md
src/core/modules/project_management/api/desktop/scheduling/api.py
src/core/modules/project_management/api/desktop/scheduling/builders/gantt_builder.py
src/core/modules/project_management/api/desktop/scheduling/models/__init__.py
src/core/modules/project_management/api/desktop/scheduling/models/gantt.py
src/tests/project_management/test_qml_scheduling_planning_ia_contract.py
src/ui_qml/modules/project_management/controllers/scheduling/gantt_list_model.py
src/ui_qml/modules/project_management/controllers/scheduling/scheduling_state_loader.py
src/ui_qml/modules/project_management/controllers/scheduling/scheduling_workspace_controller.py
src/ui_qml/modules/project_management/qml/ProjectManagement/Controllers/typeinfo/plugins.qmltypes
src/ui_qml/modules/project_management/qml/workspaces/scheduling/components/gantt/SchedulingGanttBar.qml
src/ui_qml/modules/project_management/qml/workspaces/scheduling/components/gantt/SchedulingGanttHeader.qml
src/ui_qml/modules/project_management/qml/workspaces/scheduling/components/gantt/SchedulingGanttRow.qml
src/ui_qml/modules/project_management/qml/workspaces/scheduling/components/gantt/SchedulingGanttSurface.qml
src/ui_qml/modules/project_management/qml/workspaces/scheduling/panels/SchedulingGanttPanel.qml
```

Deleted: none.

No temporary adapter, compatibility shim, second timeline renderer, or
temporary source file was introduced.

## Measurements

Measurements use `pmenv` and exclude projection construction, database reads,
and CPM. Each sample attaches the already-built projection, selects Day scale,
pans to a viewport, zooms in, and zooms out.

| Rows | Axis interactions | Major ticks | Minor ticks |
|---:|---:|---:|---:|
| 100 | 0.467 ms | 2 | 8 |
| 1,000 | 0.333 ms | 2 | 8 |
| 5,000 | 0.313 ms | 2 | 8 |

The multi-millennial stress case also stays below the 100 ms interaction gate
because descriptors are generated only for the visible buffered window, not
for every day in the project range.

The retained R4.5C viewport benchmark remained bounded at 20 active delegates
for 100, 1,000, and 5,000 rows. Its latest 5,000-row measurements were 174.376
ms model attach, 31.458 ms first viewport, 0.032 ms selection, 12.057 ms
vertical scroll, 11.756 ms local filter, and 0.208 ms mode switch.

## Verification

- 48 targeted R4.5B/C/D and Planning IA tests passed;
- runtime QML verifies center preservation across zoom, scale, and resize;
- range, leap-day, ISO week, month, quarter, one-day, no-date, actual-date,
  project-bound, and calendar-exception cases passed;
- 100/1,000/5,000 axis and viewport characterizations passed;
- direct `pyside6-qmllint` over all changed Gantt QML is silent;
- no full test suite was run;
- no commit was created by the assistant; the user committed the D production
  source during implementation as `67d4ba77`.

## Historical R4.5E Handoff

R4.5E may add exactly one centralized, viewport-aware dependency Canvas above
the timeline rows. It must consume the existing project-wide typed edge facts
and this phase's exact bar/time coordinate system. It must not create one
permanent QML object per project edge, query dependencies during scroll/zoom/
selection, calculate dependency effects in QML, or create another date-to-pixel
formula.

R4.5E remains responsible for truthful FS/SS/FF/SF anchors, signed lag metadata,
complete-edge visibility rules, visible/overscan adjacency lookup, selected
incident-edge emphasis, coalesced repaint, and measurement-backed high-density
behavior. Baseline overlays, final critical-path styling, dependency CRUD,
milestone redesign, and R5 remain excluded.

R4.5E-H completed this handoff without adding another axis or scheduling-math
implementation. Final axis and geometry validation is recorded in
`R4_5_GANTT_CLOSURE.md`.

# UI Calendar Module

`ui/calendar/` provides scheduling-calendar operations and date computation UX.

## Files

- `tab.py`: coordinator tab and widget composition
- `working_time.py`: working-days and hours/day operations
- `holidays.py`: holiday CRUD operations
- `calculator.py`: working-day calculator actions
- `project_ops.py`: project schedule recalculation actions

## UI Surface Areas

1. Working calendar configuration:
   - weekday selection
   - hours-per-day input
2. Non-working day management:
   - holiday list
   - add/remove holiday
3. Working-day calculator:
   - start date + day count to derived finish date
4. Project schedule recalc:
   - select project
   - trigger CPM recalculation

## Technical Behavior

- Uses `WorkCalendarService` for persisted calendar mutations.
- Uses `WorkCalendarEngine` for day arithmetic in calculator mode.
- Uses `SchedulingEngine` for project schedule recomputation.
- Uses async job flow for long schedule recalculation to avoid UI blocking.

## Permission Model

- mutation actions require `task.manage`
- buttons disabled with permission hints when unavailable

## Event Model

- subscribes to `domain_events.project_changed` to refresh project selector

## Data and UX Integrity

- calendar summary label reflects active calendar settings
- holiday table is read-only grid with explicit action buttons
- recalc action applies to selected project only and surfaces business errors cleanly

# UI Shared Module

`ui/shared/` contains reusable presentation infrastructure used by multiple tabs.

## Files

- `guards.py`: permission-aware guarded slot and error handling helpers
- `async_job.py`: generic async job runner with progress, cancel, retry
- `worker_services.py`: isolated worker-session service scope for background tasks
- `combo.py`: combo box utility helpers
- `table_model.py`: shared table-model header helpers

## Guard Helpers (`guards.py`)

Core utilities:

- `has_permission(...)`
- `can_execute_governed_action(...)`
- `apply_permission_hint(...)`
- `run_guarded_action(...)`
- `make_guarded_slot(...)`

Purpose:

- unify action-level permission checks
- map typed business exceptions to user-friendly dialogs
- prevent duplicated try/except UI boilerplate

## Async Job Framework (`async_job.py`)

Implements:

- cancellation token (`CancelToken`)
- worker runnable (`QRunnable`)
- signal bridge (`progress`, `success`, `failure`, `cancelled`)
- optional modal progress dialog
- retry prompt behavior for recoverable failures
- automatic lifecycle cleanup of handle references

This is the standard pattern for long operations in the app.

## Worker Service Scope (`worker_services.py`)

Background task helper:

- creates dedicated SQLAlchemy session
- builds full service dict for worker thread
- copies current principal into worker user session context
- closes session safely after work completes

This avoids using UI-thread session objects inside worker threads.

## Why This Module Matters

Without `ui/shared`, each feature tab would need bespoke implementations for:

- threading patterns
- permission hints
- common dialog error behavior

Centralization keeps behavior consistent and significantly reduces defect surface.

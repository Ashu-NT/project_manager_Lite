# Test Module

`tests/` provides functional, architectural, and performance quality gates.

## Coverage Categories

## Functional Flows

- project, task, resource, cost, calendar workflows
- dependency and assignment UX logic
- baseline comparison and reporting math
- finance integration and policy alignment

## Security and Governance

- auth module and RBAC behaviors
- governance request, approve, reject flows
- session permission checks
- audit-log behavior

## UI and Settings

- UI tab interaction logic
- settings persistence
- permission guard behavior
- productization and support-tab logic

## Architecture Guardrails

- monolith growth budgets for known large files
- layer-rule enforcement (`core` must not import `ui`)
- coordinator-only and facade-only module checks

## Performance

- `test_large_scale_performance.py`:
  - synthetic large workload seeding
  - schedule and baseline execution
  - reporting and dashboard data generation
  - SLA assertions for phase timings and total runtime
  - opt-in execution via `PM_RUN_PERF_TESTS=1`

## Update and Version Tests

- update manifest parsing and result behavior
- runtime version resolution precedence
- updater download, hash validation, and handoff script generation

## Testing Strategy Notes

- strong use of service-layer tests to validate business logic independent of UI
- targeted UI behavior tests complement service coverage for integration confidence
- architecture tests prevent regression toward monolithic modules

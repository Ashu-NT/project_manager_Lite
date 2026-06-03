# Large Files — Refactor Priority List

**Generated:** 2026-06-03  
**Threshold:** > 350 LOC  
**Total files:** 200  

Priority is ordered by **production impact first** (services → APIs → controllers/presenters → infrastructure → QML → tests → migrations).  
Within each tier, files are ordered by LOC descending.

---

## Priority Tier 1 — Application Services (Business Logic)

These own business rules and are hardest to test, reason about, and extend at scale.  
Target: split by command/query, by aggregate, or extract mixins into purpose-named units.

| LOC | File |
|----:|------|
| 1096 | `src/core/modules/maintenance/application/preventive/preventive_generation_service.py` |
|  914 | `src/core/modules/maintenance/application/work_orders/work_order_service.py` |
|  849 | `src/core/modules/maintenance/application/preventive/preventive_plan_service.py` |
|  804 | `src/core/modules/inventory_procurement/application/inventory/foundation_service.py` |
|  706 | `src/core/modules/maintenance/application/reliability/reliability_service.py` |
|  608 | `src/core/modules/maintenance/application/work_orders/work_order_material_requirement_service.py` |
|  606 | `src/core/modules/inventory_procurement/application/catalog/service.py` |
|  604 | `src/core/modules/maintenance/application/assets/asset_service.py` |
|  586 | `src/core/modules/maintenance/application/preventive/preventive_plan_task_service.py` |
|  584 | `src/core/platform/documents/application/document_service.py` |
|  562 | `src/core/modules/maintenance/application/documents/document_service.py` |
|  555 | `src/core/modules/project_management/application/scheduling/baseline_service.py` |
|  533 | `src/core/modules/maintenance/application/work_requests/work_request_service.py` |
|  522 | `src/core/modules/maintenance/application/common/support.py` |
|  506 | `src/core/modules/maintenance/application/assets/component_service.py` |
|  480 | `src/core/modules/inventory_procurement/infrastructure/importers/service.py` |
|  476 | `src/core/platform/data_exchange/service.py` |
|  473 | `src/core/modules/maintenance/application/reliability/sensor_service.py` |
|  471 | `src/core/modules/inventory_procurement/application/inventory/reservation_service.py` |
|  470 | `src/core/modules/maintenance/application/reliability/downtime_event_service.py` |
|  458 | `src/core/modules/inventory_procurement/application/procurement/purchasing_lifecycle.py` |
|  447 | `src/core/platform/time/application/timesheet_support.py` |
|  440 | `src/core/modules/maintenance/domain/preventive/schedule.py` |
|  417 | `src/core/modules/maintenance/application/work_orders/work_order_task_step_service.py` |
|  412 | `src/core/modules/inventory_procurement/application/inventory/stock_control_adjustments.py` |
|  399 | `src/core/platform/org/application/department_service.py` |
|  397 | `src/core/modules/maintenance/application/reliability/sensor_exception_service.py` |
|  397 | `src/core/modules/maintenance/domain/reliability/monitoring.py` |
|  386 | `src/core/modules/inventory_procurement/application/inventory/service.py` |
|  383 | `src/core/modules/inventory_procurement/application/procurement/procurement_lifecycle.py` |
|  378 | `src/core/modules/maintenance/application/work_orders/work_order_task_service.py` |
|  357 | `src/core/modules/inventory_procurement/application/procurement/purchasing_receiving.py` |
|  357 | `src/core/modules/inventory_procurement/application/common/support.py` |
|  354 | `src/core/modules/project_management/application/tasks/commands/lifecycle.py` |
|  353 | `src/core/modules/maintenance/application/assets/system_service.py` |
|  1025 | `src/core/platform/auth/application/auth_service.py` |

---

## Priority Tier 2 — API / Desktop Layer

Orchestration code between services and the UI. Complex dispatch, serialization, and business rules mixed together. Target: split by workspace section or extract serializers.

| LOC | File |
|----:|------|
| 2793 | `src/core/modules/project_management/api/desktop/dashboard.py` |
| 1345 | `src/core/modules/project_management/api/desktop/tasks.py` |
| 1241 | `src/core/modules/project_management/api/desktop/scheduling.py` |
|  854 | `src/core/modules/maintenance/api/desktop/preventive/api.py` |
|  835 | `src/core/modules/project_management/api/desktop/financials.py` |
|  821 | `src/api/desktop/runtime.py` |
|  787 | `src/api/desktop/platform/enterprise_calendar.py` |
|  786 | `src/core/modules/maintenance/api/desktop/assets/api.py` |
|  726 | `src/core/modules/project_management/api/desktop/portfolio.py` |
|  716 | `src/core/modules/project_management/api/desktop/resources.py` |
|  675 | `src/core/modules/inventory_procurement/api/desktop/inventory/foundation.py` |
|  664 | `src/core/modules/project_management/api/desktop/timesheets.py` |
|  631 | `src/core/modules/inventory_procurement/api/desktop/procurement/api.py` |
|  626 | `src/core/modules/project_management/api/desktop/projects.py` |
|  597 | `src/core/modules/inventory_procurement/api/desktop/pricing/api.py` |
|  591 | `src/api/desktop/platform/support.py` |
|  521 | `src/core/modules/maintenance/api/desktop/planner/api.py` |
|  412 | `src/core/modules/project_management/api/desktop/collaboration.py` |
|  409 | `src/core/modules/project_management/infrastructure/reporting/renderers/excel.py` |
|  404 | `src/core/modules/maintenance/api/desktop/preventive/serializers.py` |
|  402 | `src/core/modules/inventory_procurement/api/desktop/dashboard.py` |
|  386 | `src/core/modules/maintenance/api/desktop/work_requests/api.py` |
|  382 | `src/core/modules/maintenance/api/desktop/preventive/models.py` |
|  377 | `src/core/modules/project_management/infrastructure/reporting/api.py` |
|  357 | `src/core/modules/project_management/api/desktop/register.py` |
|  356 | `src/core/modules/maintenance/api/desktop/reliability/api.py` |
|  351 | `src/core/modules/project_management/api/desktop/__init__.py` |

---

## Priority Tier 3 — Controllers & Presenters (UI Logic)

QML controller/presenter files are the glue between services and the view layer. Very long files here make UI bugs hard to trace. Target: split by section or extract sub-controllers.

| LOC | File |
|----:|------|
| 2138 | `src/ui_qml/modules/project_management/presenters/tasks_workspace_presenter.py` |
| 1797 | `src/ui_qml/modules/project_management/controllers/scheduling/scheduling_workspace_controller.py` |
| 1452 | `src/ui_qml/modules/maintenance/presenters/preventive_workspace_presenter.py` |
| 1358 | `src/ui_qml/modules/project_management/controllers/tasks/tasks_workspace_controller.py` |
| 1289 | `src/ui_qml/modules/maintenance/presenters/assets_workspace_presenter.py` |
| 1207 | `src/ui_qml/modules/project_management/controllers/common/serializers.py` |
| 1187 | `src/ui_qml/modules/inventory_procurement/presenters/procurement_workspace_presenter.py` |
| 1179 | `src/ui_qml/modules/inventory_procurement/presenters/inventory_workspace_presenter.py` |
| 1048 | `src/ui_qml/modules/inventory_procurement/controllers/procurement/procurement_workspace_controller.py` |
| 1046 | `src/ui_qml/platform/controllers/admin/admin_console_controller.py` |
| 1018 | `src/ui_qml/modules/inventory_procurement/controllers/inventory/inventory_workspace_controller.py` |
|  944 | `src/ui_qml/modules/project_management/controllers/collaboration/collaboration_workspace_controller.py` |
|  940 | `src/ui_qml/modules/project_management/controllers/projects/projects_workspace_controller.py` |
|  932 | `src/ui_qml/modules/inventory_procurement/presenters/catalog_workspace_presenter.py` |
|  846 | `src/ui_qml/modules/inventory_procurement/controllers/catalog/catalog_workspace_controller.py` |
|  786 | `src/ui_qml/modules/maintenance/controllers/assets/assets_workspace_controller.py` |
|  775 | `src/ui_qml/modules/project_management/presenters/projects_workspace_presenter.py` |
|  712 | `src/ui_qml/modules/maintenance/controllers/common/serializers.py` |
|  696 | `src/ui_qml/modules/project_management/presenters/register_workspace_presenter.py` |
|  687 | `src/ui_qml/modules/project_management/controllers/resources/resources_workspace_controller.py` |
|  666 | `src/ui_qml/modules/project_management/presenters/financials_workspace_presenter.py` |
|  630 | `src/ui_qml/modules/project_management/presenters/collaboration_workspace_presenter.py` |
|  630 | `src/ui_qml/modules/maintenance/presenters/work_orders_workspace_presenter.py` |
|  629 | `src/ui_qml/modules/project_management/controllers/timesheets/timesheets_workspace_controller.py` |
|  624 | `src/ui_qml/modules/maintenance/controllers/preventive/preventive_workspace_controller.py` |
|  622 | `src/ui_qml/modules/project_management/controllers/financials/financials_workspace_controller.py` |
|  610 | `src/ui_qml/modules/project_management/presenters/portfolio_workspace_presenter.py` |
|  608 | `src/ui_qml/modules/project_management/presenters/resources_workspace_presenter.py` |
|  600 | `src/ui_qml/modules/project_management/controllers/dashboard/dashboard_workspace_controller.py` |
|  556 | `src/ui_qml/modules/project_management/controllers/tasks/pm_task_list_controller.py` |
|  539 | `src/ui_qml/modules/project_management/controllers/register/register_workspace_controller.py` |
|  536 | `src/ui_qml/modules/inventory_procurement/controllers/pricing/pricing_workspace_controller.py` |
|  520 | `src/ui_qml/platform/presenters/document_management_presenter.py` |
|  517 | `src/ui_qml/modules/project_management/controllers/portfolio/portfolio_workspace_controller.py` |
|  487 | `src/ui_qml/modules/maintenance/presenters/work_requests_workspace_presenter.py` |
|  483 | `src/ui_qml/modules/inventory_procurement/controllers/reservations/reservations_workspace_controller.py` |
|  470 | `src/ui_qml/modules/project_management/presenters/timesheets_workspace_presenter.py` |
|  463 | `src/ui_qml/modules/maintenance/controllers/work_requests/work_requests_workspace_controller.py` |
|  418 | `src/ui_qml/modules/inventory_procurement/presenters/reservations_workspace_presenter.py` |
|  400 | `src/ui_qml/modules/maintenance/controllers/reliability/reliability_workspace_controller.py` |
|  375 | `src/ui_qml/platform/controllers/admin/access_workspace_controller.py` |

---

## Priority Tier 4 — Infrastructure (ORM, Repositories, Mappers)

Infrastructure files are stable but large ones indicate aggregated responsibility. Target: split by aggregate root or module boundary.

| LOC | File |
|----:|------|
| 1489 | `src/core/modules/maintenance/infrastructure/persistence/repositories/repository.py` |
| 1282 | `src/core/modules/maintenance/infrastructure/persistence/orm/models.py` |
| 1203 | `src/core/modules/maintenance/infrastructure/persistence/mappers/mapper.py` |
|  607 | `src/core/modules/project_management/infrastructure/importers/import_parser.py` |
|  591 | `src/core/modules/maintenance/infrastructure/reporting/service.py` |
|  580 | `src/core/platform/infrastructure/persistence/repositories/enterprise_calendar.py` |
|  549 | `src/core/modules/maintenance/infrastructure/reporting/documents.py` |
|  535 | `src/core/modules/inventory_procurement/infrastructure/persistence/repositories/inventory.py` |
|  519 | `src/core/platform/calendar/domain/enterprise_calendar.py` |
|  508 | `src/core/modules/inventory_procurement/infrastructure/reporting/service.py` |
|  480 | `src/core/modules/inventory_procurement/infrastructure/importers/service.py` |
|  422 | `src/core/modules/inventory_procurement/infrastructure/importers/parsing.py` |
|  422 | `src/core/modules/inventory_procurement/api/desktop/inventory/models.py` |
|  419 | `src/core/modules/inventory_procurement/infrastructure/integrations/maintenance_materials.py` |
|  409 | `src/core/modules/project_management/infrastructure/reporting/renderers/excel.py` |
|  397 | `src/core/modules/inventory_procurement/infrastructure/persistence/orm/inventory.py` |
|  394 | `src/core/modules/project_management/infrastructure/reporting/cost_policy.py` |
|  392 | `src/core/platform/infrastructure/persistence/mappers/enterprise_calendar.py` |
|  377 | `src/core/modules/project_management/infrastructure/reporting/api.py` |
|  376 | `src/core/modules/inventory_procurement/infrastructure/persistence/mappers/inventory.py` |
|  365 | `src/core/modules/maintenance/infrastructure/importers/contracts.py` |
|  363 | `src/core/platform/infrastructure/persistence/orm/enterprise_calendar.py` |

---

## Priority Tier 5 — QML Workspace Files

Large QML orchestrators make it hard to trace UI state bugs. Target: extract panels, sections, and list pages into sub-files (the established workspace pattern).

| LOC | File |
|----:|------|
|  950 | `src/ui_qml/platform/qml/workspaces/admin/AdminConsolePage.qml` |
|  853 | `src/ui_qml/shared/qml/App/Widgets/DataTable.qml` |
|  663 | `src/ui_qml/platform/qml/workspaces/admin/detail/AdminCalendarDetailPage.qml` |
|  594 | `src/ui_qml/modules/project_management/qml/workspaces/portfolio/panels/PortfolioDetailPanel.qml` |
|  563 | `src/ui_qml/platform/qml/workspaces/admin/detail/AdminSiteDetailPage.qml` |
|  557 | `src/ui_qml/platform/qml/Platform/Widgets/AccessSecurityPanel.qml` |
|  542 | `src/ui_qml/platform/qml/workspaces/admin/detail/AdminPartyDetailPage.qml` |
|  542 | `src/ui_qml/platform/qml/workspaces/admin/detail/AdminDocumentsDetailPage.qml` |
|  535 | `src/ui_qml/modules/project_management/qml/ProjectManagement/Widgets/DashboardChartCard.qml` |
|  529 | `src/ui_qml/modules/project_management/qml/workspaces/scheduling/panels/SchedulingDetailPanel.qml` |
|  508 | `src/ui_qml/platform/qml/workspaces/admin/detail/AdminDepartmentDetailPage.qml` |
|  495 | `src/ui_qml/platform/qml/workspaces/admin/sections/AdminAuditSection.qml` |
|  482 | `src/ui_qml/platform/qml/workspaces/admin/detail/AdminEmployeeDetailPage.qml` |
|  482 | `src/ui_qml/modules/project_management/qml/workspaces/tasks/TasksWorkspacePage.qml` |
|  450 | `src/ui_qml/modules/project_management/qml/workspaces/scheduling/SchedulingWorkspacePage.qml` |
|  446 | `src/ui_qml/shell/qml/LoginWindow.qml` |
|  440 | `src/ui_qml/modules/project_management/qml/workspaces/portfolio/panels/PortfolioBottomPanel.qml` |
|  425 | `src/ui_qml/platform/qml/workspaces/admin/detail/AdminEntityDetailPage.qml` |
|  425 | `src/ui_qml/modules/project_management/qml/workspaces/register/panels/RegisterDetailPanel.qml` |
|  425 | `src/ui_qml/modules/project_management/qml/workspaces/collaboration/CollaborationWorkspaceState.qml` |
|  424 | `src/ui_qml/modules/project_management/qml/workspaces/tasks/sections/TasksTimeEntriesSection.qml` |
|  423 | `src/ui_qml/platform/qml/workspaces/admin/detail/AdminUserDetailPage.qml` |
|  421 | `src/ui_qml/platform/qml/workspaces/control/ControlWorkspacePage.qml` |
|  416 | `src/ui_qml/platform/qml/workspaces/admin/detail/AdminOrganizationDetailPage.qml` |
|  415 | `src/ui_qml/platform/qml/workspaces/admin/dialogs/AdminDialogHost.qml` |
|  405 | `src/ui_qml/modules/project_management/qml/workspaces/collaboration/CollaborationWorkspacePage.qml` |
|  405 | `src/ui_qml/modules/project_management/qml/ProjectManagement/Dialogs/ProjectsImportDialog.qml` |
|  395 | `src/ui_qml/modules/project_management/qml/workspaces/projects/sections/ProjectsResourcesSection.qml` |
|  394 | `src/ui_qml/modules/project_management/qml/workspaces/tasks/panels/TasksDetailPanel.qml` |
|  388 | `src/ui_qml/modules/project_management/qml/workspaces/resources/sections/ResourcesAvailabilitySection.qml` |
|  387 | `src/ui_qml/platform/qml/workspaces/admin/panels/AdminEntityDetailPanel.qml` |
|  380 | `src/ui_qml/modules/inventory_procurement/qml/workspaces/catalog/components/CatalogListPage.qml` |
|  370 | `src/ui_qml/modules/inventory_procurement/qml/workspaces/procurement/ProcurementWorkspacePage.qml` |
|  360 | `src/ui_qml/platform/qml/workspaces/admin/detail/AdminAccessDetailPage.qml` |
|  359 | `src/ui_qml/modules/project_management/qml/workspaces/tasks/dialogs/TasksDialogHost.qml` |
|  354 | `src/ui_qml/modules/project_management/qml/workspaces/portfolio/PortfolioWorkspacePage.qml` |
|  352 | `src/ui_qml/platform/qml/workspaces/control/detail/ControlApprovalDetailPage.qml` |
|  352 | `src/ui_qml/platform/qml/Platform/Dialogs/PartyEditorDialog.qml` |

---

## Priority Tier 6 — Composition & Config

Wiring files. These grow naturally but signal architecture smell when very large.

| LOC | File |
|----:|------|
|  491 | `src/infra/composition/maintenance_registry.py` |
|  438 | `src/api/desktop/platform/models/enterprise_calendar.py` |
|  431 | `src/infra/composition/project_registry.py` |
|  407 | `src/infra/composition/app_container.py` |

---

## Priority Tier 7 — Tests

Large test files reduce test isolation and increase CI time. Target: split by scenario group.

| LOC | File |
|----:|------|
| 3378 | `src/tests/project_management/test_project_management_desktop_api.py` |
| 2483 | `src/tests/platform/test_qml_platform_presenters.py` |
| 2280 | `src/tests/project_management/test_qml_project_management_presenters.py` |
| 1057 | `src/tests/maintenance/test_maintenance_foundation.py` |
| 1004 | `src/tests/maintenance/test_maintenance_desktop_api.py` |
|  922 | `src/tests/maintenance/test_maintenance_persistence.py` |
|  782 | `src/tests/inventory_procurement/test_inventory_procurement_desktop_api.py` |
|  755 | `src/tests/platform/test_enterprise_calendar_foundation.py` |
|  741 | `src/tests/inventory_procurement/test_qml_inventory_procurement_presenters.py` |
|  694 | `src/tests/architecture/test_architecture_guardrails.py` |
|  661 | `src/tests/architecture/test_qml_architecture_guardrails.py` |
|  600 | `src/tests/project_management/test_enterprise_calendar_pm_integration.py` |
|  546 | `src/tests/inventory_procurement/test_inventory_procurement_purchasing.py` |
|  500 | `src/tests/maintenance/test_qml_maintenance_presenters.py` |
|  469 | `src/tests/test_exporters_configuration.py` |
|  460 | `src/tests/inventory_procurement/test_qml_inventory_procurement_dialog_hosts.py` |
|  431 | `src/tests/project_management/test_technical_math_reporting.py` |
|  424 | `src/tests/test_qml_shared_primitives.py` |
|  417 | `src/tests/project_management/test_enterprise_pm_foundation.py` |
|  391 | `src/tests/maintenance/test_maintenance_preventive_foundation.py` |
|  389 | `src/tests/project_management/test_shared_collaboration_import_and_timesheets.py` |
|  381 | `src/tests/path_rewrites.py` |
|  378 | `src/tests/test_qml_domain_event_bridges.py` |
|  378 | `src/tests/project_management/test_business_rules_and_edge_cases.py` |
|  361 | `src/tests/maintenance/test_maintenance_preventive_generation.py` |
|  355 | `src/tests/inventory_procurement/test_inventory_procurement_foundation.py` |

---

## Priority Tier 8 — Migration Files

Schema files. Rarely changed. Document them but do not refactor.

| LOC | File |
|----:|------|
|  357 | `src/infra/persistence/migrations/versions/n7o8p9q0r1s2_add_platform_enterprise_calendars.py` |
|  351 | `src/infra/persistence/migrations/versions/9d4e7f1a2b3c_expand_shared_master_metadata.py` |

---

## Quick Stats by Tier

| Tier | Files | Refactor approach |
|---|---|---|
| 1 — Application Services | 35 | Split by command/query, aggregate, or mixin |
| 2 — API / Desktop Layer | 27 | Split by workspace section, extract serializers |
| 3 — Controllers / Presenters | 41 | Extract sub-controllers, section presenters |
| 4 — Infrastructure | 22 | Split by aggregate root or bounded context |
| 5 — QML Workspace Files | 38 | Extract panels, sections, list pages |
| 6 — Composition / Config | 4 | Extract sub-registries per module |
| 7 — Tests | 26 | Split by scenario group |
| 8 — Migration Files | 2 | Document only — do not refactor |
| **Total** | **200** | |

---

## Top 10 Highest-Impact Splits

These 10 files alone account for the most technical debt by volume and domain impact:

1. `test_project_management_desktop_api.py` (3378) — split by workspace domain
2. `dashboard.py` API (2793) — extract KPI, EVM, alerting, portfolio sections
3. `tasks_workspace_presenter.py` (2138) — split by lifecycle, timesheet, assignment
4. `scheduling_workspace_controller.py` (1797) — split by CPM, baseline, leveling, calendar
5. `maintenance/repositories/repository.py` (1489) — split by asset, WO, preventive, reliability
6. `scheduling_workspace_presenter.py` (1462) — split by section
7. `preventive_workspace_presenter.py` (1452) — split by plan, task, instance
8. `tasks_workspace_controller.py` (1358) — split by lifecycle, assignment, dependencies
9. `tasks.py` API desktop (1345) — extract commands, queries, serializers
10. `maintenance/orm/models.py` (1282) — split by aggregate (asset, WO, preventive, reliability)

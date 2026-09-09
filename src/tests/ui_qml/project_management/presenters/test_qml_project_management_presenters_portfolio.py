from types import SimpleNamespace

from src.ui_qml.modules.project_management.context import ProjectManagementWorkspaceCatalog


def _page(items, *, page, page_size, sort_key, sort_direction, search_text):
    return SimpleNamespace(
        items=tuple(items),
        total=len(items),
        page=page,
        page_size=page_size,
        sort_key=sort_key,
        sort_direction=sort_direction,
        search_text=search_text,
    )


class _FakePortfolioDesktopApi:
    def list_projects(self):
        return (
            SimpleNamespace(value="proj-1", label="Plant Upgrade"),
            SimpleNamespace(value="proj-2", label="Warehouse Retrofit"),
        )

    def list_intake_statuses(self):
        return (
            SimpleNamespace(value="PROPOSED", label="Proposed"),
            SimpleNamespace(value="APPROVED", label="Approved"),
        )

    def list_dependency_types(self):
        return (SimpleNamespace(value="FINISH_TO_START", label="Finish -> Start"),)

    def list_templates(self):
        return (
            SimpleNamespace(
                id="tpl-1",
                name="Balanced PMO",
                summary="Standard weighted intake rubric.",
                weight_summary="Strategic x3, Value x2, Urgency x2, Risk x1",
                is_active=True,
            ),
        )

    def _all_intake_items(self):
        return (
            SimpleNamespace(
                id="intake-1",
                title="Packaging Line Expansion",
                sponsor_name="Operations Director",
                summary="Capacity uplift on the secondary line.",
                requested_budget_label="EUR 180,000.00",
                requested_capacity_label="40.0%",
                scoring_template_name="Balanced PMO",
                scoring_template_id="tpl-1",
                status="PROPOSED",
                status_label="Proposed",
                composite_score=27,
                version=2,
            ),
            SimpleNamespace(
                id="intake-2",
                title="Warehouse HVAC Refresh",
                sponsor_name="Facilities Lead",
                summary="Replace failing rooftop units.",
                requested_budget_label="EUR 95,000.00",
                requested_capacity_label="15.0%",
                scoring_template_name="Balanced PMO",
                scoring_template_id="tpl-1",
                status="APPROVED",
                status_label="Approved",
                composite_score=22,
                version=1,
            ),
        )

    def list_intake_items_page(
        self, *, status=None, search_text="", page=1, page_size=25,
        sort_key="updatedAt", sort_direction="desc",
    ):
        rows = self._all_intake_items()
        if status:
            rows = tuple(row for row in rows if row.status == status)
        return _page(
            rows, page=page, page_size=page_size,
            sort_key=sort_key, sort_direction=sort_direction, search_text=search_text,
        )

    def list_scenarios(self):
        return (
            SimpleNamespace(
                id="scn-1",
                name="Q3 Balanced Plan",
                budget_limit_label="EUR 500,000.00",
                capacity_limit_label="280.0%",
                project_ids=("proj-1",),
                intake_item_ids=("intake-1",),
                notes="Protect active execution first.",
                created_at_label="2026-05-01 09:00",
            ),
            SimpleNamespace(
                id="scn-2",
                name="Aggressive Expansion",
                budget_limit_label="EUR 650,000.00",
                capacity_limit_label="340.0%",
                project_ids=("proj-1", "proj-2"),
                intake_item_ids=("intake-1", "intake-2"),
                notes="Pull intake forward if labor opens up.",
                created_at_label="2026-05-02 10:30",
            ),
        )

    def evaluate_scenario(self, scenario_id):
        return SimpleNamespace(
            scenario_id=scenario_id,
            scenario_name="Q3 Balanced Plan",
            summary="Within budget with moderate capacity headroom.",
            selected_projects_label="1",
            selected_intake_items_label="1",
            total_budget_label="EUR 180,000.00",
            budget_limit_label="EUR 500,000.00",
            total_capacity_label="40.0%",
            capacity_limit_label="280.0%",
            available_capacity_label="240.0%",
            intake_score_label="27",
            status_label="Within limits",
        )

    def compare_scenarios(self, base_scenario_id, candidate_scenario_id):
        return SimpleNamespace(
            base_scenario_name="Q3 Balanced Plan",
            candidate_scenario_name="Aggressive Expansion",
            summary="Candidate adds one more intake item and one more project.",
            budget_delta_label="+EUR 95,000.00",
            capacity_delta_label="+15.0%",
            selected_projects_delta_label="+1",
            selected_intake_items_delta_label="+1",
            intake_score_delta_label="+22",
            added_project_names=("Warehouse Retrofit",),
            removed_project_names=(),
            added_intake_titles=("Warehouse HVAC Refresh",),
            removed_intake_titles=(),
        )

    def _all_heatmap_rows(self):
        return (
            SimpleNamespace(
                project_id="proj-1",
                project_name="Plant Upgrade",
                pressure_label="Hot",
                project_status_label="Active",
                late_tasks=2,
                critical_tasks=1,
                peak_utilization_label="118.0%",
                cost_variance_label="-EUR 8,500.00",
            ),
            SimpleNamespace(
                project_id="proj-2",
                project_name="Warehouse Retrofit",
                pressure_label="Watch",
                project_status_label="Planned",
                late_tasks=0,
                critical_tasks=0,
                peak_utilization_label="82.0%",
                cost_variance_label="+EUR 1,200.00",
            ),
        )

    def list_heatmap_page(
        self, *, search_text="", status=None, page=1, page_size=25,
        sort_key="projectName", sort_direction="asc",
    ):
        rows = self._all_heatmap_rows()
        if search_text:
            needle = search_text.casefold()
            rows = tuple(row for row in rows if needle in row.project_name.casefold())
        start = (page - 1) * page_size
        page_rows = rows[start: start + page_size]
        return _page(
            page_rows, page=page, page_size=page_size,
            sort_key=sort_key, sort_direction=sort_direction, search_text=search_text,
        )

    def list_top_at_risk_projects(self):
        return self._all_heatmap_rows()

    def _all_dependencies(self):
        return (
            SimpleNamespace(
                dependency_id="dep-1",
                predecessor_project_id="proj-1",
                successor_project_id="proj-2",
                predecessor_project_name="Plant Upgrade",
                successor_project_name="Warehouse Retrofit",
                pressure_label="Watch",
                dependency_type_label="Finish -> Start",
                predecessor_project_status_label="Active",
                successor_project_status_label="Planned",
                summary="Warehouse cutover waits for line shutdown lessons learned.",
                created_at_label="2026-05-03 08:45",
            ),
        )

    def list_dependencies_page(
        self, *, search_text="", page=1, page_size=25,
        sort_key="updatedAt", sort_direction="desc",
    ):
        return _page(
            self._all_dependencies(), page=page, page_size=page_size,
            sort_key=sort_key, sort_direction=sort_direction, search_text=search_text,
        )

    def get_executive_snapshot(self):
        heatmap_rows = self._all_heatmap_rows()
        dependency_rows = self._all_dependencies()
        return SimpleNamespace(
            heatmap=heatmap_rows,
            dependencies=dependency_rows,
            top_at_risk_projects=heatmap_rows,
            hot_project_count=sum(1 for row in heatmap_rows if row.pressure_label == "Hot"),
            dependency_count=len(dependency_rows),
        )

    def list_recent_actions(self, *, limit=12):
        assert limit == 12
        return (
            SimpleNamespace(
                occurred_at_label="2026-05-03 08:45",
                project_name="Plant Upgrade",
                actor_username="alex",
                action_label="Baseline created",
                summary="Weekly execution freeze published for governance review.",
            ),
        )

    def build_capacity_pool(self):
        return ()


def test_project_management_workspace_catalog_exposes_typed_portfolio_controller() -> None:
    catalog = ProjectManagementWorkspaceCatalog(
        desktop_api_registry=SimpleNamespace(
            project_management_portfolio=_FakePortfolioDesktopApi()
        )
    )

    controller = catalog.portfolioWorkspace

    assert controller.workspace["routeId"] == "project_management.portfolio"
    assert controller.overview["title"] == "Portfolio"
    assert controller.templateOptions[0]["label"] == "Balanced PMO"
    assert controller.intakeItems["items"][0]["title"] == "Packaging Line Expansion"
    assert controller.evaluation["title"] == "Scenario Evaluation: Q3 Balanced Plan"
    assert controller.comparison["fields"][0]["value"] == "+EUR 95,000.00"

    controller.setIntakeStatusFilter("APPROVED")

    assert controller.selectedIntakeStatusFilter == "APPROVED"
    assert [item["title"] for item in controller.intakeItems["items"]] == [
        "Warehouse HVAC Refresh"
    ]
    # Heatmap browse is server-paginated: total reflects the authoritative
    # server-side count, not a client-materialized list length.
    assert controller.heatmapTotalCount == 2
    assert [row["title"] for row in controller.heatmap["items"]] == [
        "Plant Upgrade", "Warehouse Retrofit",
    ]

    controller.setHeatmapSearchText("Warehouse")

    assert controller.heatmapSearchText == "Warehouse"
    assert controller.heatmapTotalCount == 1
    assert [row["title"] for row in controller.heatmap["items"]] == ["Warehouse Retrofit"]

    # Executive aggregates (hot count, Top At-Risk) are independent of the
    # Heatmap browse's current search/page state.
    assert controller.hotProjectCount == 1
    assert len(controller.topAtRiskProjects["items"]) == 2

    controller.setActiveTab("intake")
    assert controller.activeTab == "intake"

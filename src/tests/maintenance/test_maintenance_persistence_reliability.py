from __future__ import annotations


def test_maintenance_failure_codes_and_downtime_events_persist_via_service_graph(services):
    site = services["site_service"].create_site(site_code="MNT-RLY", name="Reliability Plant")
    location = services["maintenance_location_service"].create_location(
        site_id=site.id,
        location_code="rly-area",
        name="Reliability Area",
    )
    asset = services["maintenance_asset_service"].create_asset(
        site_id=site.id,
        location_id=location.id,
        asset_code="rly-asset",
        name="Reliability Asset",
    )
    symptom_code = services["maintenance_failure_code_service"].create_failure_code(
        failure_code="seal-leak",
        name="Seal Leak",
        code_type="symptom",
    )
    cause_code = services["maintenance_failure_code_service"].create_failure_code(
        failure_code="misalignment",
        name="Misalignment",
        code_type="cause",
    )
    work_request = services["maintenance_work_request_service"].create_work_request(
        site_id=site.id,
        work_request_code="wr-rly-100",
        source_type="manual",
        request_type="breakdown",
        asset_id=asset.id,
        location_id=location.id,
        title="Seal leak on main pump",
        failure_symptom_code=symptom_code.failure_code,
    )
    work_order = services["maintenance_work_order_service"].create_work_order(
        site_id=site.id,
        work_order_code="wo-rly-100",
        work_order_type="corrective",
        source_type="work_request",
        source_id=work_request.id,
    )
    updated_work_order = services["maintenance_work_order_service"].update_work_order(
        work_order.id,
        failure_code=symptom_code.failure_code,
        root_cause_code=cause_code.failure_code,
        expected_version=work_order.version,
    )
    downtime_event = services["maintenance_downtime_event_service"].create_downtime_event(
        work_order_id=updated_work_order.id,
        started_at="2026-04-03T08:00:00+00:00",
        ended_at="2026-04-03T09:15:00+00:00",
        downtime_type="unplanned",
        reason_code=symptom_code.failure_code,
        impact_notes="Production stopped during seal replacement.",
    )

    listed_codes = services["maintenance_failure_code_service"].list_failure_codes()
    listed_events = services["maintenance_downtime_event_service"].list_downtime_events(
        work_order_id=updated_work_order.id
    )
    reloaded_work_order = services["maintenance_work_order_service"].get_work_order(updated_work_order.id)

    assert [row.failure_code for row in listed_codes] == ["MISALIGNMENT", "SEAL-LEAK"]
    assert [row.id for row in listed_events] == [downtime_event.id]
    assert listed_events[0].duration_minutes == 75
    assert reloaded_work_order.failure_code == symptom_code.failure_code
    assert reloaded_work_order.root_cause_code == cause_code.failure_code
    assert reloaded_work_order.downtime_minutes == 75


def test_maintenance_reliability_service_summarizes_persisted_patterns(services):
    site = services["site_service"].create_site(site_code="MNT-RPT", name="Reliability Reporting Plant")
    location = services["maintenance_location_service"].create_location(
        site_id=site.id,
        location_code="rpt-area",
        name="Reporting Area",
    )
    asset = services["maintenance_asset_service"].create_asset(
        site_id=site.id,
        location_id=location.id,
        asset_code="rpt-asset",
        name="Reporting Asset",
    )
    symptom_code = services["maintenance_failure_code_service"].create_failure_code(
        failure_code="bearing-hot",
        name="Bearing Hot",
        code_type="symptom",
    )
    cause_code = services["maintenance_failure_code_service"].create_failure_code(
        failure_code="lube-loss",
        name="Lubrication Loss",
        code_type="cause",
    )

    for index in range(1, 3):
        work_request = services["maintenance_work_request_service"].create_work_request(
            site_id=site.id,
            work_request_code=f"wr-rpt-{index}",
            source_type="manual",
            request_type="breakdown",
            asset_id=asset.id,
            location_id=location.id,
            title=f"Bearing issue {index}",
            failure_symptom_code=symptom_code.failure_code,
        )
        work_order = services["maintenance_work_order_service"].create_work_order(
            site_id=site.id,
            work_order_code=f"wo-rpt-{index}",
            work_order_type="corrective",
            source_type="work_request",
            source_id=work_request.id,
        )
        planned = services["maintenance_work_order_service"].update_work_order(
            work_order.id,
            status="planned",
            expected_version=work_order.version,
        )
        released = services["maintenance_work_order_service"].update_work_order(
            planned.id,
            status="released",
            expected_version=planned.version,
        )
        in_progress = services["maintenance_work_order_service"].update_work_order(
            work_order.id,
            status="in_progress",
            expected_version=released.version,
        )
        completed = services["maintenance_work_order_service"].update_work_order(
            in_progress.id,
            status="completed",
            failure_code=symptom_code.failure_code,
            root_cause_code=cause_code.failure_code,
            expected_version=in_progress.version,
        )
        services["maintenance_downtime_event_service"].create_downtime_event(
            work_order_id=completed.id,
            started_at="2026-04-03T08:00:00+00:00",
            ended_at="2026-04-03T09:00:00+00:00",
            downtime_type="unplanned",
            reason_code=symptom_code.failure_code,
            impact_notes="Bearing temperature forced shutdown.",
        )

    dashboard = services["maintenance_reliability_service"].build_reliability_dashboard(
        asset_id=asset.id,
        days=365,
    )
    recurring = services["maintenance_reliability_service"].list_recurring_failure_patterns(
        asset_id=asset.id,
        days=365,
        min_occurrences=2,
    )
    suggestions = services["maintenance_reliability_service"].suggest_root_causes(
        failure_code=symptom_code.failure_code,
        asset_id=asset.id,
    )

    summary = {metric.label: metric.value for metric in dashboard.summary}
    assert summary["Open work orders"] == 0
    assert summary["Downtime minutes"] == 120
    assert dashboard.top_root_causes[0].root_cause_code == cause_code.failure_code
    assert recurring[0].occurrence_count == 2
    assert recurring[0].leading_root_cause_code == cause_code.failure_code
    assert suggestions[0].root_cause_code == cause_code.failure_code

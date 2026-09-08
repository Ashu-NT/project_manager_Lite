from src.core.modules.project_management.domain.enums import WorkerType
from src.ui_qml.modules.project_management.adapters.resources.resource_view_invalidation_adapter import (
    ResourceViewInvalidationAdapter,
)


def test_resource_view_invalidation_smoke(services):
    resource_service = services["resource_service"]
    org = services["tenant_context_service"].get_active_organization()

    adapter = ResourceViewInvalidationAdapter(
        channel=services["platform_view_invalidation_channel"],
        tenant_id=org.tenant_id,
        organization_id=org.id,
    )
    list_calls = []
    cap_calls = []
    adapter.resourceListStale.connect(lambda rid: list_calls.append(rid))
    adapter.resourceCapabilitiesStale.connect(lambda rid: cap_calls.append(rid))

    resource = resource_service.create_resource(name="P18B Smoke")
    assert list_calls == [resource.id]
    assert cap_calls == []

    resource_service.update_resource(
        resource_id=resource.id, expected_version=resource.version, name="P18B Smoke 2",
        code=resource.code, kind=resource.kind, role="", hourly_rate=resource.hourly_rate,
        cost_type=resource.cost_type, currency_code=resource.currency_code,
        capacity_percent=resource.capacity_percent, address="", contact="",
        worker_type=resource.worker_type, employee_id=None, department_id=None, site_id=None,
    )
    assert list_calls == [resource.id, resource.id]
    assert cap_calls == []

    skill = resource_service.add_resource_skill(resource.id, "PY", "Python")
    assert list_calls == [resource.id, resource.id]  # unchanged -- capability != list
    assert cap_calls == [resource.id]

    print("P18B SMOKE PASSED")

from src.core.shared.events.view_invalidation import (
    OrganizationScope,
    TenantScope,
    ViewInvalidationHint,
)
from src.infra.composition.global_overview_invalidation import (
    ACTION_CENTER_INVALIDATION_TARGETS,
)
from src.infra.events.in_process_view_invalidation_channel import (
    InProcessViewInvalidationChannel,
)
from src.ui_qml.shell.adapters.action_center_view_invalidation_adapter import (
    ActionCenterViewInvalidationAdapter,
)


def test_only_real_scoped_dependents_invalidate_and_rescope_disposes_old_subscription():
    channel = InProcessViewInvalidationChannel()
    adapter = ActionCenterViewInvalidationAdapter(channel=channel, targets=ACTION_CENTER_INVALIDATION_TARGETS)
    calls = []
    adapter.actionsStale.connect(lambda: calls.append(True))
    adapter.set_active_scope(tenant_id="tenant", organization_id="org")

    def send(category, code, scope):
        channel.notify(ViewInvalidationHint(scope=scope, category=category, scope_code=code, entity_type="test"))

    send("approval", "approval_requests", OrganizationScope("foreign", "org"))
    send("approval", "approval_requests", OrganizationScope("tenant", "foreign"))
    send("billing", "billing_transport", OrganizationScope("tenant", "org"))
    assert calls == []
    send("approval", "approval_requests", OrganizationScope("tenant", "org"))
    send("approval", "approval_requests", OrganizationScope("tenant", "org"))
    assert len(calls) == 2  # Separate committed hints must not be deduplicated here.
    send("role_binding", "role_binding_assignments", TenantScope("tenant"))
    assert len(calls) == 3
    adapter.set_active_scope(tenant_id="tenant", organization_id="new")
    send("approval", "approval_requests", OrganizationScope("tenant", "org"))
    assert len(calls) == 3
    send("approval", "approval_requests", OrganizationScope("tenant", "new"))
    assert len(calls) == 4
    adapter.dispose()
    send("approval", "approval_requests", OrganizationScope("tenant", "new"))
    assert len(calls) == 4

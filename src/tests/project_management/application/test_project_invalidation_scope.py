from datetime import UTC, datetime
from unittest.mock import Mock

from src.core.modules.project_management.application.projects.event_handlers.view_invalidation import (
    build_project_view_invalidation_handler,
)
from src.core.modules.project_management.application.projects.project_events import (
    ProjectCreated,
)
from src.core.shared.events.domain_event_context import DomainEventContext


def test_project_invalidation_never_emits_an_unscoped_hint(caplog):
    channel = Mock()
    handler = build_project_view_invalidation_handler(channel)
    handler(
        ProjectCreated(tenant_id=None, organization_id="org", project_id="project", occurred_at=datetime.now(UTC)),
        DomainEventContext(correlation_id="missing-tenant"),
    )
    channel.notify.assert_not_called()
    assert "tenant context is missing" in caplog.text

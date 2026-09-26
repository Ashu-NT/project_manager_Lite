from datetime import timedelta

from src.core.platform.application.integration import (
    IntegrationOutboxService,
    IntegrationRetryPolicy,
)
from src.core.platform.integration import OutboxDeliveryStatus
from src.tests.platform.integration.test_integration_delivery_foundation import (
    _Clock,
    _event,
    delivery_store,  # noqa: F401
)


def test_expired_final_attempt_is_terminal_without_exceeding_limit(request):
    session, _, repository, _ = request.getfixturevalue("delivery_store")
    clock = _Clock()
    service = IntegrationOutboxService(
        repository=repository, owner_module="platform_time", clock=clock, max_attempts=1
    )
    record = service.enqueue(_event())
    session.commit()
    assert (
        service.claim_batch(lease_token="first", lease_duration=timedelta(seconds=5))[
            0
        ].attempt_count
        == 1
    )
    session.commit()
    clock.advance(6)
    assert (
        service.claim_batch(lease_token="second", lease_duration=timedelta(seconds=5))
        == []
    )
    session.commit()
    exhausted = repository.get(record.id)
    assert exhausted.status is OutboxDeliveryStatus.DEAD_LETTER
    assert exhausted.attempt_count == exhausted.max_attempts == 1
    assert exhausted.lease_token is None
    assert exhausted.last_error_code == "DELIVERY_ATTEMPTS_EXHAUSTED"
    clock.advance(100)
    assert (
        service.claim_batch(lease_token="third", lease_duration=timedelta(seconds=5))
        == []
    )


def test_expiry_below_limit_recovers_with_new_lease(request):
    session, _, repository, _ = request.getfixturevalue("delivery_store")
    clock = _Clock()
    service = IntegrationOutboxService(
        repository=repository, owner_module="platform_time", clock=clock, max_attempts=2
    )
    service.enqueue(_event())
    session.commit()
    service.claim_batch(lease_token="first", lease_duration=timedelta(seconds=5))
    session.commit()
    clock.advance(6)
    recovered = service.claim_batch(
        lease_token="second", lease_duration=timedelta(seconds=5)
    )
    assert recovered[0].attempt_count == 2
    assert recovered[0].lease_token == "second"


def test_extreme_attempt_backoff_is_bounded():
    now = _Clock().now()
    assert IntegrationRetryPolicy().next_attempt_at(
        now=now, attempt_count=10**9
    ) == now + timedelta(minutes=15)

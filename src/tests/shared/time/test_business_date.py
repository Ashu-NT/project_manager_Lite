from __future__ import annotations

from datetime import date, datetime, timezone

from src.core.shared.time.business_date import business_today


def test_business_today_converts_utc_instant_into_target_timezone() -> None:
    # 2026-01-01 23:30 UTC is already 2026-01-02 in a timezone ahead of UTC.
    now = datetime(2026, 1, 1, 23, 30, tzinfo=timezone.utc)

    assert business_today("UTC", now=now) == date(2026, 1, 1)
    assert business_today("Pacific/Auckland", now=now) == date(2026, 1, 2)


def test_business_today_handles_a_timezone_behind_utc_crossing_midnight() -> None:
    # 2026-01-02 02:00 UTC is still 2026-01-01 in US/Pacific (UTC-8 in January).
    now = datetime(2026, 1, 2, 2, 0, tzinfo=timezone.utc)

    assert business_today("UTC", now=now) == date(2026, 1, 2)
    assert business_today("America/Los_Angeles", now=now) == date(2026, 1, 1)


def test_business_today_resolves_correctly_across_a_dst_transition() -> None:
    # US DST begins 2026-03-08; just after the spring-forward instant the
    # local calendar date must already be 2026-03-08, not the UTC date of
    # whatever instant triggered the check to drift unexpectedly.
    before_transition = datetime(2026, 3, 8, 9, 0, tzinfo=timezone.utc)  # 01:00 PST
    after_transition = datetime(2026, 3, 8, 11, 0, tzinfo=timezone.utc)  # 04:00 PDT

    assert business_today("America/Los_Angeles", now=before_transition) == date(2026, 3, 8)
    assert business_today("America/Los_Angeles", now=after_transition) == date(2026, 3, 8)


def test_business_today_defaults_naive_datetime_to_utc() -> None:
    naive = datetime(2026, 6, 1, 12, 0)

    assert business_today("UTC", now=naive) == date(2026, 6, 1)


def test_business_today_falls_back_to_utc_for_missing_or_unknown_timezone() -> None:
    now = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)

    assert business_today("", now=now) == date(2026, 1, 1)
    assert business_today(None, now=now) == date(2026, 1, 1)
    assert business_today("Not/A_Real_Zone", now=now) == date(2026, 1, 1)


def test_business_today_without_now_uses_the_real_current_instant() -> None:
    result = business_today("UTC")

    assert isinstance(result, date)
    assert result == datetime.now(timezone.utc).date()

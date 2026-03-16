from datetime import datetime, timedelta, timezone


def test_ensure_utc_datetime_treats_naive_values_as_utc() -> None:
    from nonebot_plugin_tetris_stats.utils.timezone import ensure_utc_datetime  # noqa: PLC0415

    aware = datetime(2026, 3, 8, 15, 30, 42, 248129, tzinfo=timezone.utc)
    naive = aware.replace(tzinfo=None)

    assert ensure_utc_datetime(naive) == aware  # noqa: S101
    assert (aware - ensure_utc_datetime(naive)).total_seconds() == 0  # noqa: S101


def test_ensure_utc_datetime_converts_offset_aware_values() -> None:
    from nonebot_plugin_tetris_stats.utils.timezone import ensure_utc_datetime  # noqa: PLC0415

    aware_cst = datetime(2026, 3, 8, 23, 30, 42, 248129, tzinfo=timezone(timedelta(hours=8)))
    expected = datetime(2026, 3, 8, 15, 30, 42, 248129, tzinfo=timezone.utc)

    assert ensure_utc_datetime(aware_cst) == expected  # noqa: S101

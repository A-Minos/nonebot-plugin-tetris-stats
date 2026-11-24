# ruff: noqa: PLC0415
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest


@pytest.mark.parametrize(
    ('values', 'expected'),
    [
        ([21690, 21970], (21690, 21970, 70)),
        ([24800, 24990], (24795, 24995, 50)),
        ([0, 30], (0, 40, 10)),
        ([0, 50], (0, 80, 20)),
        ([24000], (23980, 24020, 10)),
        ([24990, 25000], (24960, 25000, 10)),
    ],
    ids=['exact', 'padded', 'low-tr', 'low-tr-padded', 'flat', 'near-cap'],
)
def test_get_axis_renders_five_ticks(values: list[int | float], expected: tuple[int, int, int]) -> None:
    from nonebot_plugin_tetris_stats.games.tetrio.constant import TR_MAX, TR_MIN
    from nonebot_plugin_tetris_stats.utils.chart import get_axis

    axis = get_axis(values, TR_MAX, TR_MIN)

    assert (axis.value_min, axis.value_max, axis.split_value) == expected  # noqa: S101
    assert axis.value_max - axis.value_min == axis.split_value * 4  # noqa: S101
    assert TR_MIN <= axis.value_min < axis.value_max <= TR_MAX  # noqa: S101


def test_handle_history_data_keeps_window_borders() -> None:
    from nonebot_plugin_tetris_stats.utils.chart import handle_history_data
    from nonebot_plugin_tetris_stats.utils.render.schemas.base import HistoryData

    zero = datetime.now(ZoneInfo('Asia/Shanghai')).replace(hour=0, minute=0, second=0, microsecond=0)
    left_border = zero - timedelta(days=9)
    right_border = zero.replace(microsecond=1000)
    data = [
        HistoryData(score=22000, record_at=left_border - timedelta(days=3)),
        HistoryData(score=22100, record_at=left_border + timedelta(days=2)),
        HistoryData(score=22200, record_at=right_border - timedelta(hours=1)),
        HistoryData(score=22300, record_at=right_border),
    ]

    history = handle_history_data(data)

    assert [i.record_at for i in history] == [left_border, data[1].record_at, data[2].record_at, right_border]  # noqa: S101
    assert history[1:-1] == data[1:3]  # noqa: S101
    assert history[-1].score == data[3].score  # noqa: S101


def test_handle_history_data_flattens_without_points_in_window() -> None:
    from nonebot_plugin_tetris_stats.utils.chart import handle_history_data
    from nonebot_plugin_tetris_stats.utils.render.schemas.base import HistoryData

    zero = datetime.now(ZoneInfo('Asia/Shanghai')).replace(hour=0, minute=0, second=0, microsecond=0)
    left_border = zero - timedelta(days=9)
    right_border = zero.replace(microsecond=1000)
    old_score = 22000

    history = handle_history_data([HistoryData(score=old_score, record_at=left_border - timedelta(days=5))])

    assert [(i.score, i.record_at) for i in history] == [(old_score, left_border), (old_score, right_border)]  # noqa: S101

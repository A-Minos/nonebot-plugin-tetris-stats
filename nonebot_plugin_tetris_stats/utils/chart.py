from bisect import bisect_left
from datetime import datetime, timedelta
from math import ceil, floor, inf
from typing import NamedTuple
from zoneinfo import ZoneInfo

from .exception import WhatTheFuckError
from .render.schemas.base import HistoryData
from .typedefs import Number


class Axis(NamedTuple):
    value_min: int
    value_max: int
    split_value: int


def get_axis(values: list[int | float], max_value: Number = inf, min_value: Number = -inf) -> Axis:
    """把数据范围补成 y 轴的 4 等分, 每段间隔是 10 的整数倍, 前端因此固定渲染 5 个刻度"""
    value_max = 10 * ceil(max(values) / 10)
    value_min = 10 * floor(min(values) / 10)
    span = value_max - value_min
    padding = 40 if not span else -span % 40
    # 上下各补一半, 一侧贴着 min_value/max_value 时把剩余的补到另一侧
    down = min(padding // 2, value_min - min_value)
    down = int(max(down, padding - (max_value - value_max)))
    return Axis(value_min - down, value_max + padding - down, (span + padding) // 4)


def get_specified_point(
    previous_point: HistoryData,
    behind_point: HistoryData,
    point_time: datetime,
) -> HistoryData:
    """根据给出的 previous_point 和 behind_point, 推算 point_time 点处的数据

    Args:
        previous_point (Data): 前面的数据点
        behind_point (Data): 后面的数据点
        point_time (datetime): 要推算的点的位置

    Returns:
        Data: 要推算的点的数据
    """
    # 求两个点的斜率
    slope = (behind_point.score - previous_point.score) / (
        datetime.timestamp(behind_point.record_at) - datetime.timestamp(previous_point.record_at)
    )
    return HistoryData(
        record_at=point_time,
        score=previous_point.score
        + slope * (datetime.timestamp(point_time) - datetime.timestamp(previous_point.record_at)),
    )


def handle_history_data(data: list[HistoryData]) -> list[HistoryData]:
    """裁出以今天零点结束的 10 天窗口, 两端补上正好落在边界上的点

    返回值首尾分别是左边界(9 天前的零点)和右边界(今天零点)上的数据, 中间是窗口内的原始数据
    """
    if not data:
        raise WhatTheFuckError
    data.sort(key=lambda x: x.record_at)

    # 右边界放在今天零点后 1ms, 把今天的数据排除在窗口外, 只用来推算零点处的值
    zero = datetime.now(ZoneInfo('Asia/Shanghai')).replace(hour=0, minute=0, second=0, microsecond=0)
    left_border = zero - timedelta(days=9)
    right_border = zero.replace(microsecond=1000)

    lo = bisect_left(data, left_border, key=lambda i: i.record_at)
    hi = bisect_left(data, right_border, key=lambda i: i.record_at)
    if lo == hi:  # 窗口内没有数据, 用窗口外最近的一个点拉平
        score = data[hi].score if hi < len(data) else data[lo - 1].score
        return [
            HistoryData(score=score, record_at=left_border),
            HistoryData(score=score, record_at=right_border),
        ]

    ret = [
        get_specified_point(data[lo - 1], data[lo], left_border)
        if lo
        else HistoryData(score=data[lo].score, record_at=left_border)
    ]
    ret.extend(data[lo:hi])
    ret.append(
        get_specified_point(data[hi - 1], data[hi], right_border)
        if hi < len(data)
        else HistoryData(score=data[hi - 1].score, record_at=right_border)
    )
    return ret

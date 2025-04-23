from datetime import datetime, timedelta
from math import ceil, floor, inf
from typing import NamedTuple
from zoneinfo import ZoneInfo

from .exception import WhatTheFuckError
from .render.schemas.base import HistoryData
from .typedefs import Number


class ValueBound(NamedTuple):
    value_max: int
    value_min: int


class Split(NamedTuple):
    split_value: int
    offset: int


def get_value_bounds(values: list[int | float]) -> ValueBound:
    value_max = 10 * ceil(max(values) / 10)
    value_min = 10 * floor(min(values) / 10)
    return ValueBound(value_max, value_min)


def get_split(value_bound: ValueBound, max_value: Number = inf, min_value: Number = -inf) -> Split:
    offset = 0
    overflow = 0

    while True:
        if (new_max_value := value_bound.value_max + offset + overflow) > max_value:
            overflow -= 1
            continue
        if (new_min_value := value_bound.value_min - offset + overflow) < min_value:
            overflow += 1
            continue
        if ((new_max_value - new_min_value) / 40).is_integer():
            split_value = int((value_bound.value_max + offset - (value_bound.value_min - offset)) / 4)
            break
        offset += 1
    return Split(split_value, offset + overflow)


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


def handle_history_data(data: list[HistoryData]) -> list[HistoryData]:  # noqa: C901, PLR0912
    # 按照 记录时间 对数据进行排序
    data.sort(key=lambda x: x.record_at)

    # 定义时间边界, 右边界为当前时间的当天零点, 左边界为右边界前推9天
    # 返回值的[0]和[-1]分别应满足left_border和right_border
    zero = datetime.now(ZoneInfo('Asia/Shanghai')).replace(hour=0, minute=0, second=0, microsecond=0)
    left_border = zero - timedelta(days=9)
    right_border = zero.replace(microsecond=1000)

    lefts: list[HistoryData] = []
    in_border: list[HistoryData] = []
    rights: list[HistoryData] = []

    # 根据 记录时间 将数据分类到对应的列表中
    for i in data:
        if i.record_at < left_border:
            lefts.append(i)
        elif i.record_at < right_border:
            in_border.append(i)
        else:
            rights.append(i)

    ret: list[HistoryData] = []

    # 处理左边界的点
    if lefts and in_border:  # 如果边界左侧和边界内都有值则推算
        ret.append(get_specified_point(lefts[-1], in_border[0], left_border))
    elif lefts and not in_border:  # 如果边界左侧有值但是边界内没有值则直接取左侧的最后一个值
        ret.append(HistoryData(score=lefts[-1].score, record_at=left_border))
    elif not lefts and in_border:  # 如果边界左侧没有值但是边界内有值则直接取边界内的第一个值
        ret.append(HistoryData(score=in_border[0].score, record_at=left_border))
    elif not lefts and not in_border and rights:  # 如果边界左侧和边界内都没有值但是边界右侧有值则直接取边界右侧的第一个值 # fmt: skip
        ret.append(HistoryData(score=rights[0].score, record_at=left_border))
    else:  # 暂时没想到其他情况
        raise WhatTheFuckError

    # 添加边界内数据
    ret.extend(in_border)

    # 处理右边界的点
    if in_border and rights:  # 如果边界内和边界右侧都有值则推算
        ret.append(get_specified_point(in_border[-1], rights[0], right_border))
    elif not in_border and rights:  # 如果边界内没有值但是边界右侧有值则直接取右侧的第一个值
        ret.append(HistoryData(score=rights[0].score, record_at=right_border))
    elif in_border and not rights:  # 如果边界内有值但是边界右侧没有值则直接取边界内的最后一个值
        ret.append(HistoryData(score=in_border[-1].score, record_at=right_border))
    elif not in_border and not rights and lefts:  # 如果边界内和边界右侧都没有值但是边界左侧有值则直接取边界左侧的最后一个值 # fmt: skip
        ret.append(HistoryData(score=lefts[-1].score, record_at=right_border))
    else:  # 暂时没想到其他情况
        raise WhatTheFuckError
    return ret

from asyncio import gather
from datetime import datetime, timedelta
from hashlib import md5
from math import ceil, floor
from zoneinfo import ZoneInfo

from yarl import URL

from ....utils.exception import FallbackError, WhatTheFuckError
from ....utils.host import HostPage, get_self_netloc
from ....utils.render import render
from ....utils.render.schemas.base import Avatar, Ranking
from ....utils.render.schemas.tetrio.user.base import TetraLeagueHistoryData
from ....utils.render.schemas.tetrio.user.info_v1 import Info, Radar, TetraLeague, TetraLeagueHistory, User
from ....utils.screenshot import screenshot
from ..api import Player
from ..api.schemas.summaries.league import RatedData
from ..constant import TR_MAX, TR_MIN
from .tools import flow_to_history, get_league_data


def get_value_bounds(values: list[int | float]) -> tuple[int, int]:
    value_max = 10 * ceil(max(values) / 10)
    value_min = 10 * floor(min(values) / 10)
    return value_max, value_min


def get_split(value_max: int, value_min: int) -> tuple[int, int]:
    offset = 0
    overflow = 0

    while True:
        if (new_max_value := value_max + offset + overflow) > TR_MAX:
            overflow -= 1
            continue
        if (new_min_value := value_min - offset + overflow) < TR_MIN:
            overflow += 1
            continue
        if ((new_max_value - new_min_value) / 40).is_integer():
            split_value = int((value_max + offset - (value_min - offset)) / 4)
            break
        offset += 1
    return split_value, offset + overflow


def get_specified_point(
    previous_point: TetraLeagueHistoryData,
    behind_point: TetraLeagueHistoryData,
    point_time: datetime,
) -> TetraLeagueHistoryData:
    """根据给出的 previous_point 和 behind_point, 推算 point_time 点处的数据

    Args:
        previous_point (Data): 前面的数据点
        behind_point (Data): 后面的数据点
        point_time (datetime): 要推算的点的位置

    Returns:
        Data: 要推算的点的数据
    """
    # 求两个点的斜率
    slope = (behind_point.tr - previous_point.tr) / (
        datetime.timestamp(behind_point.record_at) - datetime.timestamp(previous_point.record_at)
    )
    return TetraLeagueHistoryData(
        record_at=point_time,
        tr=previous_point.tr + slope * (datetime.timestamp(point_time) - datetime.timestamp(previous_point.record_at)),
    )


def handle_history_data(data: list[TetraLeagueHistoryData]) -> list[TetraLeagueHistoryData]:  # noqa: C901, PLR0912
    # 按照 记录时间 对数据进行排序
    data.sort(key=lambda x: x.record_at)

    # 定义时间边界, 右边界为当前时间的当天零点, 左边界为右边界前推9天
    # 返回值的[0]和[-1]分别应满足left_border和right_border
    zero = datetime.now(ZoneInfo('Asia/Shanghai')).replace(hour=0, minute=0, second=0, microsecond=0)
    left_border = zero - timedelta(days=9)
    right_border = zero.replace(microsecond=1000)

    lefts: list[TetraLeagueHistoryData] = []
    in_border: list[TetraLeagueHistoryData] = []
    rights: list[TetraLeagueHistoryData] = []

    # 根据 记录时间 将数据分类到对应的列表中
    for i in data:
        if i.record_at < left_border:
            lefts.append(i)
        elif i.record_at < right_border:
            in_border.append(i)
        else:
            rights.append(i)

    ret: list[TetraLeagueHistoryData] = []

    # 处理左边界的点
    if lefts and in_border:  # 如果边界左侧和边界内都有值则推算
        ret.append(get_specified_point(lefts[-1], in_border[0], left_border))
    elif lefts and not in_border:  # 如果边界左侧有值但是边界内没有值则直接取左侧的最后一个值
        ret.append(TetraLeagueHistoryData(tr=lefts[-1].tr, record_at=left_border))
    elif not lefts and in_border:  # 如果边界左侧没有值但是边界内有值则直接取边界内的第一个值
        ret.append(TetraLeagueHistoryData(tr=in_border[0].tr, record_at=left_border))
    elif not lefts and not in_border and rights:  # 如果边界左侧和边界内都没有值但是边界右侧有值则直接取边界右侧的第一个值 # fmt: skip
        ret.append(TetraLeagueHistoryData(tr=rights[0].tr, record_at=left_border))
    else:  # 暂时没想到其他情况
        raise WhatTheFuckError

    # 添加边界内数据
    ret.extend(in_border)

    # 处理右边界的点
    if in_border and rights:  # 如果边界内和边界右侧都有值则推算
        ret.append(get_specified_point(in_border[-1], rights[0], right_border))
    elif not in_border and rights:  # 如果边界内没有值但是边界右侧有值则直接取右侧的第一个值
        ret.append(TetraLeagueHistoryData(tr=rights[0].tr, record_at=right_border))
    elif in_border and not rights:  # 如果边界内有值但是边界右侧没有值则直接取边界内的最后一个值
        ret.append(TetraLeagueHistoryData(tr=in_border[-1].tr, record_at=right_border))
    elif not in_border and not rights and lefts:  # 如果边界内和边界右侧都没有值但是边界左侧有值则直接取边界左侧的最后一个值 # fmt: skip
        ret.append(TetraLeagueHistoryData(tr=lefts[-1].tr, record_at=right_border))
    else:  # 暂时没想到其他情况
        raise WhatTheFuckError
    return ret


async def make_query_image_v1(player: Player) -> bytes:
    (
        (user, user_info, league, sprint, blitz, leagueflow),
        (avatar_revision,),
    ) = await gather(
        gather(player.user, player.get_info(), player.league, player.sprint, player.blitz, player.get_leagueflow()),
        gather(player.avatar_revision),
    )
    league_data = get_league_data(league, RatedData)
    if league_data.vs is None:
        raise FallbackError
    histories = flow_to_history(leagueflow, handle_history_data)
    value_max, value_min = get_value_bounds([i.tr for i in histories])
    split_value, offset = get_split(value_max, value_min)
    if sprint.data.record is not None:
        duration = timedelta(milliseconds=sprint.data.record.results.stats.finaltime).total_seconds()
        sprint_value = f'{duration:.3f}s' if duration < 60 else f'{duration // 60:.0f}m {duration % 60:.3f}s'  # noqa: PLR2004
    else:
        sprint_value = 'N/A'
    blitz_value = f'{blitz.data.record.results.stats.score:,}' if blitz.data.record is not None else 'N/A'
    netloc = get_self_netloc()
    async with HostPage(
        page=await render(
            'v1/tetrio/info',
            Info(
                user=User(
                    avatar=str(
                        URL(f'http://{netloc}/host/resource/tetrio/avatars/{user.ID}') % {'revision': avatar_revision}
                    )
                    if avatar_revision is not None and avatar_revision != 0
                    else Avatar(
                        type='identicon',
                        hash=md5(user.ID.encode()).hexdigest(),  # noqa: S324
                    ),
                    name=user.name.upper(),
                    bio=user_info.data.bio,
                ),
                ranking=Ranking(
                    rating=round(league_data.glicko, 2),
                    rd=round(league_data.rd, 2),
                ),
                tetra_league=TetraLeague(
                    rank=league_data.rank,
                    tr=round(league_data.tr, 2),
                    global_rank=league_data.standing,
                    pps=league_data.pps,
                    lpm=round(lpm := (league_data.pps * 24), 2),
                    apm=league_data.apm,
                    apl=round(league_data.apm / lpm, 2),
                    vs=league_data.vs,
                    adpm=round(adpm := (league_data.vs * 0.6), 2),
                    adpl=round(adpm / lpm, 2),
                ),
                tetra_league_history=TetraLeagueHistory(
                    data=histories,
                    split_interval=split_value,
                    min_tr=value_min,
                    max_tr=value_max,
                    offset=offset,
                ),
                radar=Radar(
                    app=(app := (league_data.apm / (60 * league_data.pps))),
                    dsps=(dsps := ((league_data.vs / 100) - (league_data.apm / 60))),
                    dspp=(dspp := (dsps / league_data.pps)),
                    ci=150 * dspp - 125 * app + 50 * (league_data.vs / league_data.apm) - 25,
                    ge=2 * ((app * dsps) / league_data.pps),
                ),
                sprint=sprint_value,
                blitz=blitz_value,
            ),
        )
    ) as page_hash:
        return await screenshot(f'http://{netloc}/host/{page_hash}.html')

from collections import defaultdict
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from hashlib import sha512
from math import floor
from statistics import mean
from typing import TYPE_CHECKING

from aiofiles import open
from nonebot import get_driver
from nonebot.compat import model_dump
from nonebot.utils import run_sync
from nonebot_plugin_apscheduler import scheduler
from nonebot_plugin_localstore import get_data_file
from nonebot_plugin_orm import get_session
from sqlalchemy import select
from zstandard import ZstdCompressor

from ....utils.exception import RequestError
from ....utils.retry import retry
from ..api.schemas.base import FailedModel
from ..api.schemas.tetra_league import ValidUser
from ..api.schemas.user import User
from ..api.tetra_league import full_export
from ..constant import RANK_PERCENTILE
from ..models import IORank

if TYPE_CHECKING:
    from ..api.typing import Rank

UTC = timezone.utc

driver = get_driver()


@scheduler.scheduled_job('cron', hour='0,6,12,18', minute=0)
@retry(exception_type=RequestError, delay=timedelta(minutes=15))
async def get_tetra_league_data() -> None:
    league, original = await full_export(with_original=True)
    if isinstance(league, FailedModel):
        msg = f'排行榜数据请求错误:\n{league.error}'
        raise RequestError(msg)

    def pps(user: ValidUser) -> float:
        return user.league.pps

    def apm(user: ValidUser) -> float:
        return user.league.apm

    def vs(user: ValidUser) -> float:
        return user.league.vs

    def _min(users: list[ValidUser], field: Callable[[ValidUser], float]) -> ValidUser:
        return min(users, key=field)

    def _max(users: list[ValidUser], field: Callable[[ValidUser], float]) -> ValidUser:
        return max(users, key=field)

    def build_extremes_data(
        users: list[ValidUser],
        field: Callable[[ValidUser], float],
        sort: Callable[[list[ValidUser], Callable[[ValidUser], float]], ValidUser],
    ) -> tuple[dict[str, str], float]:
        user = sort(users, field)
        return model_dump(User(ID=user.id, name=user.username)), field(user)

    data_hash: str | None = await run_sync((await run_sync(sha512)(original)).hexdigest)()
    async with open(get_data_file('nonebot_plugin_tetris_stats', f'{data_hash}.json.zst'), mode='wb') as file:
        await file.write(await run_sync(ZstdCompressor(level=12, threads=-1).compress)(original))

    users = [i for i in league.data.users if isinstance(i, ValidUser)]
    rank_to_users: defaultdict[Rank, list[ValidUser]] = defaultdict(list)
    for i in users:
        rank_to_users[i.league.rank].append(i)
    rank_info: list[IORank] = []
    for rank, percentile in RANK_PERCENTILE.items():
        offset = floor((percentile / 100) * len(users)) - 1
        tr_line = users[offset].league.rating
        rank_users = rank_to_users[rank]
        rank_info.append(
            IORank(
                rank=rank,
                tr_line=tr_line,
                player_count=len(rank_users),
                low_pps=(build_extremes_data(rank_users, pps, _min)),
                low_apm=(build_extremes_data(rank_users, apm, _min)),
                low_vs=(build_extremes_data(rank_users, vs, _min)),
                avg_pps=mean({i.league.pps for i in rank_users}),
                avg_apm=mean({i.league.apm for i in rank_users}),
                avg_vs=mean({i.league.vs for i in rank_users}),
                high_pps=(build_extremes_data(rank_users, pps, _max)),
                high_apm=(build_extremes_data(rank_users, apm, _max)),
                high_vs=(build_extremes_data(rank_users, vs, _max)),
                update_time=league.cache.cached_at,
                file_hash=data_hash,
            )
        )
    async with get_session() as session:
        session.add_all(rank_info)
        await session.commit()


@driver.on_startup
async def _() -> None:
    async with get_session() as session:
        latest_time = await session.scalar(select(IORank.update_time).order_by(IORank.id.desc()).limit(1))
    if latest_time is None or datetime.now(tz=UTC) - latest_time.replace(tzinfo=UTC) > timedelta(hours=6):
        await get_tetra_league_data()


from . import all, detail  # noqa: E402

__all__ = ['all', 'detail']

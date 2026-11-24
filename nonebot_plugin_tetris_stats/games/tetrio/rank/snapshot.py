from dataclasses import dataclass
from typing import NamedTuple
from weakref import WeakKeyDictionary

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ....i18n import Lang
from ....utils.metrics import get_metrics
from ..api.schemas.leaderboards.by import Entry
from ..api.typedefs import Rank
from ..exception import LeagueSnapshotNotFoundError
from ..models import TETRIOLeagueStats
from ..typedefs import ListSort


@dataclass(frozen=True)
class LeagueListQuery:
    sort: ListSort = 'league'
    max_tr: float | None = None
    min_tr: float | None = None
    limit: int = 25
    country: str | None = None


class LeagueListEntry(NamedTuple):
    """列表渲染用到的字段, 不用为每条记录保留整个 Entry"""

    id: str
    username: str
    country: str | None
    xp: float
    rank: Rank
    tr: float
    glicko: float
    rd: float
    decaying: bool
    pps: float
    apm: float
    vs: float

    @classmethod
    def from_entry(cls, entry: Entry) -> 'LeagueListEntry':
        league = entry.league
        return cls(
            id=entry.id,
            username=entry.username,
            country=entry.country,
            xp=entry.xp,
            rank=league.rank,
            tr=league.tr,
            glicko=league.glicko,
            rd=league.rd,
            decaying=league.decaying,
            pps=league.pps,
            apm=league.apm,
            vs=league.vs,
        )


# 快照写入后不再变化, 按 (数据库, 快照 id) 缓存投影, 命中时省掉整份快照的读入和校验
_snapshot_cache: WeakKeyDictionary[object, tuple[int, list[LeagueListEntry]]] = WeakKeyDictionary()


async def query_league_list(session: AsyncSession, query: LeagueListQuery) -> list[LeagueListEntry]:
    """Read and rank players from the latest persisted league snapshot."""
    latest_id = await session.scalar(select(TETRIOLeagueStats.id).order_by(TETRIOLeagueStats.id.desc()).limit(1))
    if latest_id is None:
        raise LeagueSnapshotNotFoundError(Lang.list.no_snapshot())

    engine = session.bind
    if engine is not None and (cached := _snapshot_cache.get(engine)) is not None and cached[0] == latest_id:
        snapshot_entries = cached[1]
    else:
        snapshot = (
            await session.scalars(
                select(TETRIOLeagueStats)
                .where(TETRIOLeagueStats.id == latest_id)
                .options(selectinload(TETRIOLeagueStats.raw))
            )
        ).one()
        if not snapshot.raw:
            raise LeagueSnapshotNotFoundError(Lang.list.no_snapshot())
        snapshot_entries = [
            LeagueListEntry.from_entry(entry)
            for historical in sorted(snapshot.raw, key=lambda item: item.id)
            for entry in historical.data.data.entries
            if isinstance(entry, Entry)
        ]
        if engine is not None:
            _snapshot_cache[engine] = (latest_id, snapshot_entries)

    country = query.country.upper() if query.country is not None else None
    entries = [
        entry
        for entry in snapshot_entries
        if (query.max_tr is None or entry.tr <= query.max_tr)
        and (query.min_tr is None or entry.tr >= query.min_tr)
        and (country is None or entry.country == country)
    ]

    # League order is the deterministic tie-breaker for every metric.
    entries.sort(key=lambda entry: entry.tr, reverse=True)
    sort = query.sort
    if sort == 'league':
        if query.min_tr is not None:
            return entries[-query.limit :] if query.limit else []
        return entries[: query.limit]

    ranked_entries: list[tuple[float | int, LeagueListEntry]] = []
    for entry in entries:
        if sort in ('apl', 'adpl') and not entry.pps:
            continue

        metrics = get_metrics(pps=entry.pps, apm=entry.apm, vs=entry.vs)
        metric = {
            'pps': metrics.pps,
            'apm': metrics.apm,
            'adpm': metrics.adpm,
            'apl': metrics.apl,
            'adpl': metrics.adpl,
        }[sort]
        ranked_entries.append((metric, entry))
    ranked_entries.sort(key=lambda ranked_entry: ranked_entry[0], reverse=True)
    return [entry for _, entry in ranked_entries[: query.limit]]

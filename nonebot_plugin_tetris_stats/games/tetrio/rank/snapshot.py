from dataclasses import dataclass
from typing import Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ....i18n import Lang
from ....utils.exception import NeedCatchError
from ....utils.metrics import get_metrics
from ..api.schemas.leaderboards.by import Entry
from ..models import TETRIOLeagueStats

ListSort = Literal['league', 'pps', 'apm', 'adpm', 'apl', 'adpl']


class LeagueSnapshotNotFoundError(NeedCatchError):
    """No persisted TETR.IO league snapshot is available."""


@dataclass(frozen=True)
class LeagueListQuery:
    sort: ListSort = 'league'
    max_tr: float | None = None
    min_tr: float | None = None
    limit: int = 25
    country: str | None = None


def _metric(entry: Entry, sort: ListSort) -> float | int | None:
    league = entry.league
    if sort == 'league':
        return round(league.tr, 2)
    if sort in ('apl', 'adpl') and not league.pps:
        return None

    metrics = get_metrics(pps=league.pps, apm=league.apm, vs=league.vs)
    return {
        'pps': metrics.pps,
        'apm': metrics.apm,
        'adpm': metrics.adpm,
        'apl': metrics.apl,
        'adpl': metrics.adpl,
    }[sort]


async def query_league_list(session: AsyncSession, query: LeagueListQuery) -> list[Entry]:
    """Read and rank players from the latest persisted league snapshot."""
    latest = (
        await session.scalars(
            select(TETRIOLeagueStats)
            .order_by(TETRIOLeagueStats.id.desc())
            .limit(1)
            .options(selectinload(TETRIOLeagueStats.raw))
        )
    ).one_or_none()
    if latest is None or not latest.raw:
        raise LeagueSnapshotNotFoundError(Lang.list.no_snapshot())

    country = query.country.upper() if query.country is not None else None
    entries = [
        entry
        for historical in sorted(latest.raw, key=lambda item: item.id)
        for entry in historical.data.data.entries
        if isinstance(entry, Entry)
        and (query.max_tr is None or entry.league.tr <= query.max_tr)
        and (query.min_tr is None or entry.league.tr >= query.min_tr)
        and (country is None or entry.country == country)
    ]

    # League order is the deterministic tie-breaker for every metric.
    entries.sort(key=lambda entry: entry.league.tr, reverse=True)
    if query.sort == 'league':
        if query.min_tr is not None:
            return entries[-query.limit :] if query.limit else []
        return entries[: query.limit]

    ranked_entries: list[tuple[float | int, Entry]] = []
    for entry in entries:
        metric = _metric(entry, query.sort)
        if metric is not None:
            ranked_entries.append((metric, entry))
    ranked_entries.sort(key=lambda ranked_entry: ranked_entry[0], reverse=True)
    return [entry for _, entry in ranked_entries[: query.limit]]


__all__ = [
    'LeagueListQuery',
    'LeagueSnapshotNotFoundError',
    'ListSort',
    'query_league_list',
]

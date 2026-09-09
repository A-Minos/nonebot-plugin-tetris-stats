from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ....i18n import Lang
from ....utils.metrics import get_metrics
from ..api.schemas.leaderboards.by import Entry
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
    sort = query.sort
    if sort == 'league':
        if query.min_tr is not None:
            return entries[-query.limit :] if query.limit else []
        return entries[: query.limit]

    ranked_entries: list[tuple[float | int, Entry]] = []
    for entry in entries:
        league = entry.league
        if sort in ('apl', 'adpl') and not league.pps:
            continue

        metrics = get_metrics(pps=league.pps, apm=league.apm, vs=league.vs)
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

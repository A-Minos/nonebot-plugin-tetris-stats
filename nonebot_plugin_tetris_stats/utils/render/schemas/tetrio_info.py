from datetime import datetime
from typing import Annotated, ClassVar

from nonebot.compat import PYDANTIC_V2
from pydantic import BaseModel

from ....games.tetrio.api.typing import Rank
from ...typing import Number
from .base import People

if PYDANTIC_V2:
    from pydantic import PlainSerializer


def format_datetime_to_timestamp(dt: datetime) -> int:
    return int(dt.timestamp() * 1000)


class User(People):
    bio: str | None


class Ranking(BaseModel):
    rating: Number
    rd: Number


class TetraLeague(BaseModel):
    rank: Rank
    tr: Number
    global_rank: Number
    pps: Number
    lpm: Number
    apm: Number
    apl: Number
    vs: Number
    adpm: Number
    adpl: Number


class Data(BaseModel):
    if PYDANTIC_V2:
        record_at: Annotated[datetime, PlainSerializer(format_datetime_to_timestamp, return_type=int)]
    else:
        record_at: datetime  # type: ignore[no-redef]
    tr: Number


class TetraLeagueHistory(BaseModel):
    data: list[Data]
    split_interval: Number
    min_tr: Number
    max_tr: Number
    offset: Number


class Radar(BaseModel):
    app: Number
    dsps: Number
    dspp: Number
    ci: Number
    ge: Number


class TETRIOInfo(BaseModel):
    user: User
    ranking: Ranking
    tetra_league: TetraLeague
    tetra_league_history: TetraLeagueHistory
    radar: Radar
    sprint: str
    blitz: str

    if not PYDANTIC_V2:

        class Config:
            json_encoders: ClassVar[dict] = {datetime: format_datetime_to_timestamp}

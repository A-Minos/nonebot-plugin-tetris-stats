from datetime import datetime
from typing import Literal, Self, overload

from jinja2 import Environment, FileSystemLoader
from nonebot.compat import PYDANTIC_V2, model_dump
from pydantic import BaseModel

from ..game_data_processor.io_data_processor.typing import Rank
from .templates import templates_dir
from .typing import Number

if PYDANTIC_V2:
    from pydantic import field_validator
else:
    from pydantic import validator as field_validator  # type: ignore[no-redef]

env = Environment(
    loader=FileSystemLoader(templates_dir), autoescape=True, trim_blocks=True, lstrip_blocks=True, enable_async=True
)


class TimestampDatetime(datetime):
    def __str__(self) -> str:
        return str(int(self.timestamp() * 1000))

    def __repr__(self) -> str:
        return self.__str__()

    @classmethod
    def from_datetime(cls, dt: datetime) -> Self:
        return cls(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second, dt.microsecond, dt.tzinfo, fold=dt.fold)


class Bind(BaseModel):
    class People(BaseModel):
        avatar: str
        name: str

    platform: Literal['TETR.IO', 'TOP', 'TOS']
    status: Literal['error', 'success', 'unknown', 'unlink', 'unverified']
    user: People
    bot: People
    command: str


class TETRIOInfo(BaseModel):
    class User(BaseModel):
        avatar: str
        name: str
        id: str
        sign: str | None

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

    class TetraLeagueHistory(BaseModel):
        class Data(BaseModel):
            record_at: datetime
            tr: Number

            @field_validator('record_at')
            @classmethod
            def _(cls, value: datetime) -> TimestampDatetime:
                return TimestampDatetime.from_datetime(value)

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

    user: User
    ranking: Ranking
    tetra_league: TetraLeague
    tetra_league_history: TetraLeagueHistory
    radar: Radar
    sprint: str
    blitz: str


@overload
async def render(render_type: Literal['binding'], data: Bind) -> str: ...


@overload
async def render(render_type: Literal['tetrio/info'], data: TETRIOInfo) -> str: ...


async def render(render_type: Literal['binding', 'tetrio/info'], data: Bind | TETRIOInfo) -> str:
    return await env.get_template('index.html').render_async(path=render_type, data=data.model_dump_json())

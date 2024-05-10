from datetime import datetime
from typing import Annotated, ClassVar, Literal, overload

from jinja2 import Environment, FileSystemLoader
from nonebot.compat import PYDANTIC_V2
from pydantic import BaseModel

from ..game_data_processor.io_data_processor.typing import Rank
from .templates import templates_dir
from .typing import Number

if PYDANTIC_V2:
    from pydantic import PlainSerializer

env = Environment(
    loader=FileSystemLoader(templates_dir), autoescape=True, trim_blocks=True, lstrip_blocks=True, enable_async=True
)


def format_datetime_to_timestamp(dt: datetime) -> int:
    return int(dt.timestamp() * 1000)


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

    class TetraLeagueHistory(BaseModel):
        class Data(BaseModel):
            if PYDANTIC_V2:
                record_at: Annotated[datetime, PlainSerializer(format_datetime_to_timestamp, return_type=int)]
            else:
                record_at: datetime  # type: ignore[no-redef]
            tr: Number

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

    if not PYDANTIC_V2:

        class Config:
            json_encoders: ClassVar[dict] = {datetime: format_datetime_to_timestamp}


@overload
async def render(render_type: Literal['binding'], data: Bind) -> str: ...


@overload
async def render(render_type: Literal['tetrio/info'], data: TETRIOInfo) -> str: ...


async def render(render_type: Literal['binding', 'tetrio/info'], data: Bind | TETRIOInfo) -> str:
    if PYDANTIC_V2:
        return await env.get_template('index.html').render_async(path=render_type, data=data.model_dump_json())
    return await env.get_template('index.html').render_async(path=render_type, data=data.json())

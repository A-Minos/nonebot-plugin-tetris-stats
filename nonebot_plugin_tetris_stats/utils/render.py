from typing import Any, Literal, overload

from jinja2 import Environment, FileSystemLoader

from ..game_data_processor.io_data_processor.typing import Rank
from ..templates import path
from .typing import GameType

Bind = Literal['bind.j2.html']
Data = Literal['data.j2.html']

env = Environment(
    loader=FileSystemLoader(path), autoescape=True, trim_blocks=True, lstrip_blocks=True, enable_async=True
)


@overload
async def render(
    template: Bind,
    *,
    user_avatar: str,
    state: Literal['error', 'success', 'unknown', 'unlink', 'unverified'],
    bot_avatar: str,
    game_type: GameType,
    user_name: str,
    bot_name: str,
    command: str,
) -> str: ...


@overload
async def render(
    template: Data,
    *,
    user_avatar: str,
    user_name: str,
    user_sign: str | None,
    game_type: Literal['TETR.IO'],
    ranking: str | float,
    rd: str | float,
    rank: Rank,
    TR: str | float,  # noqa: N803
    global_rank: str | int,
    lpm: str | float,
    pps: str | float,
    apm: str | float,
    apl: str | float,
    adpm: str | float,
    adpl: str | float,
    vs: str | float,
    sprint: str,
    blitz: str,
    data: list[list[int]],
    split_value: int,
    value_max: int,
    value_min: int,
    offset: int,
    app: str | float,
    dsps: str | float,
    dspp: str | float,
    ci: str | float,
    ge: str | float,
) -> str: ...


async def render(template: Bind | Data, **kwargs: Any) -> str:
    if kwargs['game_type'] == 'IO':
        kwargs['game_type'] = 'TETR.IO'
    return await env.get_template(template).render_async(**kwargs)

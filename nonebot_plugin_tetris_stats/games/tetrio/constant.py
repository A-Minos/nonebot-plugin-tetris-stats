from re import compile  # noqa: A004
from typing import Literal

from yarl import URL

from .api.typedefs import ValidRank

GAME_TYPE: Literal['IO'] = 'IO'

BASE_URL = URL('https://ch.tetr.io/api/')

RANK_PERCENTILE: dict[ValidRank, float] = {
    'x+': 0.2,
    'x': 1,
    'u': 5,
    'ss': 11,
    's+': 17,
    's': 23,
    's-': 30,
    'a+': 38,
    'a': 46,
    'a-': 54,
    'b+': 62,
    'b': 70,
    'b-': 78,
    'c+': 84,
    'c': 90,
    'c-': 95,
    'd+': 97.5,
    'd': 100,
}

TR_MIN = 0
TR_MAX = 25000

USER_ID = compile(r'^[a-f0-9]{24}$')
USER_NAME = compile(r'^[a-zA-Z0-9_-]{3,16}$')

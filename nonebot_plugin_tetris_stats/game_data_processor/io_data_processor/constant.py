from typing import Literal

from .typing import Rank

GAME_TYPE: Literal['IO'] = 'IO'
BASE_URL = 'https://ch.tetr.io/api/'
RANK_PERCENTILE: dict[Rank, float] = {
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

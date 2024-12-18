from re import compile  # noqa: A004
from typing import Literal

from yarl import URL

GAME_TYPE: Literal['TOP'] = 'TOP'

BASE_URL = URL('http://tetrisonline.pl/top/')

USER_NAME = compile(r'^[a-zA-Z0-9_]{1,16}$')

from re import compile
from typing import Literal

GAME_TYPE: Literal['TOP'] = 'TOP'

BASE_URL = 'http://tetrisonline.pl/top/'

USER_NAME = compile(r'^[a-zA-Z0-9_]{1,16}$')

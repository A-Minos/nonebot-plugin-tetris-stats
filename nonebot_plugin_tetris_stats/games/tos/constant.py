from re import compile  # noqa: A004
from typing import Literal

from yarl import URL

GAME_TYPE: Literal['TOS'] = 'TOS'

BASE_URL = {
    URL('https://teatube.cn:8888/'),
    URL('http://cafuuchino1.studio26f.org:19970'),
}

USER_NAME = compile(
    r'^(?!\.)(?!com[0-9]$)(?!con$)(?!lpt[0-9]$)(?!nul$)(?!prn$)[^\-][^\+][^\|\*\?\\\s\!:<>/$"]*[^\.\|\*\?\\\s\!:<>/$"]+$'
)

from re import compile
from typing import Literal

GAME_TYPE: Literal['TOS'] = 'TOS'

BASE_URL = {
    'https://teatube.cn:8888/',
    'http://cafuuchino1.studio26f.org:19970',
    'http://cafuuchino2.studio26f.org:19970',
    'http://cafuuchino3.studio26f.org:19970',
    'http://cafuuchino4.studio26f.org:19970',
}

USER_NAME = compile(
    r'^(?!\.)(?!com[0-9]$)(?!con$)(?!lpt[0-9]$)(?!nul$)(?!prn$)[^\-][^\+][^\|\*\?\\\s\!:<>/$"]*[^\.\|\*\?\\\s\!:<>/$"]+$'
)

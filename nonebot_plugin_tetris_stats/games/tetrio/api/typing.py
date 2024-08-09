from typing import Literal

ValidRank = Literal[
    'x',
    'u',
    'ss',
    's+',
    's',
    's-',
    'a+',
    'a',
    'a-',
    'b+',
    'b',
    'b-',
    'c+',
    'c',
    'c-',
    'd+',
    'd',
]

Rank = ValidRank | Literal['z']  # 未定级

Summaries = Literal[
    '40l',
    'blitz',
    'zenith',
    'zenithex',
    # 'league',  # 等待正式赛季开始
    'zen',
    'achievements',
]

Records = Literal[
    '40l_top',
    '40l_recent',
    '40l_progression',
    'blitz_top',
    'blitz_recent',
    'blitz_progression',
]

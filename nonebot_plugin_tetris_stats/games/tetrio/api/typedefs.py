from typing import Literal, NewType

S1ValidRank = Literal[
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
S1Rank = S1ValidRank | Literal['z']

ValidRank = Literal['x+'] | S1ValidRank
Rank = ValidRank | Literal['z']  # 未定级

Summaries = Literal[
    '40l',
    'blitz',
    'zenith',
    'zenithex',
    'league',
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

Prisecter = NewType('Prisecter', str)

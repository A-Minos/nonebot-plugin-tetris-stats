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

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class UserProfile(BaseModel):
    class Data(BaseModel):
        idmultiplayergameresult: int
        iduser: str
        teaid: str
        time: int
        clear_lines: int
        attack: int
        send: int
        offset: int
        receive: int
        rise: int
        dig: int
        pieces: int
        max_combo: int
        pc_count: int
        place: int
        num_players: int
        fumen_code: Literal['0', '1']  # wtf
        rule_set: str
        garbage: str
        idmultiplayergame: int
        datetime: datetime

    code: int
    success: bool
    data: list[Data]

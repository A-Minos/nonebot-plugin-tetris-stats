from datetime import datetime
from typing import Literal
from zoneinfo import ZoneInfo

from nonebot.adapters.onebot.v11 import GroupMessageEvent
from nonebot.adapters.onebot.v11.event import Sender
from pydantic import Field


class FakeGroupMessageEvent(GroupMessageEvent):
    time: int = Field(default_factory=lambda: int(datetime.now(tz=ZoneInfo('Asia/Shanghai')).timestamp()))
    self_id: int = 1
    post_type: Literal['message'] = 'message'
    sub_type: str = 'normal'
    user_id: int = 10
    message_type: Literal['group'] = 'group'
    group_id: int = 10000
    message_id: int = 1
    font: int = 0
    sender: Sender = Sender(
        card='',
        nickname='test',
        role='member',
    )
    to_me: bool = False

    class Config:
        extra = 'allow'

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from .base import ArCounts, FailedModel
from .base import SuccessModel as BaseSuccessModel


class Badge(BaseModel):
    id: str
    label: str
    group: str | None = None
    ts: datetime | Literal[False] | None = None


class Connection(BaseModel):
    id: str
    username: str
    display_username: str


class Connections(BaseModel):
    discord: Connection | None = None
    twitch: Connection | None = None
    twitter: Connection | None = None
    reddit: Connection | None = None
    youtube: Connection | None = None
    steam: Connection | None = None


class Distinguishment(BaseModel):
    type: str


class Data(BaseModel):
    id: str = Field(default=..., alias='_id')
    username: str
    role: Literal['anon', 'user', 'bot', 'halfmod', 'mod', 'admin', 'sysop', 'hidden', 'banned']
    ts: datetime | None = None
    botmaster: str | None = None
    badges: list[Badge]
    xp: float
    gamesplayed: int
    gameswon: int
    gametime: float
    country: str | None = None
    badstanding: bool | None = None
    supporter: bool | None = None  # osk说是必有, 但实际上不是 fkosk
    supporter_tier: int
    avatar_revision: int | None = None
    """This user's avatar ID. Get their avatar at

    https://tetr.io/user-content/avatars/{ USERID }.jpg?rv={ AVATAR_REVISION }"""
    banner_revision: int | None = None
    """This user's banner ID. Get their banner at

    https://tetr.io/user-content/banners/{ USERID }.jpg?rv={ BANNER_REVISION }

    Ignore this field if the user is not a supporter."""
    bio: str | None = None
    connections: Connections
    friend_count: int | None = None
    distinguishment: Distinguishment | None = None
    achievements: list[int]
    ar: int
    ar_counts: ArCounts


class UserInfoSuccess(BaseSuccessModel):
    data: Data


UserInfo = UserInfoSuccess | FailedModel

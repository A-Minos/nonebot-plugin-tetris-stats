from pydantic import BaseModel


class Data(BaseModel):
    lpm: float
    apm: float


class UserProfile(BaseModel):
    user_name: str
    today: Data | None
    total: list[Data] | None

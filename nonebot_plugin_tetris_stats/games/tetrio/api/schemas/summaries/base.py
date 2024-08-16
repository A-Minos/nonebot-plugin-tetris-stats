from pydantic import BaseModel


class User(BaseModel):
    id: str
    username: str
    avatar_revision: int | None
    banner_revision: int | None
    country: str | None
    verified: int | None = None
    supporter: int

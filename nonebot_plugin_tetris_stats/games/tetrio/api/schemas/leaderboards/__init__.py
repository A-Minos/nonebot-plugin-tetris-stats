from typing import Any

from nonebot.compat import PYDANTIC_V2
from pydantic import BaseModel, Field

from ...typedefs import Prisecter


class Parameter(BaseModel):
    after: Prisecter | None = None
    before: Prisecter | None = None
    limit: int = Field(default=25, ge=1, le=100)
    country: str | None = None

    def to_params(self) -> dict[str, Any]:
        if PYDANTIC_V2:
            return self.model_dump(exclude_defaults=True)
        return self.dict(exclude_defaults=True)

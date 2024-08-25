from typing import Any

from pydantic import BaseModel, Field

from ...typing import Prisecter


class Parameter(BaseModel):
    after: Prisecter | None = None
    before: Prisecter | None = None
    limit: int = Field(default=25, ge=1, le=100)
    country: str | None = None

    def to_params(self) -> dict[str, Any]:
        return self.model_dump(exclude_defaults=True)

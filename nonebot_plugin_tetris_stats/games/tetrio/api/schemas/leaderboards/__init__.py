from typing import Annotated

from msgspec import Meta, Struct


class Parameter(Struct, omit_defaults=True):
    after: str | None = None
    before: str | None = None
    limit: Annotated[int, Meta(ge=1, le=100)] = 25
    country: str | None = None

from typing import TypeAlias

from pydantic import BaseModel, Field

from ...typedefs import Prisecter

DEFAULT_RECORD_LIMIT = 25
MAX_RECORD_LIMIT = 100

RecordQueryParamValue: TypeAlias = Prisecter | int
RecordQueryParams: TypeAlias = dict[str, RecordQueryParamValue]


class Parameter(BaseModel):
    after: Prisecter | None = None
    before: Prisecter | None = None
    limit: int = Field(default=DEFAULT_RECORD_LIMIT, ge=1, le=MAX_RECORD_LIMIT)

    def to_params(self) -> RecordQueryParams:
        params: RecordQueryParams = {}
        if self.after is not None:
            params['after'] = self.after
        if self.before is not None:
            params['before'] = self.before
        if self.limit != DEFAULT_RECORD_LIMIT:
            params['limit'] = self.limit
        return params

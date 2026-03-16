from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import DateTime, Dialect, TypeDecorator
from typing_extensions import override

UTC = timezone.utc


class UTCDateTime(TypeDecorator[datetime]):
    """Persist UTC datetimes as naive values while exposing aware UTC in Python."""

    impl = DateTime
    cache_ok = True

    @override
    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        del dialect
        if value is None:
            return None
        if not isinstance(value, datetime):
            msg = 'UTCDateTime only accepts datetime values'
            raise TypeError(msg)
        if value.utcoffset() is None:
            msg = 'UTCDateTime requires aware UTC datetimes, got naive datetime'
            raise ValueError(msg)
        if value.utcoffset() != timedelta():
            msg = 'UTCDateTime requires aware UTC datetimes'
            raise ValueError(msg)
        return value.replace(tzinfo=None)

    @override
    def process_result_value(self, value: Any | None, dialect: Dialect) -> datetime | None:
        del dialect
        if value is None:
            return None
        if not isinstance(value, datetime):
            msg = 'UTCDateTime expected datetime result'
            raise TypeError(msg)
        if value.utcoffset() is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

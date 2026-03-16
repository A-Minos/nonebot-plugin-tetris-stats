from datetime import datetime, timezone

UTC = timezone.utc


def ensure_utc_datetime(value: datetime) -> datetime:
    """Normalize external or boundary datetimes to an aware UTC datetime."""
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)

from datetime import timedelta

from ..i18n import Lang
from .exception import MessageFormatError

DEFAULT_COMPARE_DELTA = timedelta(days=7)
_MIN_DURATION_LEN = 2
_DURATION_UNITS = {
    'w': 'weeks',
    'd': 'days',
    'h': 'hours',
    'm': 'minutes',
    's': 'seconds',
}


def parse_duration(value: str) -> timedelta | MessageFormatError:
    raw = value.strip().lower()
    if raw.isdigit():
        return timedelta(days=int(raw))
    if len(raw) < _MIN_DURATION_LEN or not raw[:-1].isdigit():
        return MessageFormatError(Lang.error.MessageFormatError.duration)
    amount = int(raw[:-1])
    if amount <= 0:
        return MessageFormatError(Lang.error.MessageFormatError.duration)
    unit = _DURATION_UNITS.get(raw[-1])
    if unit is None:
        return MessageFormatError(Lang.error.MessageFormatError.duration)
    return timedelta(**{unit: amount})

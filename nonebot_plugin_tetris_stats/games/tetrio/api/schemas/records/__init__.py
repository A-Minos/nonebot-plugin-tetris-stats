from .league import League, LeagueSuccessModel
from .solo import Solo, SoloSuccessModel

Records = League | Solo
RecordsModel = LeagueSuccessModel | SoloSuccessModel

__all__ = [
    'League',
    'LeagueSuccessModel',
    'Records',
    'RecordsModel',
    'Solo',
    'SoloSuccessModel',
]

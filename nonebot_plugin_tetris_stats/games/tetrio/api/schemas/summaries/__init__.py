from .achievements import Achievements, AchievementsSuccessModel
from .league import LeagueSuccessModel
from .solo import Solo, SoloSuccessModel
from .zen import Zen, ZenSuccessModel
from .zenith import Zenith, ZenithEx, ZenithSuccessModel

SummariesModel = AchievementsSuccessModel | SoloSuccessModel | ZenSuccessModel | LeagueSuccessModel | ZenithSuccessModel

__all__ = [
    'Achievements',
    'AchievementsSuccessModel',
    'LeagueSuccessModel',
    'Solo',
    'SoloSuccessModel',
    'SummariesModel',
    'Zen',
    'ZenSuccessModel',
    'Zenith',
    'ZenithEx',
    'ZenithSuccessModel',
]

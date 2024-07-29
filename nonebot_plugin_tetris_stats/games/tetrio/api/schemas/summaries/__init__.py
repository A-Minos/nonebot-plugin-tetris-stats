from .achievements import Achievements, AchievementsSuccessModel
from .solo import Blitz, SoloSuccessModel, Sprint
from .zen import Zen, ZenSuccessModel
from .zenith import Zenith, ZenithEx, ZenithSuccessModel

SummariesModel = AchievementsSuccessModel | SoloSuccessModel | ZenSuccessModel | ZenithSuccessModel

__all__ = [
    'Achievements',
    'AchievementsSuccessModel',
    'Blitz',
    'Sprint',
    'SoloSuccessModel',
    'Zen',
    'ZenSuccessModel',
    'Zenith',
    'ZenithEx',
    'ZenithSuccessModel',
    'SummariesModel',
]

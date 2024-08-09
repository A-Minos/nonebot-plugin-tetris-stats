from .achievements import Achievements, AchievementsSuccessModel
from .solo import Solo, SoloSuccessModel
from .zen import Zen, ZenSuccessModel
from .zenith import Zenith, ZenithEx, ZenithSuccessModel

SummariesModel = AchievementsSuccessModel | SoloSuccessModel | ZenSuccessModel | ZenithSuccessModel

__all__ = [
    'Achievements',
    'AchievementsSuccessModel',
    'Solo',
    'SoloSuccessModel',
    'Zen',
    'ZenSuccessModel',
    'Zenith',
    'ZenithEx',
    'ZenithSuccessModel',
    'SummariesModel',
]

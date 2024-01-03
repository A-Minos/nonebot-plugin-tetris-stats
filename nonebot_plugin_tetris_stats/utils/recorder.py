from datetime import datetime, timezone
from typing import ClassVar

from nonebot import get_driver, get_plugin
from nonebot.adapters import Bot, Event
from nonebot.matcher import Matcher
from nonebot.message import run_postprocessor, run_preprocessor
from nonebot_plugin_orm import get_session

from ..db.models import HistoricalData

UTC = timezone.utc

driver = get_driver()


class Recorder:
    matchers: ClassVar[set[type[Matcher]]] = set()
    historical_data: ClassVar[dict[int, tuple[HistoricalData, bool]]] = {}
    error_event: ClassVar[set[int]] = set()

    @classmethod
    def create_historical_data(cls, event_id: int, historical_data: HistoricalData) -> None:
        cls.historical_data[event_id] = (historical_data, False)

    @classmethod
    def update_historical_data(cls, event_id: int, historical_data: HistoricalData) -> None:
        if event_id not in cls.historical_data:
            raise KeyError
        cls.historical_data[event_id] = (historical_data, True)

    @classmethod
    def get_historical_data(cls, event_id: int) -> HistoricalData:
        return cls.historical_data[event_id][0]

    @classmethod
    async def save_historical_data(cls, event_id: int) -> None:
        historical_data, completed = cls.del_historical_data(event_id)
        if completed:
            async with get_session() as session:
                session.add(historical_data)
                await session.commit()

    @classmethod
    def del_historical_data(cls, event_id: int) -> tuple[HistoricalData, bool]:
        return cls.historical_data.pop(event_id)

    @classmethod
    def add_error_event(cls, event_id: int) -> None:
        cls.error_event.add(event_id)

    @classmethod
    def del_error_event(cls, event_id: int) -> None:
        cls.error_event.remove(event_id)

    @classmethod
    def is_error_event(cls, event_id: int) -> bool:
        return event_id in cls.error_event


@driver.on_startup
def _():
    plugin = get_plugin('nonebot_plugin_tetris_stats')
    if plugin is not None:
        Recorder.matchers = plugin.matcher
    else:
        raise RuntimeError('获取不到自身插件对象')


@run_preprocessor
def _(bot: Bot, event: Event, matcher: Matcher):
    if isinstance(matcher, tuple(Recorder.matchers)):
        Recorder.create_historical_data(
            event_id=id(event),
            historical_data=HistoricalData(
                trigger_time=datetime.now(tz=UTC),
                bot_platform=bot.type,
                bot_account=bot.self_id,
                source_type=event.get_type(),
                source_account=event.get_session_id(),
                message=event.get_message(),
            ),
        )


@run_postprocessor
async def _(event: Event, matcher: Matcher, exception: Exception | None):
    if isinstance(matcher, tuple(Recorder.matchers)):
        event_id = id(event)
        if exception is not None:
            Recorder.add_error_event(event_id)
            Recorder.del_historical_data(event_id)
        else:
            await Recorder.save_historical_data(event_id)

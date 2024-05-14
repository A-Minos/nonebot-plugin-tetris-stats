from enum import Enum, auto
from typing import TYPE_CHECKING, TypeVar

from nonebot.log import logger
from nonebot_plugin_orm import AsyncSession, get_session
from sqlalchemy import select

from ..utils.typing import GameType
from .models import Bind

if TYPE_CHECKING:
    from ..game_data_processor.io_data_processor.api.models import TETRIOHistoricalData
    from ..game_data_processor.top_data_processor.api.models import TOPHistoricalData
    from ..game_data_processor.tos_data_processor.api.models import TOSHistoricalData


class BindStatus(Enum):
    SUCCESS = auto()
    UPDATE = auto()


async def query_bind_info(
    session: AsyncSession,
    chat_platform: str,
    chat_account: str,
    game_platform: GameType,
) -> Bind | None:
    return (
        await session.scalars(
            select(Bind)
            .where(Bind.chat_platform == chat_platform)
            .where(Bind.chat_account == chat_account)
            .where(Bind.game_platform == game_platform)
        )
    ).one_or_none()


async def create_or_update_bind(
    session: AsyncSession,
    chat_platform: str,
    chat_account: str,
    game_platform: GameType,
    game_account: str,
) -> BindStatus:
    bind = await query_bind_info(
        session=session,
        chat_platform=chat_platform,
        chat_account=chat_account,
        game_platform=game_platform,
    )
    if bind is None:
        bind = Bind(
            chat_platform=chat_platform,
            chat_account=chat_account,
            game_platform=game_platform,
            game_account=game_account,
        )
        session.add(bind)
        message = BindStatus.SUCCESS
    else:
        bind.game_account = game_account
        message = BindStatus.UPDATE
    await session.commit()
    return message


T = TypeVar('T', 'TETRIOHistoricalData', 'TOPHistoricalData', 'TOSHistoricalData')


async def anti_duplicate_add(cls: type[T], model: T) -> None:
    async with get_session() as session:
        result = (
            await session.scalars(
                select(cls)
                .where(cls.update_time == model.update_time)
                .where(cls.user_unique_identifier == model.user_unique_identifier)
                .where(cls.api_type == model.api_type)
            )
        ).all()
    if result:
        for i in result:
            if i.data == model.data:
                logger.debug('Anti duplicate successfully')
                return
    session.add(model)
